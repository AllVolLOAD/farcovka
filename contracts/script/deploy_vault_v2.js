// Hardhat deploy helper. Requires @nomicfoundation/hardhat-ethers.
// Usage:
//   npx hardhat run contracts/script/deploy_vault_v2.js --network sepolia
//
// Env:
//   GOVERNANCE=0x...  GUARDIAN=0x...  (optional, if not set, uses deployer address)
//   DEPLOYER_KEY=0x... (required for network config)

const { ethers } = require("hardhat");

async function main() {
  // Get deployer to derive address if GOVERNANCE/GUARDIAN not set
  const [deployer] = await ethers.getSigners();
  const deployerAddress = deployer.address;
  
  const gov = process.env.GOVERNANCE || deployerAddress;
  const guardian = process.env.GUARDIAN || deployerAddress;
  
  console.log("Deployer:", deployerAddress);
  console.log("Governance:", gov);
  console.log("Guardian:", guardian);

  const VaultV2 = await ethers.getContractFactory("VaultV2");
  const vault = await VaultV2.deploy(gov, guardian);
  await vault.waitForDeployment();
  console.log("VaultV2 deployed:", await vault.getAddress());

  const Registry = await ethers.getContractFactory("VaultRegistry");
  const registry = await Registry.deploy(gov);
  await registry.waitForDeployment();
  console.log("VaultRegistry deployed:", await registry.getAddress());
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

