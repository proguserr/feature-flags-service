import time
import threading
import requests

class FFClient:
    def __init__(self, api_url: str, timeout: float = 2.0, cache_ttl: float = 30.0):
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache = {}  # key -> (value, ts, version)

    def _get(self, path: str, params=None):
        url = f"{self.api_url}{path}"
        r = requests.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def is_enabled(self, key: str, user_id: str, attributes: dict | None = None) -> bool:
        now = time.time()
        cached = self._cache.get(key)
        if cached and (now - cached[1] < self.cache_ttl):
            return cached[0]
        params = {"user_id": user_id}
        if attributes:
            params.update(attributes)
        data = self._get(f"/evaluate/{key}", params=params)
        self._cache[key] = (data["enabled"], now, data.get("version"))
        return data["enabled"]
