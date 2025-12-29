# FarCovka Mini App

Telegram Mini App for FarCovka crypto exchange with WalletConnect integration.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file from `.env.example` and configure:
   - `VITE_API_URL`: Backend API URL
   - `VITE_WC_PROJECT_ID`: Get from https://cloud.walletconnect.com

3. Run development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Features

- WalletConnect v3 integration
- Sepolia testnet support
- Real-time exchange rates display
- Non-custodial wallet connection

## Tech Stack

- SvelteKit 2.0
- TypeScript
- WalletConnect Web3Modal v3
- Wagmi Core
- Viem
- Axios

