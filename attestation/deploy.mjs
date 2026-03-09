import hre from "hardhat";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { ethers, network } = hre;

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("═══════════════════════════════════════════");
  console.log("  TesseraAnchor — Deploy");
  console.log("═══════════════════════════════════════════");
  console.log(`  Network:   ${network.name}`);
  console.log(`  Deployer:  ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`  Balance:   ${ethers.formatEther(balance)} AVAX`);
  console.log("───────────────────────────────────────────");

  if (balance === 0n) {
    throw new Error("Deployer wallet has 0 AVAX. Fund it before deploying.");
  }

  console.log("  Deploying TesseraAnchor...");
  const TesseraAnchor = await ethers.getContractFactory("TesseraAnchor");
  const contract = await TesseraAnchor.deploy();
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  const deployTx = contract.deploymentTransaction();

  console.log(`  ✅ Deployed at: ${contractAddress}`);
  console.log(`  TX hash:        ${deployTx.hash}`);
  console.log("───────────────────────────────────────────");

  const deploymentRecord = {
    network: network.name,
    chainId: network.config.chainId,
    contractAddress,
    deployerAddress: deployer.address,
    txHash: deployTx.hash,
    deployedAt: new Date().toISOString(),
    methodologyVersion: "v1.0",
  };

  const recordPath = path.join(__dirname, `deployment_${network.name}.json`);
  fs.writeFileSync(recordPath, JSON.stringify(deploymentRecord, null, 2));
  console.log(`  Deployment record: attestation/deployment_${network.name}.json`);

  console.log("───────────────────────────────────────────");
  console.log(`  1. Add to .env:  CONTRACT_ADDRESS=${contractAddress}`);
  console.log(`  2. Snowtrace:    https://testnet.snowtrace.io/address/${contractAddress}`);
  console.log("═══════════════════════════════════════════");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});