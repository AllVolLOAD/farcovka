# Deployed Contracts on Sepolia

## Contract Addresses

### VaultV2
- **Address:** `0xd5523C76018FA546431D0be4DDe48f389b561C09`
- **Network:** Sepolia Testnet (Chain ID: 11155111)
- **Deployed:** 2025-12-12
- **Transaction:** See deploy output

### VaultRegistry
- **Address:** `0xC73a812F8002FB269d2bCc5d5318233a1ecedE98`
- **Network:** Sepolia Testnet (Chain ID: 11155111)
- **Deployed:** 2025-12-12
- **Transaction:** See deploy output

### Governance/Guardian
- **Address:** `0x21Eb3dddF7B8B21F5056fB686c77590d900D01E5`
- **Role:** Governance + Guardian (same address for testing)
- **Network:** Sepolia Testnet

## Enabled Tokens

### USDT Testnet
- **Token Address:** `0x7169D38820dfd117C3FA1f22a697dBA58d90BA06`
- **Enabled:** ✅ Yes
- **MaxTVL:** 1,000,000 USDT testnet
- **Setup TX:** 
  - `setTokenEnabled`: `0xcb6a791a28bfd026dcaccf4724517cb007b7cc3153ebf6cbe139f488745bfce6`
  - `setMaxTVL`: `0xca7caf1b51556d3504efd1f10defb997e354d09adb89ce1c87bdf75aa3c8dba1`

## Configuration

These addresses are configured in:
- `config/config.yaml` - backend configuration
- `contracts/.env` - deployment configuration (not in git)

## Explorer Links

- VaultV2: https://sepolia.etherscan.io/address/0xd5523C76018FA546431D0be4DDe48f389b561C09
- VaultRegistry: https://sepolia.etherscan.io/address/0xC73a812F8002FB269d2bCc5d5318233a1ecedE98
- Governance: https://sepolia.etherscan.io/address/0x21Eb3dddF7B8B21F5056fB686c77590d900D01E5
- USDT Testnet: https://sepolia.etherscan.io/address/0x7169D38820dfd117C3FA1f22a697dBA58d90BA06

