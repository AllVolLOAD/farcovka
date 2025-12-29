import random
import asyncio
from typing import List

class RpcPool:
    """Simple RPC pool with round-robin and healthcheck."""
    def __init__(self, urls: List[str], healthcheck, timeout: float = 3.0):
        self.urls = urls
        self.idx = 0
        self.healthcheck = healthcheck
        self.timeout = timeout

    def next(self) -> str:
        if not self.urls:
            raise RuntimeError("RPC pool is empty")
        url = self.urls[self.idx % len(self.urls)]
        self.idx = (self.idx + 1) % len(self.urls)
        return url

    async def get_healthy(self) -> str:
        if not self.urls:
            raise RuntimeError("RPC pool is empty")
        start = self.idx
        for _ in range(len(self.urls)):
            url = self.next()
            if await self._is_healthy(url):
                return url
        # fallback: return next anyway
        return self.next()

    async def _is_healthy(self, url: str) -> bool:
        try:
            return await asyncio.wait_for(self.healthcheck(url), timeout=self.timeout)
        except Exception:
            return False

