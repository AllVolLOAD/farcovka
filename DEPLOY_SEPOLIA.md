# Deploy VaultV2 & Registry to Sepolia

## Prereqs
- Node 18+, npm.
- Env vars:
  - `SEPOLIA_RPC_URL` (Infura/Alchemy/etc)
  - `DEPLOYER_KEY` (private key of deployer)
  - `GOVERNANCE` (multisig/timelock address)
  - `GUARDIAN` (guardian address)

## Install deps (isolated in contracts/)
```bash
cd contracts
npm install
```

## Deploy

**Option 1: Using .env file (recommended)**

The `.env` file is already created in `contracts/` with your credentials:
- SEPOLIA_RPC_URL
- DEPLOYER_KEY
- GOVERNANCE/GUARDIAN (will auto-use deployer address if not set)

Just run:
```bash
cd contracts
npm run deploy:sepolia
```

**Option 2: Using env vars inline**

If you want to override or use different addresses:
```bash
cd contracts
GOVERNANCE=0x... GUARDIAN=0x... \
SEPOLIA_RPC_URL=https://... \
DEPLOYER_KEY=0x... \
npm run deploy:sepolia
```

Outputs:
- VaultV2 address
- VaultRegistry address

## Post-deploy actions (governance TXs)
- setTokenEnabled(token, true)
- setMaxTVL(token, <limit>)
- (optional) allowMigration(targetVault, true)
- record addresses in backend/front configs.

## Notes
- Timelock/multisig wiring happens outside script; ensure governance key is timelock (if used).
- Do not commit real keys; use env only.

