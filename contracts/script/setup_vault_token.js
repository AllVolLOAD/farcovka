// Script to enable USDT testnet token in VaultV2
// Usage: npx hardhat run script/setup_vault_token.js --network sepolia

const { ethers } = require("hardhat");

async function main() {
  const vaultAddr = "0xd5523C76018FA546431D0be4DDe48f389b561C09";
  const token = "0x7169D38820dfd117C3FA1f22a697dBA58d90BA06"; // USDT testnet on Sepolia
  const maxTVL = "1000000000000000000000000"; // 1,000,000 USDT testnet (18 decimals)

  console.log("Connecting to VaultV2 at:", vaultAddr);
  const VaultV2 = await ethers.getContractFactory("VaultV2");
  const vault = VaultV2.attach(vaultAddr);

  const [signer] = await ethers.getSigners();
  console.log("Using account:", signer.address);

  // Check if governance
  const governance = await vault.governance();
  if (signer.address.toLowerCase() !== governance.toLowerCase()) {
    throw new Error(`Signer ${signer.address} is not governance (${governance})`);
  }
  console.log("✓ Signer is governance");

  // Enable token
  console.log("\nEnabling token...");
  const tx1 = await vault.setTokenEnabled(token, true);
  console.log("  TX hash:", tx1.hash);
  await tx1.wait();
  console.log("  ✓ Token enabled");

  // Set maxTVL
  console.log("\nSetting maxTVL...");
  const tx2 = await vault.setMaxTVL(token, maxTVL);
  console.log("  TX hash:", tx2.hash);
  await tx2.wait();
  console.log("  ✓ MaxTVL set to 1,000,000 USDT testnet");

  // Verify
  const enabled = await vault.tokenEnabled(token);
  const tvl = await vault.maxTVL(token);
  console.log("\n✓ Verification:");
  console.log("  Token enabled:", enabled);
  console.log("  MaxTVL:", tvl.toString(), "(", ethers.formatEther(tvl), "tokens )");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

