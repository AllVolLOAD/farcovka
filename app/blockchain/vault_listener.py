import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class VaultListener:
    """Processes Vault events idempotently via injected DAO layer."""

    def __init__(
        self,
        upsert_deposit: Callable[[str, str, int], Awaitable[None]],
        upsert_withdraw: Callable[[str, str, int], Awaitable[None]],
        upsert_emergency: Callable[[str, str, int], Awaitable[None]],
        upsert_migrate: Callable[[str, str, int, str], Awaitable[None]],
    ):
        self.upsert_deposit = upsert_deposit
        self.upsert_withdraw = upsert_withdraw
        self.upsert_emergency = upsert_emergency
        self.upsert_migrate = upsert_migrate

    async def process_log(self, log: dict):
        event = log.get("event")
        args = log.get("args", {})
        if event == "Deposit":
            await self.upsert_deposit(args["user"], args["token"], args["amount"])
        elif event == "Withdraw":
            await self.upsert_withdraw(args["user"], args["token"], args["amount"])
        elif event == "EmergencyWithdraw":
            await self.upsert_emergency(args["user"], args["token"], args["amount"])
        elif event == "Migrated":
            await self.upsert_migrate(args["user"], args["token"], args["amount"], args["targetVault"])
        else:
            logger.debug("skip event %s", event)
"""Background listener for Vault contract events."""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.provider import get_block_number, get_web3
from app.models.db.wallet import WalletAccount
from app.services.hot_balance_service import HOTBalanceService
from app.services.vault_contract_service import VaultContractService

logger = logging.getLogger(__name__)


class VaultEventListener:
    """Polls Vault contract events and syncs balances."""

    def __init__(
        self,
        session: AsyncSession,
        chain_id: int = 11155111,
        token_decimals: int = 6,  # USDT on Sepolia uses 6 decimals
        lookback_blocks: int = 128,
    ):
        self.session = session
        self.chain_id = chain_id
        self.token_decimals = token_decimals
        self.lookback_blocks = lookback_blocks
        self._last_processed_block: int | None = None
        self.vault_service = VaultContractService(session, chain_id)
        self.balance_service = HOTBalanceService(session)

    async def listen_deposit_events(self):
        await self._process_events(event_name='Deposit')

    async def listen_withdraw_events(self):
        await self._process_events(event_name='Withdraw')

    async def listen_all(self):
        await self.listen_deposit_events()
        await self.listen_withdraw_events()

    async def _process_events(self, event_name: str):
        contract = await self.vault_service.get_contract()
        current_block = await get_block_number(self.chain_id)

        from_block = self._last_processed_block
        if from_block is None:
            from_block = max(current_block - self.lookback_blocks, 0)

        try:
            event_coro = getattr(contract.events, event_name)
        except AttributeError:
            logger.warning("Vault contract has no event %s", event_name)
            return

        try:
            logs = await event_coro().get_logs(fromBlock=from_block, toBlock=current_block)
        except Exception as exc:
            logger.error("Failed to fetch %s events: %s", event_name, exc, exc_info=True)
            return

        logger.debug("Processing %s %s events (from %s to %s)", len(logs), event_name, from_block, current_block)
        for log in logs:
            await self._handle_event(event_name, log['args'])

        self._last_processed_block = current_block + 1

    async def _handle_event(self, event_name: str, args: dict):
        if event_name == 'Deposit':
            await self._handle_deposit(args)
        elif event_name == 'Withdraw':
            await self._handle_withdraw(args)

    async def _handle_deposit(self, args: dict):
        user_address = args.get('user')
        amount_raw = int(args.get('amount', 0))
        user_id = await self._resolve_user_id(user_address)

        if not user_id:
            logger.warning("Deposit event for unknown address %s", user_address)
            return

        amount = self._convert_amount(amount_raw)
        await self.balance_service.update_balance(
            user_id=user_id,
            token='USDT',
            delta=amount,
            reason='vault_deposit',
        )
        logger.info("Deposit event processed for %s amount=%s", user_address, amount)

    async def _handle_withdraw(self, args: dict):
        # Withdrawals already deduct balance during request; we log to confirm
        user_address = args.get('user')
        to_address = args.get('to')
        amount = args.get('amount')
        logger.info("Withdraw event detected user=%s to=%s amount=%s", user_address, to_address, amount)

    async def _resolve_user_id(self, address: str) -> int | None:
        if not address:
            return None

        stmt = select(WalletAccount).where(WalletAccount.address.ilike(address))
        result = await self.session.execute(stmt)
        wallet = result.scalar_one_or_none()
        if wallet:
            return wallet.user_id
        return None

    def _convert_amount(self, raw_amount: int) -> Decimal:
        factor = Decimal(10) ** self.token_decimals
        return Decimal(raw_amount) / factor

