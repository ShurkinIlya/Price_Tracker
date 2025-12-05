import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup


class AmazonParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://www.amazon.com/",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def search_product(self, product_name: str) -> List[dict]:
        try:
            search_url = f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}"
            response = self.session.get(search_url, timeout=12)
            soup = BeautifulSoup(response.content, "html.parser")

            products = []
            items = soup.find_all("div", {"data-component-type": "s-search-result"})

            for item in items[:5]:
                product = self.parse_product_item(item)
                if product:
                    products.append(product)

            return products
        except Exception as e:
            print(f"Amazon parser error: {e}")
            return []

    def parse_product_item(self, item) -> Optional[dict]:
        try:
            title_elem = item.find("h2")
            price_elem = item.find("span", class_="a-price-whole")
            image_elem = item.find("img", class_="s-image")
            link_elem = item.find("a", class_="a-link-normal")
            rating_elem = item.find("span", class_="a-icon-alt")

            if not all([title_elem, price_elem]):
                return None

            title = title_elem.text.strip()
            price_text = price_elem.text.replace(",", "").replace("?", "").strip()
            price = float(re.sub(r"[^\d.]", "", price_text))
            image_url = image_elem.get("src") if image_elem else ""
            product_url = f"https://amazon.com{link_elem.get('href')}" if link_elem else ""
            rating = None
            if rating_elem:
                match = re.search(r"([\d.]+)", rating_elem.text)
                rating = float(match.group(1)) if match else None

            return {
                "title": title,
                "price": price,
                "image_url": image_url,
                "url": product_url,
                "marketplace": "amazon",
                "currency": "USD",
                "rating": rating,
            }
        except Exception as e:
            print(f"Error parsing Amazon item: {e}")
            return None
