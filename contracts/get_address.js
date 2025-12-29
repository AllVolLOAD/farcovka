// Helper script to get Ethereum address from private key
// Usage: node get_address.js <private_key>

const { ethers } = require("ethers");

const privateKey = process.argv[2] || process.env.DEPLOYER_KEY;

if (!privateKey) {
  console.error("Usage: node get_address.js <private_key>");
  console.error("Or set DEPLOYER_KEY env var");
  process.exit(1);
}

try {
  const wallet = new ethers.Wallet(privateKey);
  console.log("Address:", wallet.address);
  console.log("Private key:", privateKey);
} catch (e) {
  console.error("Error:", e.message);
  process.exit(1);
}

