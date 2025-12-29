"""Order management service"""

import logging
import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.order import Order
from app.models.db.user import User
from app.models.db.wallet import WalletAccount
from app.services.hot_balance_service import HOTBalanceService

logger = logging.getLogger(__name__)

VALID_WALLET_MODES = {"COLD", "HOT"}


class OrderService:
    """Service for managing exchange orders"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_order(
        self,
        user_id: int,
        wallet_id: int | None,
        order_type: str,  # 'buy' or 'sell'
        currency_pair: str,  # e.g., 'USD/RUB'
        amount_crypto: Decimal,
        amount_fiat: Decimal,
        rate: Decimal,
        wallet_mode: str = "COLD",
        token: str = "USDT",
    ) -> Order:
        """
        Create a new order.
        For buy orders: generates deposit address and sets status to 'deposit_wait'
        For sell orders: prepares withdrawal and sets status to 'pending'
        """
        try:
            wallet_mode = (wallet_mode or "COLD").upper()
            if wallet_mode not in VALID_WALLET_MODES:
                raise ValueError(f"Unsupported wallet mode: {wallet_mode}")

            wallet: WalletAccount | None = None
            if wallet_id:
                wallet = await self._get_user_wallet(user_id, wallet_id)
            elif wallet_mode == "COLD":
                raise ValueError("wallet_id is required for COLD orders")

            hot_balance_service: HOTBalanceService | None = None
            if wallet_mode == "HOT":
                await self._ensure_user_hot_access(user_id)
                hot_balance_service = HOTBalanceService(self.session)

            # Create order
            order = Order(
                user_id=user_id,
                wallet_id=wallet.id if wallet else None,
                type=order_type,
                currency_pair=currency_pair,
                amount_crypto=amount_crypto,
                amount_fiat=amount_fiat,
                rate=rate,
                status='pending',
                wallet_mode=wallet_mode,
            )
            
            if wallet_mode == "COLD":
                # For buy orders, generate deposit address
                if order_type == 'buy':
                    deposit_address = self._generate_deposit_address()
                    order.deposit_address = deposit_address
                    order.status = 'deposit_wait'
                    logger.info(f"Creating COLD buy order with deposit address {deposit_address}")
                else:
                    logger.info(f"Creating COLD sell order for wallet {wallet_id}")
            else:
                # HOT mode: no deposit addresses, status immediately processing
                order.deposit_address = None
                order.status = 'processing'

                if order_type == 'buy':
                    has_balance = await hot_balance_service.check_sufficient_balance(user_id, amount_crypto, token)
                    if not has_balance:
                        raise ValueError("Insufficient HOT balance for buy order")
                else:
                    # For sell orders we reserve funds immediately
                    await hot_balance_service.update_balance(
                        user_id=user_id,
                        token=token,
                        delta=Decimal(0) - Decimal(amount_crypto),
                        reason="sell_order_reserve",
                    )
            
            self.session.add(order)
            await self.session.commit()
            await self.session.refresh(order)
            
            return order
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating order: {e}", exc_info=True)
            raise
    
    def _generate_deposit_address(self) -> str:
        """
        Generate a deposit address.
        In M1, this is a placeholder. In production:
        - Use HD wallet to derive unique addresses
        - Or use a hot wallet with payment IDs
        """
        # Placeholder: generate a random-looking address
        # In reality, this should be a real Ethereum address you control
        random_hex = secrets.token_hex(20)
        return f"0x{random_hex}"
    
    async def get_order(self, order_id: int) -> Order | None:
        """Get order by ID"""
        stmt = select(Order).where(Order.id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_orders(self, user_id: int) -> list[Order]:
        """Get all orders for a user"""
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_pending_deposits(self) -> list[Order]:
        """Get all orders waiting for deposit"""
        stmt = select(Order).where(Order.status == 'deposit_wait')
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def mark_deposit_received(self, order_id: int):
        """Mark order as having received deposit"""
        try:
            order = await self.get_order(order_id)
            if order:
                order.status = 'processing'
                order.updated_at = datetime.utcnow()
                await self.session.commit()
                logger.info(f"Order {order_id} deposit received, moved to processing")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error marking deposit received: {e}", exc_info=True)
            raise
    
    async def cancel_order(self, order_id: int, user_id: int):
        """Cancel an order (only by owner)"""
        try:
            order = await self.get_order(order_id)
            
            if not order:
                raise ValueError("Order not found")
            
            if order.user_id != user_id:
                raise PermissionError("You can only cancel your own orders")
            
            if order.status in ['completed', 'cancelled']:
                raise ValueError(f"Cannot cancel order in status: {order.status}")
            
            order.status = 'cancelled'
            order.updated_at = datetime.utcnow()
            await self.session.commit()
            
            logger.info(f"Order {order_id} cancelled by user {user_id}")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error cancelling order: {e}", exc_info=True)
            raise
    
    async def process_withdrawal(self, order_id: int, admin_private_key: str, bot=None):
        """
        Process withdrawal for sell order (admin-triggered in M1).
        This builds and sends the blockchain transaction.
        
        Args:
            order_id: Order ID to process
            admin_private_key: Admin wallet private key for signing
            bot: Bot instance for sending notifications (optional)
        """
        try:
            order = await self.get_order(order_id)
            
            if not order:
                raise ValueError("Order not found")
            
            if order.type != 'sell':
                raise ValueError("Can only process withdrawal for sell orders")
            
            if order.status != 'processing':
                raise ValueError(f"Order must be in 'processing' status, currently: {order.status}")
            
            # Get wallet address
            from app.models.db.wallet import WalletAccount
            stmt = select(WalletAccount).where(WalletAccount.id == order.wallet_id)
            result = await self.session.execute(stmt)
            wallet = result.scalar_one_or_none()
            
            if not wallet:
                raise ValueError("Wallet not found for order")
            
            # Build and send blockchain transaction
            from app.blockchain.transaction_builder import TransactionBuilder
            from app.services.tx_service import TxService
            
            tx_builder = TransactionBuilder(chain_id=11155111)  # Sepolia
            
            logger.info(f"Building withdrawal transaction for order {order_id}")
            
            # Build transaction parameters
            tx_params = await tx_builder.build_withdrawal_tx(
                to_address=wallet.address,
                amount=order.amount_crypto,
                token="USDT"
            )
            
            # Sign and send transaction
            tx_hash = await tx_builder.submit_withdrawal_tx(tx_params, admin_private_key)
            
            logger.info(f"✅ Withdrawal transaction sent: {tx_hash}")
            
            # Create transaction record
            tx_service = TxService(self.session)
            await tx_service.create_transaction(
                order_id=order.id,
                tx_hash=tx_hash,
                from_address=tx_params['from'],
                to_address=wallet.address,
                amount=order.amount_crypto,
                chain_id=11155111,
                tx_type='withdrawal'
            )
            
            # Update order status
            order.status = 'completed'
            order.updated_at = datetime.utcnow()
            await self.session.commit()
            
            # Send notification to user
            if bot:
                from app.services.notification_service import NotificationService
                notif_service = NotificationService(bot, self.session)
                await notif_service.notify_withdrawal_sent(
                    user_id=order.user_id,
                    order_id=order.id,
                    tx_hash=tx_hash,
                    amount=str(order.amount_crypto)
                )
            
            logger.info(f"✅ Order {order_id} withdrawal processed successfully")
            return tx_hash
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error processing withdrawal: {e}", exc_info=True)
            raise

    async def process_hot_order(self, order_id: int, token: str = "USDT") -> Order:
        """Finalize HOT-mode order (off-chain)."""
        try:
            order = await self.get_order(order_id)
            if not order:
                raise ValueError("Order not found")

            if order.wallet_mode != "HOT":
                raise ValueError("Order is not in HOT mode")

            if order.status not in {'processing', 'pending'}:
                raise ValueError(f"Order status must be pending/processing, got {order.status}")

            hot_balance_service = HOTBalanceService(self.session)

            if order.type == 'buy':
                await hot_balance_service.update_balance(
                    user_id=order.user_id,
                    token=token,
                    delta=order.amount_crypto,
                    reason="buy_order_completed",
                )

            order.status = 'completed'
            order.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(order)

            logger.info("HOT order %s processed successfully", order_id)
            return order
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error processing HOT order: {e}", exc_info=True)
            raise

    async def _get_user_wallet(self, user_id: int, wallet_id: int) -> WalletAccount:
        stmt = select(WalletAccount).where(
            WalletAccount.id == wallet_id,
            WalletAccount.user_id == user_id
        )
        result = await self.session.execute(stmt)
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise ValueError("Wallet not found or doesn't belong to user")
        return wallet

    async def _ensure_user_hot_access(self, user_id: int) -> User:
        stmt = select(User).where(User.tg_id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if not getattr(user, "hot_access_enabled", False):
            raise PermissionError("HOT mode is not enabled for this user")
        return user

