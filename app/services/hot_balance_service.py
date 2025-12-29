"""
⚠️ ЗАМОРОЖЕНО: Разработка HOT/COLD режимов приостановлена
Возвращаемся к работе над парсерами курсов валют.

Service helpers for managing HOT-mode off-chain balances.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.balance import UserBalance

logger = logging.getLogger(__name__)


class HOTBalanceService:
    """Manages user balances for HOT (custodial) mode."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_balance(self, user_id: int, token: str = "USDT") -> Decimal:
        """Return current balance for user/token (creates zero row if missing)."""
        balance_row = await self._get_or_create_balance(user_id, token)
        return Decimal(balance_row.balance or 0)

    async def create_balance(self, user_id: int, token: str = "USDT") -> UserBalance:
        """Ensure balance row exists; idempotent."""
        existing = await self._get_balance_row(user_id, token)
        if existing:
            return existing

        balance_row = UserBalance(user_id=user_id, token=token, balance=Decimal("0"))
        self.session.add(balance_row)
        await self.session.commit()
        await self.session.refresh(balance_row)

        logger.info("Created HOT balance row for user %s token %s", user_id, token)
        return balance_row

    async def update_balance(
        self,
        user_id: int,
        token: str,
        delta: Decimal,
        reason: str | None = None,
    ) -> UserBalance:
        """
        Increment balance by delta (can be negative). Raises if result would be < 0.
        """
        if not isinstance(delta, Decimal):
            delta = Decimal(str(delta))

        balance_row = await self._get_or_create_balance(user_id, token)
        new_balance = Decimal(balance_row.balance or 0) + delta

        if new_balance < 0:
            raise ValueError("Insufficient HOT balance")

        balance_row.balance = new_balance
        await self.session.commit()
        await self.session.refresh(balance_row)

        logger.info(
            "Updated HOT balance user=%s token=%s delta=%s reason=%s -> %s",
            user_id,
            token,
            delta,
            reason,
            new_balance,
        )
        return balance_row

    async def check_sufficient_balance(
        self,
        user_id: int,
        amount: Decimal,
        token: str = "USDT",
    ) -> bool:
        """Return True if user has at least amount available."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        balance = await self.get_balance(user_id, token)
        return balance >= amount

    async def _get_or_create_balance(self, user_id: int, token: str) -> UserBalance:
        balance_row = await self._get_balance_row(user_id, token)
        if balance_row:
            return balance_row
        return await self.create_balance(user_id, token)

    async def _get_balance_row(self, user_id: int, token: str) -> UserBalance | None:
        stmt = (
            select(UserBalance)
            .where(
                UserBalance.user_id == user_id,
                UserBalance.token == token,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

