"""Transaction tracking service"""

import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.db.transaction import Transaction

logger = logging.getLogger(__name__)


class TxService:
    """Service for tracking blockchain transactions"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_transaction(
        self,
        order_id: int | None,
        tx_hash: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        chain_id: int,
        tx_type: str  # 'deposit' or 'withdrawal'
    ) -> Transaction:
        """Create a new transaction record"""
        try:
            tx = Transaction(
                order_id=order_id,
                tx_hash=tx_hash,
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                chain_id=chain_id,
                type=tx_type,
                status='pending',
                confirmations=0
            )
            
            self.session.add(tx)
            await self.session.commit()
            await self.session.refresh(tx)
            
            logger.info(f"Created transaction record: {tx_hash}")
            return tx
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating transaction: {e}", exc_info=True)
            raise
    
    async def get_transaction_by_hash(self, tx_hash: str) -> Transaction | None:
        """Get transaction by hash"""
        stmt = select(Transaction).where(Transaction.tx_hash == tx_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_pending_transactions(self) -> list[Transaction]:
        """Get all pending transactions"""
        stmt = select(Transaction).where(Transaction.status == 'pending')
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_transaction_status(
        self,
        tx_hash: str,
        status: str,
        confirmations: int
    ):
        """Update transaction status and confirmations"""
        try:
            tx = await self.get_transaction_by_hash(tx_hash)
            
            if tx:
                tx.status = status
                tx.confirmations = confirmations
                await self.session.commit()
                logger.info(f"Updated tx {tx_hash}: status={status}, confirmations={confirmations}")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating transaction: {e}", exc_info=True)
            raise
    
    async def get_order_transactions(self, order_id: int) -> list[Transaction]:
        """Get all transactions for an order"""
        stmt = select(Transaction).where(Transaction.order_id == order_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

