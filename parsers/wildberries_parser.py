from typing import List, Optional

import requests
from .proxy_pool import ProxyPool


class WildberriesParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": "https://www.wildberries.ru",
            "Referer": "https://www.wildberries.ru/",
        }
        self.params_base = {
            "appType": 1,
            "curr": "rub",
            "dest": "-1257786",
        }
        self.proxy_pool = ProxyPool()

    def search_product(self, product_name: str) -> List[dict]:
        try:
            search_url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
            params = {
                **self.params_base,
                "query": product_name,
                "resultset": "catalog",
                "sort": "popular",
                "limit": 20,
                "page": 1,
            }

            response = self._safe_get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

            products = []
            for item in data.get("data", {}).get("products", [])[:8]:
                product = self.parse_product_item(item)
                if product:
                    products.append(product)

            return products
        except Exception as e:
            print(f"Wildberries parser error: {e}")
            return []

    def parse_product_item(self, item) -> Optional[dict]:
        try:
            title = item.get("name", "")
            price_raw = item.get("salePriceU") or item.get("priceU")
            price = float(price_raw) / 100 if price_raw else None
            # берем более крупный размер, чтобы не было "мыла" в карточках
            image_url = f"https://images.wbstatic.net/c516x688/new/{item.get('id', 0)}-1.jpg"
            product_url = f"https://www.wildberries.ru/catalog/{item.get('id', 0)}/detail.aspx"
            rating_raw = item.get("reviewRating")
            rating = None
            if rating_raw:
                rating = float(rating_raw) / 100 if rating_raw > 10 else float(rating_raw)

            return {
                "title": title,
                "price": price,
                "image_url": image_url,
                "url": product_url,
                "marketplace": "wildberries",
                "currency": "RUB",
                "rating": rating,
            }
        except Exception as e:
            print(f"Error parsing Wildberries item: {e}")
            return None

    def _safe_get(self, url, **kwargs):
        try:
            resp = requests.get(url, headers=self.headers, timeout=12, **kwargs)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass

        # fallback to free proxies
        for _ in range(5):
            proxy = self.proxy_pool.get_proxy()
            if not proxy:
                break
            try:
                resp = requests.get(
                    url, headers=self.headers, timeout=12, proxies=proxy, **kwargs
                )
                if resp.status_code == 200:
                    return resp
            except Exception:
                continue
        return requests.get(url, headers=self.headers, timeout=12, **kwargs)
