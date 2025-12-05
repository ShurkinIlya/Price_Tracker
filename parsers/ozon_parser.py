import json
import re
from typing import List, Optional

import os
import requests
from bs4 import BeautifulSoup

from .proxy_pool import ProxyPool


class OzonParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ru,en;q=0.9",
            "Referer": "https://www.ozon.ru/",
        }
        proxy_url = os.environ.get("PROXY_URL")
        self.proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        self.proxy_pool = ProxyPool()

    def search_product(self, product_name: str) -> List[dict]:
        try:
            search_url = f"https://www.ozon.ru/search/?text={product_name.replace(' ', '+')}"
            response = self._safe_get(search_url)
            soup = BeautifulSoup(response.text, "lxml")

            products = self._parse_from_state_script(soup)
            if not products:
                products = self._composer_api_search(product_name)
            if not products:
                products = self._parse_from_cards(soup)
            return products[:6]
        except Exception as e:
            print(f"Ozon parser error: {e}")
            return []

    def _composer_api_search(self, product_name: str) -> List[dict]:
        """
        Try internal composer-api endpoint. Often sits behind Cloudflare;
        will return empty on block, but helps when HTML is obfuscated.
        """
        url = "https://www.ozon.ru/api/composer-api.bx/_action"
        payload = {
            "url": f"/search/?text={product_name.replace(' ', '+')}",
            "action": "state/get",
        }
        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Origin": "https://www.ozon.ru",
        }
        try:
            resp = self._safe_post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            # Try to locate items inside widgetStates
            widgets = data.get("widgetStates") or {}
            products: List[dict] = []

            for _, widget_json in widgets.items():
                try:
                    widget = json.loads(widget_json)
                except Exception:
                    continue
                items = None
                if isinstance(widget, dict):
                    items = widget.get("items") or widget.get("products") or None
                if not items and isinstance(widget, list) and widget:
                    items = widget
                if not items:
                    continue
                for item in items:
                    mapped = self._map_state_item(item)
                    if mapped:
                        products.append(mapped)
                if products:
                    break

            return products
        except Exception as exc:
            print(f"Ozon composer api error: {exc}")
            return []

    # Proxy-aware wrappers
    def _safe_get(self, url, **kwargs):
        return self._request_with_fallback("get", url, **kwargs)

    def _safe_post(self, url, **kwargs):
        return self._request_with_fallback("post", url, **kwargs)

    def _request_with_fallback(self, method: str, url: str, **kwargs):
        # Try direct or env proxy first
        try:
            resp = requests.request(
                method, url, headers=self.headers, timeout=12, proxies=self.proxies, **kwargs
            )
            if resp.status_code == 200:
                return resp
        except Exception:
            pass

        # Fallback: rotate free proxy
        for _ in range(5):
            proxy = self.proxy_pool.get_proxy()
            if not proxy:
                break
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=12,
                    proxies=proxy,
                    **kwargs,
                )
                if resp.status_code == 200:
                    return resp
            except Exception:
                continue
        # Final attempt without proxy to raise any error
        return requests.request(method, url, headers=self.headers, timeout=12, **kwargs)

    def _parse_from_state_script(self, soup: BeautifulSoup) -> List[dict]:
        results: List[dict] = []
        state_script = soup.find("script", id="__NEXT_DATA__")
        if not state_script or not state_script.string:
            return results
        try:
            data = json.loads(state_script.string)
            widgets = data.get("props", {}).get("pageProps", {}).get("fallback", {})
            # Try to find items array anywhere inside fallback payload
            items = []
            def walk(obj):
                nonlocal items
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == "items" and isinstance(value, list) and value:
                            items = value
                            return
                        walk(value)
                elif isinstance(obj, list):
                    for value in obj:
                        walk(value)
            walk(widgets)
            for item in items[:5]:
                mapped = self._map_state_item(item)
                if mapped:
                    results.append(mapped)
        except Exception as exc:
            print(f"Ozon state parse failed: {exc}")
        return results

    def _map_state_item(self, item) -> Optional[dict]:
        try:
            title = item.get("name") or item.get("title") or ""
            price_raw = item.get("price") or item.get("priceValue") or 0
            if isinstance(price_raw, dict):
                price_raw = price_raw.get("price") or price_raw.get("value") or 0
            price_text = str(price_raw)
            price = float(re.sub(r"[^\d.]", "", price_text)) if price_text else None
            url_suffix = item.get("url") or item.get("action") or ""
            product_url = f"https://www.ozon.ru{url_suffix}" if url_suffix else ""
            image_url = (
                item.get("image")
                or item.get("tileImage")
                or item.get("primaryImage")
                or self._extract_image_from_media(item)
                or ""
            )
            rating = item.get("rating") or item.get("mark")
            rating_value = float(rating) if rating else None
            return {
                "title": title,
                "price": price,
                "image_url": image_url,
                "url": product_url,
                "marketplace": "ozon",
                "currency": "RUB",
                "rating": rating_value,
            }
        except Exception:
            return None

    def _parse_from_cards(self, soup: BeautifulSoup) -> List[dict]:
        results: List[dict] = []
        cards = soup.select("div[data-widget='searchResultsV2'] a")
        if not cards:
            cards = soup.select("a.tile-hover-target")
        for card in cards[:5]:
            title_elem = card.find("span")
            price_elem = card.find(text=re.compile(r"[\d\s]+₽"))
            title = title_elem.text.strip() if title_elem else ""
            price = None
            if price_elem:
                price = float(re.sub(r"[^\d.]", "", price_elem))
            href = card.get("href", "")
            product_url = f"https://www.ozon.ru{href}" if href.startswith("/") else href
            image = ""
            img_elem = card.find("img")
            if img_elem:
                image = img_elem.get("src") or img_elem.get("data-src") or ""
            results.append(
                {
                    "title": title,
                    "price": price,
                    "image_url": image,
                    "url": product_url,
                    "marketplace": "ozon",
                    "currency": "RUB",
                    "rating": None,
                }
            )
        return results

    def _extract_image_from_media(self, item) -> Optional[str]:
        media = item.get("media") or item.get("images") or None
        if isinstance(media, list) and media:
            first = media[0]
            if isinstance(first, dict):
                return first.get("url") or first.get("src")
        if isinstance(media, dict):
            return media.get("url") or media.get("src")
        return None
