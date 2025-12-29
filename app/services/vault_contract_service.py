"""Utilities for interacting with the HOT Vault contract via web3.py."""

import logging
from decimal import Decimal

from eth_account import Account
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract.async_contract import AsyncContractFunction

from app.blockchain.provider import get_gas_price, get_transaction_count, get_web3, _blockchain_config
from app.models.db.hot_wallet import HotWallet

logger = logging.getLogger(__name__)

VAULT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenAddress", "type": "address"},
            {"internalType": "address", "name": "initialAdmin", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "Deposit",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "Withdraw",
        "type": "event",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "newAdmin", "type": "address"}],
        "name": "setAdmin",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class VaultContractService:
    """Wraps Vault.sol interaction helpers."""

    def __init__(self, session: AsyncSession, chain_id: int = 11155111):
        self.session = session
        self.chain_id = chain_id

    async def get_vault_address(self) -> str:
        # Try DB first
        stmt = (
            select(HotWallet)
            .where(HotWallet.name == 'vault', HotWallet.is_active.is_(True))
            .order_by(HotWallet.id.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        vault = result.scalar_one_or_none()
        if vault:
            return vault.address
        
        # Fallback to config
        if _blockchain_config and _blockchain_config.vault_v2_address:
            logger.debug("Using Vault address from config (no DB entry found)")
            return _blockchain_config.vault_v2_address
        
        raise ValueError("Vault address is not configured (check DB hot_wallets or config.blockchain.vault_v2_address)")

    async def deposit_to_vault(
        self,
        from_address: str,
        private_key: str,
        amount: Decimal | int,
    ) -> str:
        """
        Execute deposit(amount) on Vault contract.

        Args:
            from_address: wallet that provides tokens (must have approved Vault).
            private_key: private key for signing transaction.
            amount: token amount (already in smallest units / wei).
        """
        contract = await self._get_contract()
        func = contract.functions.deposit(int(amount))
        tx = await self._build_transaction(func, from_address)
        signed = Account.sign_transaction(tx, private_key)
        w3 = await get_web3(self.chain_id)
        tx_hash = await w3.eth.send_raw_transaction(signed.rawTransaction)
        logger.info("Vault deposit tx submitted: %s", tx_hash.hex())
        return tx_hash.hex()

    async def withdraw_from_vault(
        self,
        admin_private_key: str,
        user_address: str,
        to_address: str,
        amount: Decimal | int,
    ) -> str:
        """Execute withdraw on Vault contract using admin key."""
        account = Account.from_key(admin_private_key)
        contract = await self._get_contract()
        func = contract.functions.withdraw(user_address, to_address, int(amount))
        tx = await self._build_transaction(func, account.address)
        signed = Account.sign_transaction(tx, admin_private_key)
        w3 = await get_web3(self.chain_id)
        tx_hash = await w3.eth.send_raw_transaction(signed.rawTransaction)
        logger.info("Vault withdrawal tx submitted: %s", tx_hash.hex())
        return tx_hash.hex()

    async def _get_contract(self):
        address = await self.get_vault_address()
        w3 = await get_web3(self.chain_id)
        return w3.eth.contract(address=address, abi=VAULT_ABI)

    async def _build_transaction(
        self,
        func: AsyncContractFunction,
        from_address: str,
    ) -> dict:
        w3 = await get_web3(self.chain_id)
        nonce = await get_transaction_count(from_address, self.chain_id)
        gas_price = await get_gas_price(self.chain_id)
        gas_estimate = await func.estimate_gas({'from': from_address})

        tx = await func.build_transaction({
            'from': from_address,
            'nonce': nonce,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'chainId': self.chain_id,
        })
        return tx

    async def get_contract(self):
        """Expose contract instance (used by listeners)."""
        return await self._get_contract()

