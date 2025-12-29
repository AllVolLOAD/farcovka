from app.models.config.blockchain import BlockchainConfig


def load_blockchain_config(blockchain_dict: dict | None) -> BlockchainConfig | None:
    """Load blockchain configuration from dict"""
    if not blockchain_dict:
        return None
    
    return BlockchainConfig(
        sepolia_rpc_url=blockchain_dict.get("sepolia_rpc_url", ""),
        vault_v2_address=blockchain_dict.get("vault_v2_address", ""),
        vault_registry_address=blockchain_dict.get("vault_registry_address"),
        chain_id=blockchain_dict.get("chain_id", 11155111),
    )

