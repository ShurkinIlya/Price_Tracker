import os
import random
from typing import List, Optional

import requests


class ProxyPool:
    """
    Very lightweight free-proxy fetcher. It pulls HTTP proxies from proxyscrape.
    Reliability is low; use only when no paid proxy is available.
    """

    def __init__(self):
        self.static_proxy = os.environ.get("PROXY_URL")
        self.pool: List[str] = []
        if not self.static_proxy:
            self._refresh_pool()

    def _refresh_pool(self) -> None:
        try:
            resp = requests.get(
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=all&ssl=all&anonymity=all",
                timeout=8,
            )
            if resp.status_code == 200:
                lines = [p.strip() for p in resp.text.splitlines() if p.strip()]
                self.pool = [f"http://{p}" for p in lines][:30]
        except Exception as exc:
            print(f"ProxyPool refresh error: {exc}")

    def get_proxy(self) -> Optional[dict]:
        if self.static_proxy:
            return {"http": self.static_proxy, "https": self.static_proxy}
        if not self.pool:
            self._refresh_pool()
        if not self.pool:
            return None
        proxy = random.choice(self.pool)
        return {"http": proxy, "https": proxy}
