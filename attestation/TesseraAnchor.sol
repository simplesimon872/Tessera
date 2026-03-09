// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * TesseraAnchor — timestamped attestation only.
 *
 * One job: emit a verifiable onchain event binding a snapshot hash
 * to a block timestamp. No storage. No access control. No upgrades.
 *
 * The verifiable output is the Anchored event. Anyone can query it
 * independently via Snowtrace or any Avalanche C-Chain RPC.
 *
 * Methodology v1.0 — deploy once, reuse across all epochs.
 */
contract TesseraAnchor {

    /**
     * Emitted once per epoch per handle.
     *
     * @param sender        Protocol wallet address (single signer in v1).
     * @param snapshotHash  SHA-256 of the canonical epoch snapshot JSON,
     *                      passed as bytes32. Must match the hash displayed
     *                      on the audit page exactly.
     * @param timestamp     Block timestamp at time of anchoring (Unix seconds).
     */
    event Anchored(
        address indexed sender,
        bytes32 indexed snapshotHash,
        uint256 timestamp
    );

    /**
     * Anchor a snapshot hash onchain.
     *
     * Called once per epoch per handle by the protocol wallet.
     * No state is written — the event log is the record.
     *
     * @param snapshotHash  bytes32 representation of the SHA-256 snapshot hash.
     */
    function anchor(bytes32 snapshotHash) external {
        emit Anchored(msg.sender, snapshotHash, block.timestamp);
    }
}
