"""
sealer.py — Anchor a scored epoch snapshot onchain.

Public interface:
    anchor_epoch(snapshot: dict) -> AnchorReceipt

The sealer:
    1. Converts the canonical snapshot hash (hex string) to bytes32
    2. Builds and signs a transaction from the protocol wallet
    3. Submits to Avalanche C-Chain and waits for confirmation
    4. Returns an AnchorReceipt with tx_hash, block_number, anchored_at

The snapshot hash stored in the receipt must exactly match what the
audit page displays. The audit page derives it from snapshot_json —
the two must be identical or verification fails.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.chain import (
    RPC_URL,
    CONTRACT_ADDRESS,
    ABI_PATH,
    PRIVATE_KEY,
    CHAIN_ID,
    CONFIRMATIONS_REQUIRED,
    GAS_LIMIT,
    validate as validate_chain_config,
    snowtrace_tx_url,
)

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class AnchorReceipt:
    """Returned by anchor_epoch() on success."""
    tx_hash:       str        # 0x-prefixed hex string
    block_number:  int
    snapshot_hash: str        # hex string — matches audit page display
    anchored_at:   str        # ISO 8601, UTC, no milliseconds
    snowtrace_url: str        # direct link for audit page


@dataclass
class AnchorResult:
    """Wraps success or failure without raising."""
    success:  bool
    receipt:  Optional[AnchorReceipt] = None
    error:    Optional[str] = None


# ── Connection ───────────────────────────────────────────────────────────────

def _connect() -> Web3:
    """Connect to Avalanche C-Chain. Raises on failure."""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    # Avalanche C-Chain uses POA-style extra data in some blocks
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Avalanche C-Chain RPC: {RPC_URL}")
    logger.info(f"Connected to Avalanche C-Chain | chainId={w3.eth.chain_id} | block={w3.eth.block_number}")
    return w3


def _load_contract(w3: Web3):
    """Load the TesseraAnchor contract instance."""
    abi = json.loads(ABI_PATH.read_text())
    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi,
    )


# ── Hash conversion ───────────────────────────────────────────────────────────

def _hex_to_bytes32(hex_hash: str) -> bytes:
    """
    Convert a 64-char hex string (SHA-256 output) to bytes32.

    The canonical_hash() in scoring/engine.py returns a hex string.
    Solidity bytes32 needs raw bytes. This is the bridge.
    """
    clean = hex_hash.removeprefix("0x")
    if len(clean) != 64:
        raise ValueError(
            f"Expected 64-char hex hash, got {len(clean)} chars: {clean[:16]}…"
        )
    return bytes.fromhex(clean)


# ── Core anchor function ──────────────────────────────────────────────────────

def anchor_epoch(snapshot: dict) -> AnchorReceipt:
    """
    Anchor a scored epoch snapshot onchain.

    Args:
        snapshot: The full canonical snapshot dict as produced by
                  scoring/engine.py. Must contain 'snapshot_hash' key.

    Returns:
        AnchorReceipt with tx_hash, block_number, snapshot_hash, anchored_at.

    Raises:
        KeyError:        If snapshot missing required fields.
        ValueError:      If snapshot_hash is malformed.
        ConnectionError: If cannot connect to RPC.
        Exception:       On tx submission or confirmation failure.
    """
    validate_chain_config()

    snapshot_hash_hex = snapshot["snapshot_hash"]
    handle = snapshot.get("handle", "unknown")
    epoch_start = snapshot.get("epoch", {}).get("start", "unknown")
    epoch_end = snapshot.get("epoch", {}).get("end", "unknown")

    logger.info(
        f"Anchoring epoch | @{handle} | {epoch_start} → {epoch_end} | "
        f"hash={snapshot_hash_hex[:16]}…"
    )

    # Connect
    w3 = _connect()
    contract = _load_contract(w3)
    account = w3.eth.account.from_key(PRIVATE_KEY)

    # Convert hash
    hash_bytes32 = _hex_to_bytes32(snapshot_hash_hex)

    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    txn = contract.functions.anchor(hash_bytes32).build_transaction({
        "chainId": CHAIN_ID,
        "from":    account.address,
        "nonce":   nonce,
        "gas":     GAS_LIMIT,
        "gasPrice": gas_price,
    })

    # Sign and submit
    signed = account.sign_transaction(txn)
    tx_hash_bytes = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = tx_hash_bytes.hex()
    if not tx_hash_hex.startswith("0x"):
        tx_hash_hex = "0x" + tx_hash_hex

    logger.info(f"TX submitted | hash={tx_hash_hex}")

    # Wait for confirmation
    receipt = _wait_for_receipt(w3, tx_hash_bytes, handle)

    anchored_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    anchor_receipt = AnchorReceipt(
        tx_hash=tx_hash_hex,
        block_number=receipt["blockNumber"],
        snapshot_hash=snapshot_hash_hex,
        anchored_at=anchored_at,
        snowtrace_url=snowtrace_tx_url(tx_hash_hex),
    )

    logger.info(
        f"✅ Epoch sealed | @{handle} | "
        f"block={receipt['blockNumber']} | "
        f"tx={tx_hash_hex[:18]}… | "
        f"snowtrace={anchor_receipt.snowtrace_url}"
    )

    return anchor_receipt


def _wait_for_receipt(w3: Web3, tx_hash_bytes: bytes, handle: str, timeout: int = 120) -> dict:
    """
    Poll for transaction receipt until confirmed or timeout.

    Avalanche C-Chain typically confirms in ~2 seconds.
    Timeout of 120s is generous — alert if we ever hit it.
    """
    start = time.time()
    poll_interval = 2  # seconds

    while time.time() - start < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash_bytes)
            if receipt is not None:
                if receipt["status"] == 0:
                    raise Exception(
                        f"Transaction reverted | @{handle} | "
                        f"tx={tx_hash_bytes.hex()[:18]}…"
                    )
                logger.info(
                    f"TX confirmed | @{handle} | "
                    f"block={receipt['blockNumber']} | "
                    f"gasUsed={receipt['gasUsed']}"
                )
                return receipt
        except Exception as e:
            if "reverted" in str(e).lower():
                raise
            # Transient RPC error — keep polling
            logger.warning(f"Receipt poll error (will retry): {e}")

        time.sleep(poll_interval)

    raise TimeoutError(
        f"No confirmation after {timeout}s | @{handle} | "
        f"tx={tx_hash_bytes.hex()[:18]}…"
    )


# ── Safe wrapper ─────────────────────────────────────────────────────────────

def try_anchor_epoch(snapshot: dict) -> AnchorResult:
    """
    anchor_epoch() wrapped in a result type — never raises.

    Use this in the cron to ensure one failure doesn't abort the batch.
    """
    try:
        receipt = anchor_epoch(snapshot)
        return AnchorResult(success=True, receipt=receipt)
    except Exception as e:
        handle = snapshot.get("handle", "unknown")
        logger.error(f"Seal failed | @{handle} | {e}", exc_info=True)
        return AnchorResult(success=False, error=str(e))


# ── CLI test helper ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Quick sanity test — submit a real anchor() call with a dummy hash.

    Usage:
        python -m attestation.sealer

    Requires CONTRACT_ADDRESS and DEPLOYER_PRIVATE_KEY in .env.
    Will submit a real transaction and cost a small amount of gas (~$0.001).
    """
    import hashlib
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    dummy_snapshot = {
        "handle": "test_sealer",
        "snapshot_hash": hashlib.sha256(b"tessera_sealer_test").hexdigest(),
        "epoch": {
            "start": "2026-03-01T00:00:00+00:00",
            "end":   "2026-03-30T00:00:00+00:00",
        },
    }

    print(f"\nTest snapshot hash: {dummy_snapshot['snapshot_hash']}")
    print("Submitting anchor() call to Avalanche C-Chain...\n")

    result = try_anchor_epoch(dummy_snapshot)

    if result.success:
        r = result.receipt
        print(f"✅ Success")
        print(f"   TX hash:      {r.tx_hash}")
        print(f"   Block:        {r.block_number}")
        print(f"   Anchored at:  {r.anchored_at}")
        print(f"   Snowtrace:    {r.snowtrace_url}")
    else:
        print(f"❌ Failed: {result.error}")
