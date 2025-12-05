import requests
from typing import Dict, Optional

from analysis.models import CurrencyRate

_RATE_CACHE: Dict[str, float] = {"RUB": 1.0}


def get_rate(currency: str) -> float:
    curr = (currency or "").upper()
    if curr in _RATE_CACHE:
        return _RATE_CACHE[curr]
    if curr == "RUB" or curr == "":
        _RATE_CACHE[curr or "RUB"] = 1.0
        return 1.0
    # try DB
    try:
        db_rate = CurrencyRate.objects.filter(code=curr).order_by("-updated_at").first()
        if db_rate:
            _RATE_CACHE[curr] = float(db_rate.rate)
            return float(db_rate.rate)
    except Exception:
        pass
    # fallback to API and save (если нет записи — для первой инициализации)
    try:
        resp = requests.get("https://www.cbr-xml-daily.ru/latest.js", timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            rate_val = data.get("rates", {}).get(curr)
            if rate_val:
                inv = 1 / float(rate_val)  # RUB per currency
                _RATE_CACHE[curr] = inv
                try:
                    CurrencyRate.objects.update_or_create(code=curr, defaults={"rate": inv})
                except Exception:
                    pass
                return inv
    except Exception:
        pass
    fallback = 90.0 if curr == "USD" else 100.0
    _RATE_CACHE[curr] = fallback
    return fallback


def to_rub(price: float, currency: Optional[str]) -> float:
    rate = get_rate(currency or "RUB")
    return price * rate
