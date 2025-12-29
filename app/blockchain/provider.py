"""Web3 provider for Sepolia testnet"""

import logging
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)

# Default values (will be overridden by config)
SEPOLIA_RPC_URL = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
SEPOLIA_CHAIN_ID = 11155111

# Global config (set by set_blockchain_config)
_blockchain_config = None


def set_blockchain_config(config):
    """Set blockchain configuration (called from main.py)"""
    global SEPOLIA_RPC_URL, SEPOLIA_CHAIN_ID, _blockchain_config
    _blockchain_config = config
    if config:
        SEPOLIA_RPC_URL = config.sepolia_rpc_url
        SEPOLIA_CHAIN_ID = config.chain_id

# Global Web3 instance
_web3_instance = None


async def get_web3(chain_id: int = SEPOLIA_CHAIN_ID) -> AsyncWeb3:
    """
    Get or create Web3 instance for specified chain.
    For M1, only Sepolia is supported.
    """
    global _web3_instance
    
    if chain_id != SEPOLIA_CHAIN_ID:
        raise ValueError(f"Unsupported chain_id: {chain_id}. Only Sepolia ({SEPOLIA_CHAIN_ID}) is supported in M1.")
    
    if _web3_instance is None:
        try:
            provider = AsyncHTTPProvider(SEPOLIA_RPC_URL)
            _web3_instance = AsyncWeb3(provider)
            
            # Add POA middleware for Sepolia
            _web3_instance.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            
            # Test connection
            is_connected = await _web3_instance.is_connected()
            if not is_connected:
                logger.error("Failed to connect to Sepolia RPC")
                raise ConnectionError("Cannot connect to Sepolia RPC")
            
            logger.info(f"✅ Connected to Sepolia testnet (Chain ID: {chain_id})")
            
        except Exception as e:
            logger.error(f"Error initializing Web3: {e}")
            raise
    
    return _web3_instance


async def get_balance(address: str, chain_id: int = SEPOLIA_CHAIN_ID) -> int:
    """Get ETH balance for address in Wei"""
    w3 = await get_web3(chain_id)
    balance = await w3.eth.get_balance(address)
    return balance


async def get_block_number(chain_id: int = SEPOLIA_CHAIN_ID) -> int:
    """Get current block number"""
    w3 = await get_web3(chain_id)
    block_num = await w3.eth.block_number
    return block_num


async def get_transaction_receipt(tx_hash: str, chain_id: int = SEPOLIA_CHAIN_ID):
    """Get transaction receipt by hash"""
    w3 = await get_web3(chain_id)
    try:
        receipt = await w3.eth.get_transaction_receipt(tx_hash)
        return receipt
    except Exception:
        return None


async def get_transaction(tx_hash: str, chain_id: int = SEPOLIA_CHAIN_ID):
    """Get transaction details by hash"""
    w3 = await get_web3(chain_id)
    try:
        tx = await w3.eth.get_transaction(tx_hash)
        return tx
    except Exception:
        return None


async def estimate_gas(transaction: dict, chain_id: int = SEPOLIA_CHAIN_ID) -> int:
    """Estimate gas for transaction"""
    w3 = await get_web3(chain_id)
    gas_estimate = await w3.eth.estimate_gas(transaction)
    return gas_estimate


async def get_gas_price(chain_id: int = SEPOLIA_CHAIN_ID) -> int:
    """Get current gas price in Wei"""
    w3 = await get_web3(chain_id)
    gas_price = await w3.eth.gas_price
    return gas_price


async def get_transaction_count(address: str, chain_id: int = SEPOLIA_CHAIN_ID) -> int:
    """Get nonce for address"""
    w3 = await get_web3(chain_id)
    nonce = await w3.eth.get_transaction_count(address)
    return nonce

