"""Transaction builder for preparing and sending blockchain transactions"""

import logging
from decimal import Decimal
from eth_account import Account
from eth_account.signers.local import LocalAccount

from app.blockchain.provider import (
    get_web3,
    get_transaction_count,
    get_gas_price,
    estimate_gas
)

logger = logging.getLogger(__name__)

# ERC-20 ABI for transfer function
ERC20_TRANSFER_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# USDT contract address on Sepolia (mock - replace with actual deployed contract)
USDT_CONTRACT_SEPOLIA = "0x7169D38820dfd117C3FA1f22a697dBA58d90BA06"  # Example address


class TransactionBuilder:
    """Builder for Ethereum transactions"""
    
    def __init__(self, chain_id: int = 11155111):
        self.chain_id = chain_id
    
    async def build_eth_transfer(
        self,
        from_address: str,
        to_address: str,
        amount_eth: Decimal
    ) -> dict:
        """
        Build a raw ETH transfer transaction.
        Returns transaction parameters dict.
        """
        try:
            w3 = await get_web3(self.chain_id)
            
            # Convert amount to Wei
            amount_wei = w3.to_wei(amount_eth, 'ether')
            
            # Get nonce
            nonce = await get_transaction_count(from_address, self.chain_id)
            
            # Get gas price
            gas_price = await get_gas_price(self.chain_id)
            
            # Build transaction
            tx_params = {
                'from': from_address,
                'to': to_address,
                'value': amount_wei,
                'gas': 21000,  # Standard ETH transfer gas
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': self.chain_id
            }
            
            logger.info(f"Built ETH transfer: {amount_eth} ETH from {from_address} to {to_address}")
            return tx_params
            
        except Exception as e:
            logger.error(f"Error building ETH transfer: {e}", exc_info=True)
            raise
    
    async def build_erc20_transfer(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token_contract: str = USDT_CONTRACT_SEPOLIA
    ) -> dict:
        """
        Build an ERC-20 token transfer transaction (e.g., USDT).
        Returns transaction parameters dict.
        """
        try:
            w3 = await get_web3(self.chain_id)
            
            # Create contract instance
            contract = w3.eth.contract(
                address=w3.to_checksum_address(token_contract),
                abi=ERC20_TRANSFER_ABI
            )
            
            # Convert amount to token's smallest unit (assuming 18 decimals for simplicity)
            # For real USDT, it's 6 decimals
            amount_units = int(amount * Decimal(10**6))  # USDT has 6 decimals
            
            # Encode transfer function call
            data = contract.encode_abi('transfer', args=[
                w3.to_checksum_address(to_address),
                amount_units
            ])
            
            # Get nonce
            nonce = await get_transaction_count(from_address, self.chain_id)
            
            # Get gas price
            gas_price = await get_gas_price(self.chain_id)
            
            # Build transaction
            tx_params = {
                'from': from_address,
                'to': token_contract,
                'value': 0,
                'data': data,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': self.chain_id
            }
            
            # Estimate gas
            try:
                gas_estimate = await estimate_gas(tx_params, self.chain_id)
                tx_params['gas'] = int(gas_estimate * 1.2)  # Add 20% buffer
            except Exception as e:
                logger.warning(f"Gas estimation failed, using default: {e}")
                tx_params['gas'] = 100000  # Default gas limit for ERC-20 transfer
            
            logger.info(f"Built ERC-20 transfer: {amount} tokens from {from_address} to {to_address}")
            return tx_params
            
        except Exception as e:
            logger.error(f"Error building ERC-20 transfer: {e}", exc_info=True)
            raise
    
    async def sign_transaction(self, tx_params: dict, private_key: str) -> str:
        """
        Sign a transaction with private key.
        Returns signed raw transaction.
        """
        try:
            w3 = await get_web3(self.chain_id)
            
            # Create account from private key
            account: LocalAccount = Account.from_key(private_key)
            
            # Sign transaction
            signed_tx = account.sign_transaction(tx_params)
            
            logger.info(f"Signed transaction from {account.address}")
            return signed_tx.rawTransaction
            
        except Exception as e:
            logger.error(f"Error signing transaction: {e}", exc_info=True)
            raise
    
    async def send_raw_transaction(self, signed_raw_tx: bytes) -> str:
        """
        Send a signed raw transaction to the network.
        Returns transaction hash.
        """
        try:
            w3 = await get_web3(self.chain_id)
            
            # Send transaction
            tx_hash = await w3.eth.send_raw_transaction(signed_raw_tx)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"Sent transaction: {tx_hash_hex}")
            return tx_hash_hex
            
        except Exception as e:
            logger.error(f"Error sending transaction: {e}", exc_info=True)
            raise
    
    async def build_sign_and_send(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        private_key: str,
        token: str | None = None
    ) -> str:
        """
        Complete workflow: build, sign, and send transaction.
        Returns transaction hash.
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to send
            private_key: Private key for signing
            token: Token contract address (None for ETH)
        """
        try:
            # Build transaction
            if token:
                tx_params = await self.build_erc20_transfer(
                    from_address, to_address, amount, token
                )
            else:
                tx_params = await self.build_eth_transfer(
                    from_address, to_address, amount
                )
            
            # Sign transaction
            signed_tx = await self.sign_transaction(tx_params, private_key)
            
            # Send transaction
            tx_hash = await self.send_raw_transaction(signed_tx)
            
            logger.info(f"✅ Transaction complete: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Error in build_sign_and_send: {e}", exc_info=True)
            raise
    
    async def build_withdrawal_tx(
        self,
        to_address: str,
        amount: Decimal,
        token: str = "USDT"
    ) -> dict:
        """
        Build withdrawal transaction (for OrderService).
        This is a convenience wrapper that uses admin wallet.
        
        Returns transaction parameters ready for signing.
        """
        # TODO: Get admin wallet address from config
        admin_address = "0xYourAdminWalletAddress"  # Placeholder
        
        if token.upper() == "USDT":
            return await self.build_erc20_transfer(
                admin_address,
                to_address,
                amount,
                USDT_CONTRACT_SEPOLIA
            )
        else:
            raise ValueError(f"Unsupported token: {token}")
    
    async def submit_withdrawal_tx(
        self,
        tx_params: dict,
        private_key: str
    ) -> str:
        """
        Sign and submit a withdrawal transaction.
        Returns transaction hash.
        """
        signed_tx = await self.sign_transaction(tx_params, private_key)
        tx_hash = await self.send_raw_transaction(signed_tx)
        return tx_hash

