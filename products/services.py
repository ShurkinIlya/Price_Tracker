from __future__ import annotations

from typing import Dict, List

from random import randint

from parsers.amazon_parser import AmazonParser
from parsers.wildberries_parser import WildberriesParser
from parsers.ozon_parser import OzonParser


PARSER_REGISTRY = {
    "amazon": AmazonParser,
    "wildberries": WildberriesParser,
    "ozon": OzonParser,
}


def fetch_offers_from_marketplaces(
    product_name: str, marketplaces: List[str]
) -> List[Dict]:
    offers: List[Dict] = []
    for marketplace in marketplaces:
        parser_cls = PARSER_REGISTRY.get(marketplace)
        if not parser_cls:
            continue
        parser = parser_cls()
        try:
            offers.extend(parser.search_product(product_name))
        except Exception as exc:
            print(f"{marketplace} parser failed: {exc}")
    return offers


def generate_demo_offers(product_name: str) -> List[Dict]:
    """
    Use lightweight deterministic demo offers when real parsing fails.
    """
    base = 50 + (sum(ord(ch) for ch in product_name) % 300)
    return [
        {
            "title": f"{product_name} — Amazon demo",
            "price": round(base * 1.05, 2),
            "currency": "USD",
            "marketplace": "amazon",
            "rating": 4.6,
            "url": "",
            "image_url": "",
        },
        {
            "title": f"{product_name} — Wildberries demo",
            "price": round(base * 92, 2),
            "currency": "RUB",
            "marketplace": "wildberries",
            "rating": 4.3,
            "url": "",
            "image_url": "",
        },
        {
            "title": f"{product_name} — Ozon demo",
            "price": round(base * 95, 2),
            "currency": "RUB",
            "marketplace": "ozon",
            "rating": 4.5,
            "url": "",
            "image_url": "",
        },
    ]
