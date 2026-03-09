import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("TesseraAnchor", (m) => {
  const contract = m.contract("TesseraAnchor");
  return { contract };
});