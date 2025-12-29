"""Deposit tracker for monitoring incoming blockchain transactions"""

import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.db.order import Order
from app.models.db.transaction import Transaction
from app.blockchain.provider import get_web3, get_transaction_receipt, get_block_number
from app.blockchain.vault_listener import VaultEventListener
from app.services.hot_balance_service import HOTBalanceService
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class DepositTracker:
    """Tracks deposits for pending orders"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def scan_pending_orders(self):
        """
        Scan all orders waiting for deposit and check blockchain for incoming transactions.
        This runs as a background task every 2 minutes.
        """
        try:
            cold_stmt = select(Order).where(
                Order.status == 'deposit_wait',
                Order.wallet_mode == 'COLD'
            )
            result = await self.session.execute(cold_stmt)
            cold_orders = result.scalars().all()

            hot_orders = await self._get_hot_orders_waiting()
            
            if not cold_orders and not hot_orders:
                logger.debug("No orders waiting for deposit (COLD/HOT)")
                return
            
            if cold_orders:
                logger.info(f"🔍 Scanning {len(cold_orders)} COLD orders for deposits...")
                for order in cold_orders:
                    try:
                        await self.check_order_deposit(order)
                    except Exception as e:
                        logger.error(f"Error checking deposit for order {order.id}: {e}", exc_info=True)
            
            if hot_orders:
                await self._handle_hot_orders(hot_orders)
            
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Error in scan_pending_orders: {e}", exc_info=True)
            await self.session.rollback()
    
    async def check_order_deposit(self, order: Order):
        """
        Check if deposit has been received for a specific order.
        Looks for transactions to the order's deposit_address.
        """
        if not order.deposit_address:
            logger.warning(f"Order {order.id} has no deposit address")
            return
        
        try:
            w3 = await get_web3(11155111)  # Sepolia
            
            # Get balance of deposit address
            balance_wei = await w3.eth.get_balance(order.deposit_address)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            
            # For M1, we're expecting ETH deposits (not USDT)
            # TODO: In M2/M3, add ERC-20 token tracking
            expected_amount = order.amount_crypto
            
            logger.debug(f"Order {order.id}: balance={balance_eth} ETH, expected={expected_amount}")
            
            # Check if sufficient funds received
            if Decimal(str(balance_eth)) >= expected_amount:
                logger.info(f"✅ Deposit received for order {order.id}! Amount: {balance_eth} ETH")
                
                # Update order status
                order.status = 'processing'
                
                # Create transaction record
                # Note: We'd need to scan recent blocks to get the actual tx hash
                # For simplicity in M1, we create a placeholder
                current_block = await get_block_number()
                
                tx = Transaction(
                    order_id=order.id,
                    tx_hash=f"0x{'0'*64}",  # Placeholder - need to scan blocks for real hash
                    from_address="0x0000000000000000000000000000000000000000",  # Unknown sender
                    to_address=order.deposit_address,
                    amount=expected_amount,
                    chain_id=11155111,
                    type='deposit',
                    status='confirmed',
                    confirmations=1
                )
                
                self.session.add(tx)
                
                # TODO: Trigger notification to user via bot
                logger.info(f"Order {order.id} moved to processing")
                
        except Exception as e:
            logger.error(f"Error checking deposit for order {order.id}: {e}", exc_info=True)
    
    async def scan_recent_blocks(self, address: str, from_block: int, to_block: int):
        """
        Scan recent blocks for transactions to specific address.
        More accurate than just checking balance.
        """
        w3 = await get_web3()
        transactions = []
        
        try:
            for block_num in range(from_block, to_block + 1):
                block = await w3.eth.get_block(block_num, full_transactions=True)
                
                if block and block.transactions:
                    for tx in block.transactions:
                        if tx.to and tx.to.lower() == address.lower():
                            transactions.append({
                                'hash': tx.hash.hex(),
                                'from': tx['from'],
                                'to': tx.to,
                                'value': tx.value,
                                'block': block_num
                            })
        
        except Exception as e:
            logger.error(f"Error scanning blocks {from_block}-{to_block}: {e}")
        
        return transactions

    async def _get_hot_orders_waiting(self) -> list[Order]:
        """Return HOT-mode orders that are awaiting vault events (placeholder)."""
        stmt = select(Order).where(
            Order.wallet_mode == 'HOT',
            Order.status.in_(['processing', 'deposit_wait'])
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _handle_hot_orders(self, orders: list[Order]):
        """
        Process HOT-mode orders by syncing Vault events and auto-processing eligible orders.
        """
        if not orders:
            return

        listener = VaultEventListener(self.session)
        await listener.listen_deposit_events()

        balance_service = HOTBalanceService(self.session)
        order_service = OrderService(self.session)

        for order in orders:
            if order.type != 'buy':
                continue

            has_balance = await balance_service.check_sufficient_balance(order.user_id, order.amount_crypto)
            if has_balance and order.status in {'pending', 'processing', 'deposit_wait'}:
                logger.info("Auto-processing HOT order %s after deposit sync", order.id)
                await order_service.process_hot_order(order.id)

