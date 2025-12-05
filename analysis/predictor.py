from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from django.utils import timezone

from products.models import OfferHistory
from .seasonal_analyzer import SeasonalAnalyzer


class PricePredictor:
    """
    Lightweight predictor:
    - нормализует цены в единую валюту (упрощённо, фиксированные курсы)
    - сглаживает ряд экспоненциальным сглаживанием
    - применяет сезонный коэффициент по категории и календарь распродаж
    """

    def __init__(self, smoothing: float = 0.4, base_currency: str = "RUB"):
        self.alpha = smoothing
        self.base_currency = base_currency
        self.seasonal = SeasonalAnalyzer()
        self.rate_cache: Dict[str, float] = {"RUB": 1.0}

    def predict(self, query_id: int, category: str) -> Dict[str, object]:
        history = list(
            OfferHistory.objects.filter(query_id=query_id)
            .order_by("-collected_at")[:60]
            .values("price", "currency", "collected_at")
        )
        if not history:
            return {
                "current_price": None,
                "forecast_price": None,
                "confidence": 0,
                "note": "Недостаточно данных для прогноза",
            }

        normalized = [
            self._to_base(float(h["price"]), h["currency"]) for h in history
        ]
        hist_for_smoothing = [
            {"price": price, "collected_at": h["collected_at"]}
            for price, h in zip(normalized, history)
        ]

        smoothed, last_price = self._exponential_smoothing(hist_for_smoothing)
        trend_adj = self._linear_trend(hist_for_smoothing)
        seasonal_discount = self._category_season_discount(category)
        sale_event_discount = self._sale_event_discount()

        discount_total = 1 - ((seasonal_discount + sale_event_discount) / 100.0)
        forecast_price = (smoothed + trend_adj) * max(discount_total, 0.5)

        volatility = self._volatility(hist_for_smoothing)
        confidence = 0.5
        if len(history) >= 10:
            confidence = 0.65
        if len(history) >= 25:
            confidence = 0.75
        if volatility < 0.08 and len(history) >= 15:
            confidence += 0.05

        return {
            "current_price": round(float(last_price), 2),
            "forecast_price": round(float(forecast_price), 2),
            "confidence": confidence,
            "base_currency": self.base_currency,
            "applied_discounts": {
                "seasonal": seasonal_discount,
                "sale_event": sale_event_discount,
            },
            "points": len(history),
            "volatility": round(volatility, 3),
            "trend": round(trend_adj, 2),
        }

    def _exponential_smoothing(
        self, history: List[Dict]
    ) -> Tuple[float, float]:
        hist = list(reversed(history))  # chronological
        smoothed = hist[0]["price"]
        last = smoothed
        for item in hist[1:]:
            price = item["price"]
            smoothed = self.alpha * price + (1 - self.alpha) * smoothed
            last = price
        return smoothed, last

    def _to_base(self, price: float, currency: Optional[str]) -> float:
        curr = (currency or "").upper()
        rate = self._get_rate(curr)
        return price * rate

    def _get_rate(self, currency: str) -> float:
        if currency in self.rate_cache:
            return self.rate_cache[currency]
        if not currency or currency == "RUB":
            self.rate_cache[currency or "RUB"] = 1.0
            return 1.0
        try:
            resp = requests.get("https://www.cbr-xml-daily.ru/latest.js", timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                rate_val = data.get("rates", {}).get(currency)
                if rate_val:
                    # в API база RUB, rates[currency] = currency_per_RUB; нам нужен RUB_per_currency
                    inv = 1 / float(rate_val)
                    self.rate_cache[currency] = inv
                    return inv
        except Exception:
            pass
        # fallback: хранить грубый курс, если запрос не удался
        fallback = 90.0 if currency == "USD" else 100.0
        self.rate_cache[currency] = fallback
        return fallback

    def _category_season_discount(self, category: str) -> float:
        """
        Хардкод правил: пуховики/одежда дешевеют летом, электроника — ближе к BF,
        книги — без сильной сезонности. Возвращает % скидки ожидаемой.
        """
        month = timezone.now().month
        category = (category or "").lower()
        if "clothing" in category or "пух" in category or "coat" in category:
            # лето — самая низкая цена
            if month in (6, 7, 8):
                return 20
            if month in (9, 10):
                return 10
            return 5
        if "electronics" in category or "ноут" in category or "phone" in category:
            # чуть лучше к ноябрю (BF)
            if month in (10, 11):
                return 15
            if month in (12,):
                return 8
            return 5
        return 5

    def _sale_event_discount(self) -> float:
        """
        Проверяем близость к большим распродажам.
        """
        now = timezone.now().date()
        year = now.year
        events = [
            datetime(year, 11, 11).date(),  # 11.11
            datetime(year, 11, 29).date(),  # условно Black Friday (последняя пятница ноября)
            datetime(year, 12, 25).date(),  # Новый год/праздничные скидки
            datetime(year, 1, 10).date(),   # post-NY распродажи
        ]
        min_days = min(abs((ev - now).days) for ev in events)
        if min_days <= 7:
            return 15
        if min_days <= 21:
            return 8
        return 0

    def _volatility(self, history: List[Dict]) -> float:
        """
        Простая волатильность: относительное стандартное отклонение.
        """
        values = [h["price"] for h in history]
        if not values:
            return 0
        mean = sum(values) / len(values)
        if mean == 0:
            return 0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        return std / mean

    def _linear_trend(self, history: List[Dict]) -> float:
        """
        Простая линейная регрессия по индексу точек (как дни). Возвращает прогнозируемый сдвиг
        на 7 шагов вперёд.
        """
        if len(history) < 3:
            return 0.0
        n = len(history)
        xs = list(range(n))
        ys = [item["price"] for item in history]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        if den == 0:
            return 0.0
        slope = num / den
        horizon = 7
        return slope * horizon
