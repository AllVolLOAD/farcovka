import asyncio
import logging
from typing import Callable, Awaitable, Iterable

logger = logging.getLogger(__name__)


class Reconciler:
    """Periodically compares on-chain balances with DB cache."""

    def __init__(
        self,
        get_users_tokens: Callable[[], Awaitable[Iterable[tuple]]],
        get_onchain_balance: Callable[[str, str], Awaitable[int]],
        get_db_balance: Callable[[str, str], Awaitable[int]],
        handle_delta: Callable[[str, str, int], Awaitable[None]],
        interval: float = 60.0,
    ):
        self.get_users_tokens = get_users_tokens
        self.get_onchain_balance = get_onchain_balance
        self.get_db_balance = get_db_balance
        self.handle_delta = handle_delta
        self.interval = interval
        self._stop = False

    async def run(self):
        while not self._stop:
            try:
                await self._cycle()
            except Exception as e:
                logger.exception("reconcile error: %s", e)
            await asyncio.sleep(self.interval)

    async def _cycle(self):
        pairs = await self.get_users_tokens()
        for user, token in pairs:
            onchain = await self.get_onchain_balance(user, token)
            cached = await self.get_db_balance(user, token)
            delta = onchain - cached
            if delta != 0:
                await self.handle_delta(user, token, delta)

    def stop(self):
        self._stop = True

