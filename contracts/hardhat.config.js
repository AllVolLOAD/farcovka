require("@nomicfoundation/hardhat-ethers");
require("dotenv").config();

const { SEPOLIA_RPC_URL, DEPLOYER_KEY } = process.env;

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    sources: "./src",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    sepolia: {
      url: SEPOLIA_RPC_URL || "",
      accounts: DEPLOYER_KEY ? [DEPLOYER_KEY] : [],
    },
  },
  mocha: {
    timeout: 40000,
  },
};

