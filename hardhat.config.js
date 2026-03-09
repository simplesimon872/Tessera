import "@nomicfoundation/hardhat-toolbox";
import { config as dotenvConfig } from "dotenv";
dotenvConfig();

const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY;
if (!DEPLOYER_PRIVATE_KEY) {
  throw new Error("DEPLOYER_PRIVATE_KEY not set in .env");
}

export default {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    avalanche: {
      type: "http",
      url: "https://api.avax.network/ext/bc/C/rpc",
      chainId: 43114,
      accounts: [`0x${DEPLOYER_PRIVATE_KEY}`],
    },
    fuji: {
      type: "http",
      url: "https://api.avax-test.network/ext/bc/C/rpc",
      chainId: 43113,
      accounts: [`0x${DEPLOYER_PRIVATE_KEY}`],
    },
  },
};