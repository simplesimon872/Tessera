"""
chain.py — Avalanche C-Chain connection config.

All chain-specific values live here. Never hardcode inline.

Required environment variables:
    DEPLOYER_PRIVATE_KEY   — protocol wallet private key (no 0x prefix)
    CONTRACT_ADDRESS       — deployed TesseraAnchor address
    AVALANCHE_RPC_URL      — optional override (defaults to public RPC)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Chain ────────────────────────────────────────────────────────────────────

CHAIN_ID         = 43114
CHAIN_NAME       = "Avalanche C-Chain"
RPC_URL          = os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
SNOWTRACE_BASE   = "https://snowtrace.io"
TX_URL_TEMPLATE  = f"{SNOWTRACE_BASE}/tx/{{tx_hash}}"

# ── Contract ─────────────────────────────────────────────────────────────────

CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
ABI_PATH         = Path(__file__).parent.parent / "attestation" / "abi.json"

# ── Wallet ───────────────────────────────────────────────────────────────────

# Private key — loaded from env, never committed to repo.
# The protocol wallet is the single signer for all anchor() calls in v1.
_RAW_KEY = os.getenv("DEPLOYER_PRIVATE_KEY", "")
PRIVATE_KEY = f"0x{_RAW_KEY}" if _RAW_KEY and not _RAW_KEY.startswith("0x") else _RAW_KEY

# ── Transaction ──────────────────────────────────────────────────────────────

# Confirmations to wait for before treating a tx as final.
# 1 is sufficient for prototype — Avalanche C-Chain finalises in ~2s.
CONFIRMATIONS_REQUIRED = 1

# Gas limit for anchor() — the function is trivially cheap (emit only).
# 100k is a safe ceiling; actual usage is ~25k.
GAS_LIMIT = 100_000


def validate():
    """Raise if any required config is missing. Call at startup."""
    errors = []
    if not PRIVATE_KEY:
        errors.append("DEPLOYER_PRIVATE_KEY not set")
    if not CONTRACT_ADDRESS:
        errors.append("CONTRACT_ADDRESS not set")
    if not ABI_PATH.exists():
        errors.append(f"ABI file not found: {ABI_PATH}")
    if errors:
        raise EnvironmentError(
            "Chain config incomplete:\n" + "\n".join(f"  • {e}" for e in errors)
        )


def snowtrace_tx_url(tx_hash: str) -> str:
    return TX_URL_TEMPLATE.format(tx_hash=tx_hash)
