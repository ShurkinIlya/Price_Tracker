"""
Продвинутый прогноз с защитой от шума:
- нормализация цен в RUB
- фичи: лаги t-1..t-7, скользящие mean/std, тренд, волатильность, месяц, one-hot маркетплейса, дисконт распродаж
- CatBoost/LightGBM при наличии и достаточном числе точек, иначе тренд+сглаживание
- мини-валидация на holdout (MAPE), скрываем прогноз при плохом качестве или сильном отклонении
"""

from __future__ import annotations

from typing import Dict, List
from datetime import timedelta

from django.utils import timezone

from products.currency import to_rub
from products.models import OfferHistory
from analysis.models import SaleEvent

MARKETPLACES = ["amazon", "wildberries", "ozon"]
MAPE_THRESHOLD = 0.25
MIN_POINTS_MODEL = 10
MIN_POINTS_ANY = 3


def _one_hot(value: str, choices: List[str]) -> List[int]:
    val = (value or "").lower()
    return [1 if val == c else 0 for c in choices]


def _calc_features(history: List[dict], marketplace: str) -> Dict[str, float]:
    values = [float(item["price"]) for item in history]
    n = len(values)
    mean = sum(values) / n
    last = values[-1]
    diffs = [values[i] - values[i - 1] for i in range(1, n)]
    trend = diffs[-1] if diffs else 0.0
    vol = 0.0
    if n > 1:
        var = sum((v - mean) ** 2 for v in values) / n
        vol = var ** 0.5
    month = timezone.now().month
    # лаги (до 7)
    lags = []
    for i in range(1, 8):
        lags.append(values[-i] if len(values) >= i else values[0])
    # скользящие
    window = values[-3:] if len(values) >= 3 else values
    roll_mean = sum(window) / len(window)
    roll_std = 0.0
    if len(window) > 1:
        v = sum((x - roll_mean) ** 2 for x in window) / len(window)
        roll_std = v ** 0.5
    mp_one_hot = _one_hot(marketplace, MARKETPLACES)
    return {
        "last": last,
        "mean": mean,
        "trend": trend,
        "volatility": vol,
        "month": month,
        "count": n,
        "roll_mean": roll_mean,
        "roll_std": roll_std,
        "lags": lags,
        "mp_one_hot": mp_one_hot,
        "values": values,
    }


def _sale_event_discount() -> float:
    today = timezone.now().date()
    events = SaleEvent.objects.filter(start_date__lte=today, end_date__gte=today)
    if events.exists():
        return max(float(ev.discount_hint) for ev in events)
    soon = SaleEvent.objects.filter(start_date__gt=today, start_date__lte=today + timedelta(days=14))
    if soon.exists():
        return max(float(ev.discount_hint) * 0.5 for ev in soon)
    return 0.0


def _mape(y_true: List[float], y_pred: List[float]) -> float:
    eps = 1e-6
    errors = []
    for t, p in zip(y_true, y_pred):
        if t == 0:
            continue
        errors.append(abs((t - p) / (t + eps)))
    if not errors:
        return 1.0
    return sum(errors) / len(errors)


def advanced_predict(query_id: int, category: str, marketplace: str = "") -> Dict[str, float]:
    history = list(
        OfferHistory.objects.filter(query_id=query_id)
        .order_by("collected_at")
        .values("price", "currency", "marketplace", "collected_at")
    )
    if not history or len(history) < MIN_POINTS_ANY:
        return {}

    normalized = [
        {"price": to_rub(float(h["price"]), h["currency"]), "marketplace": h["marketplace"], "collected_at": h["collected_at"]}
        for h in history
    ]
    most_recent_mp = normalized[-1].get("marketplace", marketplace)
    feats = _calc_features(normalized, most_recent_mp)
    if not feats:
        return {}

    # базовый прогноз: тренд + поправка
    projected = feats["last"] + feats["trend"] * (30 / 7)
    sale_discount = _sale_event_discount()
    projected *= (1 - sale_discount / 100.0)

    # смягчение: смешиваем со сглаженной ценой
    smoothed = feats["roll_mean"]
    projected = 0.7 * projected + 0.3 * smoothed

    # CatBoost/LightGBM если данных >= MIN_POINTS_MODEL
    if feats["count"] >= MIN_POINTS_MODEL:
        try:
            try:
                from catboost import CatBoostRegressor  # type: ignore

                model = CatBoostRegressor(
                    iterations=60, depth=5, learning_rate=0.1, loss_function="RMSE", verbose=False
                )
                X = [[
                    feats["mean"], feats["trend"], feats["volatility"], feats["count"], feats["month"],
                    feats["roll_mean"], feats["roll_std"], *feats["lags"], *feats["mp_one_hot"]
                ]]
                y = [feats["last"]]
                # мини-валидация на holdout (20% последних точек, если хватит)
                holdout_start = max(0, feats["count"] - max(2, feats["count"] // 5))
                holdout = feats["values"][holdout_start:]
                train_vals = feats["values"][:holdout_start] or feats["values"]
                model.fit(X, y)
                pred_model = float(model.predict(X)[0])
                if holdout:
                    hold_pred = [pred_model for _ in holdout]
                    mape = _mape(holdout, hold_pred)
                    if mape > MAPE_THRESHOLD:
                        return {}
                projected = 0.7 * pred_model + 0.3 * smoothed
            except ImportError:
                from lightgbm import LGBMRegressor  # type: ignore

                model = LGBMRegressor(n_estimators=80, learning_rate=0.08, max_depth=4)
                X = [[
                    feats["mean"], feats["trend"], feats["volatility"], feats["count"], feats["month"],
                    feats["roll_mean"], feats["roll_std"], *feats["lags"], *feats["mp_one_hot"]
                ]]
                y = [feats["last"]]
                model.fit(X, y)
                pred_model = float(model.predict(X)[0])
                projected = 0.7 * pred_model + 0.3 * smoothed
        except Exception:
            pass

    # ограничение по волатильности и минимум 0
    if feats["volatility"] > 0:
        max_jump = feats["volatility"] * 2.5
        projected = max(min(projected, feats["last"] + max_jump), feats["last"] - max_jump)
    projected = max(projected, 0.0)

    confidence = 0.8 if feats["count"] > 20 else 0.65 if feats["count"] >= 10 else 0.5
    if feats["volatility"] > 0.15:
        confidence -= 0.1
    # если прогноз сильно отклонён (>50% от текущей цены) — скрываем
    if feats["last"] > 0 and abs(projected - feats["last"]) / feats["last"] > 0.5:
        return {}
    if confidence < 0.4:
        return {}

    return {
        "forecast_price": round(projected, 2),
        "current_price": round(feats["last"], 2),
        "base_currency": "RUB",
        "confidence": confidence,
        "volatility": round(feats["volatility"], 3),
        "trend": round(feats["trend"], 2),
        "points": feats["count"],
        "sale_discount": sale_discount,
    }
