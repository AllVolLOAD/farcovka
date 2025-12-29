import asyncio
import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class EventListener:
    """Generic event listener with idempotent processor."""

    def __init__(
        self,
        fetch_logs: Callable[[int, int], Awaitable[list]],
        process_log: Callable[[dict], Awaitable[None]],
        get_last_block: Callable[[], Awaitable[int]],
        confirm_depth: int = 6,
        batch_size: int = 500,
    ):
        self.fetch_logs = fetch_logs
        self.process_log = process_log
        self.get_last_block = get_last_block
        self.confirm_depth = confirm_depth
        self.batch_size = batch_size
        self._stop = False

    async def run(self):
        while not self._stop:
            try:
                await self._cycle()
            except Exception as e:
                logger.exception("listener error: %s", e)
                await asyncio.sleep(2)

    async def _cycle(self):
        head = await self.get_last_block()
        target = head - self.confirm_depth
        start = await self._load_cursor()
        if start is None:
            start = target

        while start <= target:
            end = min(start + self.batch_size - 1, target)
            logs = await self.fetch_logs(start, end)
            for log in logs:
                await self.process_log(log)
            await self._save_cursor(end + 1)
            start = end + 1

    async def _load_cursor(self) -> int | None:
        # placeholder; integrate with storage
        return None

    async def _save_cursor(self, block: int):
        # placeholder; integrate with storage
        pass

    def stop(self):
        self._stop = True

