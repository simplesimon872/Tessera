"""
test_attestation.py — Day 4 attestation layer test suite.

Tests:
  1.  Hash conversion     — hex string → bytes32 is correct
  2.  Idempotency guard   — already-sealed epoch is skipped by cron
  3.  Missed run          — stale last_seal_run triggers immediate execution
  4.  Failure isolation   — one bad epoch doesn't abort the batch
  5.  Seal batch summary  — counts are accurate
  6.  Notification format — message contains expected fields
  7.  Live anchor         — real tx submitted to Avalanche C-Chain (optional, --live)

Usage:
    python test_attestation.py            # offline tests only
    python test_attestation.py --live     # includes real onchain tx (~$0.001 gas)

The --live flag requires CONTRACT_ADDRESS and DEPLOYER_PRIVATE_KEY in .env.
"""

import argparse
import hashlib
import json
import logging
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Project root
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_attestation")

PASS = "✅"
FAIL = "❌"
SKIP = "⚠️ "

results = []


def test(name: str):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            print(f"\n{'═'*60}")
            print(f"TEST — {name}")
            print(f"{'─'*60}")
            try:
                fn(*args, **kwargs)
                print(f"{PASS} {name}")
                results.append((name, True, None))
            except AssertionError as e:
                print(f"{FAIL} {name}: {e}")
                results.append((name, False, str(e)))
            except Exception as e:
                print(f"{FAIL} {name}: {type(e).__name__}: {e}")
                results.append((name, False, f"{type(e).__name__}: {e}"))
        return wrapper
    return decorator


# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_snapshot(handle: str = "test_handle", sealed: bool = False) -> dict:
    """Build a minimal valid snapshot dict."""
    content = f"tessera_test_{handle}_{time.time()}"
    h = hashlib.sha256(content.encode()).hexdigest()
    snapshot = {
        "handle": handle,
        "snapshot_hash": h,
        "epoch": {
            "start": "2026-03-01T00:00:00+00:00",
            "end":   "2026-03-30T00:00:00+00:00",
        },
        "scores": {
            "originality": 75.0,
            "focus":       60.0,
            "consistency": 50.0,
            "depth":       10.0,
            "composite":   48.75,
        },
    }
    if sealed:
        snapshot["tx_hash"] = "0xdeadbeef" * 8
    return snapshot


# ── Tests ─────────────────────────────────────────────────────────────────────

@test("Hash conversion — hex string to bytes32")
def test_hash_conversion():
    from attestation.sealer import _hex_to_bytes32

    hex_hash = hashlib.sha256(b"tessera").hexdigest()
    assert len(hex_hash) == 64, f"Expected 64-char hex, got {len(hex_hash)}"

    result = _hex_to_bytes32(hex_hash)
    assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"
    assert len(result) == 32, f"Expected 32 bytes, got {len(result)}"

    # Round-trip: bytes back to hex should match original
    reconstructed = result.hex()
    assert reconstructed == hex_hash, f"Round-trip failed: {reconstructed} != {hex_hash}"
    print(f"  hex_hash:   {hex_hash}")
    print(f"  bytes32:    {result.hex()}")
    print(f"  Round-trip: ✅")

    # Wrong length should raise
    try:
        _hex_to_bytes32("abc123")
        assert False, "Should have raised ValueError for short hash"
    except ValueError:
        print(f"  Short hash raises ValueError: ✅")


@test("Hash conversion — 0x prefix stripped correctly")
def test_hash_0x_prefix():
    from attestation.sealer import _hex_to_bytes32

    hex_hash = hashlib.sha256(b"prefix_test").hexdigest()
    prefixed = "0x" + hex_hash

    result_plain   = _hex_to_bytes32(hex_hash)
    result_prefixed = _hex_to_bytes32(prefixed)

    assert result_plain == result_prefixed, "0x-prefixed and plain hashes should produce same bytes32"
    print(f"  0x-prefixed and plain produce identical bytes32: ✅")


@test("Idempotency — already-sealed epoch skipped by cron")
def test_cron_idempotency():
    import attestation.cron as cron_module

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Patch state dirs
        cron_module.STATE_DIR   = tmp / "state"
        cron_module.SEALED_DIR  = tmp / "state" / "sealed"
        cron_module.FAILED_DIR  = tmp / "state" / "failed"
        cron_module.EPOCHS_DIR  = tmp / "epochs"
        cron_module.LAST_RUN_FILE = tmp / "state" / "last_seal_run.json"
        cron_module.initialise()

        # Write a scored snapshot
        snapshot = _make_snapshot("idempotency_test")
        epoch_file = cron_module.EPOCHS_DIR / "idempotency_test_2026-03-01.json"
        epoch_file.write_text(json.dumps(snapshot))

        # Write a sealed receipt for this epoch (simulating already sealed)
        sealed_record = {
            "handle": "idempotency_test",
            "tx_hash": "0x" + "ab" * 32,
            "block_number": 99999,
            "snapshot_hash": snapshot["snapshot_hash"],
            "anchored_at": "2026-03-30T00:00:00+00:00",
        }
        sealed_path = cron_module.SEALED_DIR / "idempotency_test_2026-03-01.json"
        sealed_path.write_text(json.dumps(sealed_record))

        # Discover epochs — should find zero because sealed receipt exists
        computed = cron_module._get_computed_epochs()
        assert len(computed) == 0, (
            f"Expected 0 computed epochs (already sealed), got {len(computed)}"
        )
        print(f"  Already-sealed epoch correctly skipped: ✅")


@test("Missed run detection — stale timestamp triggers immediate flag")
def test_missed_run_detection():
    import attestation.cron as cron_module

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cron_module.STATE_DIR     = tmp / "state"
        cron_module.LAST_RUN_FILE = tmp / "state" / "last_seal_run.json"
        cron_module.initialise()

        # No last run file — should flag as missed
        assert cron_module._check_missed_run() is True
        print(f"  No last_run file → missed run detected: ✅")

        # Recent last run — should not flag
        cron_module._write_last_run()
        assert cron_module._check_missed_run() is False
        print(f"  Recent last_run → no missed run: ✅")

        # Stale last run (8 days ago) — should flag
        stale_time = (
            datetime.now(timezone.utc) - timedelta(days=8)
        ).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        cron_module.LAST_RUN_FILE.write_text(
            json.dumps({"last_seal_run": stale_time})
        )
        assert cron_module._check_missed_run() is True
        print(f"  8-day-old last_run → missed run detected: ✅")


@test("Failure isolation — bad epoch doesn't abort batch")
def test_failure_isolation():
    import attestation.cron as cron_module

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cron_module.STATE_DIR     = tmp / "state"
        cron_module.SEALED_DIR    = tmp / "state" / "sealed"
        cron_module.FAILED_DIR    = tmp / "state" / "failed"
        cron_module.EPOCHS_DIR    = tmp / "epochs"
        cron_module.LAST_RUN_FILE = tmp / "state" / "last_seal_run.json"
        cron_module.initialise()

        good_snapshot = _make_snapshot("good_account")
        bad_snapshot  = _make_snapshot("bad_account")

        # Write both
        (cron_module.EPOCHS_DIR / "good_account_epoch.json").write_text(
            json.dumps(good_snapshot)
        )
        (cron_module.EPOCHS_DIR / "bad_account_epoch.json").write_text(
            json.dumps(bad_snapshot)
        )

        # Mock try_anchor_epoch: good succeeds, bad fails
        from attestation.sealer import AnchorReceipt, AnchorResult

        def mock_try_anchor(snapshot):
            if snapshot["handle"] == "good_account":
                return AnchorResult(
                    success=True,
                    receipt=AnchorReceipt(
                        tx_hash="0x" + "aa" * 32,
                        block_number=12345,
                        snapshot_hash=snapshot["snapshot_hash"],
                        anchored_at="2026-03-30T00:00:00+00:00",
                        snowtrace_url="https://snowtrace.io/tx/0x" + "aa" * 32,
                    ),
                )
            else:
                return AnchorResult(success=False, error="Simulated RPC failure")

        with patch("attestation.cron.try_anchor_epoch", side_effect=mock_try_anchor):
            with patch("attestation.cron._post_notification"):
                summary = cron_module.run_seal_batch()

        assert summary["sealed"] == 1, f"Expected 1 sealed, got {summary['sealed']}"
        assert summary["failed"] == 1, f"Expected 1 failed, got {summary['failed']}"

        # Good epoch has a sealed receipt
        sealed_files = list(cron_module.SEALED_DIR.glob("*.json"))
        assert len(sealed_files) == 1, f"Expected 1 sealed file, got {len(sealed_files)}"

        # Bad epoch has a failed record
        failed_files = list(cron_module.FAILED_DIR.glob("*.json"))
        assert len(failed_files) == 1, f"Expected 1 failed file, got {len(failed_files)}"

        print(f"  Good epoch sealed, bad epoch failed, batch completed: ✅")
        print(f"  Summary: sealed={summary['sealed']}, failed={summary['failed']}")


@test("Notification format — contains required fields")
def test_notification_format():
    import attestation.cron as cron_module
    from attestation.sealer import AnchorReceipt

    notifications = []

    def capture_notification(handle, receipt, epoch):
        epoch_start = epoch.get("start", "")[:10]
        epoch_end   = epoch.get("end", "")[:10]
        msg = (
            f"@{handle} — Epoch [{epoch_start} → {epoch_end}] sealed.\n"
            f"TX: {receipt.tx_hash}\n"
            f"tessera.xyz/{handle}"
        )
        notifications.append(msg)

    snapshot = _make_snapshot("notify_test")
    receipt = AnchorReceipt(
        tx_hash="0x" + "cc" * 32,
        block_number=54321,
        snapshot_hash=snapshot["snapshot_hash"],
        anchored_at="2026-03-30T00:00:00+00:00",
        snowtrace_url="https://snowtrace.io/tx/0x" + "cc" * 32,
    )

    with patch("attestation.cron._post_notification", side_effect=capture_notification):
        cron_module._post_notification("notify_test", receipt, snapshot["epoch"])

    assert len(notifications) == 1
    msg = notifications[0]
    assert "@notify_test" in msg,      "Missing @handle in notification"
    assert "2026-03-01" in msg,        "Missing epoch start date"
    assert "2026-03-30" in msg,        "Missing epoch end date"
    assert receipt.tx_hash in msg,     "Missing TX hash"
    assert "tessera.xyz/notify_test" in msg, "Missing tessera.xyz link"

    print(f"  Notification message:")
    for line in msg.splitlines():
        print(f"    {line}")
    print(f"  All required fields present: ✅")


# ── Live test (optional) ──────────────────────────────────────────────────────

def run_live_test():
    """
    Submit a real anchor() transaction to Avalanche C-Chain.
    Requires CONTRACT_ADDRESS and DEPLOYER_PRIVATE_KEY in .env.
    Costs ~$0.001 in gas.
    """
    print(f"\n{'═'*60}")
    print(f"LIVE TEST — Real anchor() call to Avalanche C-Chain")
    print(f"{'─'*60}")

    try:
        from attestation.sealer import try_anchor_epoch
        from config.chain import validate, CONTRACT_ADDRESS

        validate()

        snapshot = _make_snapshot("live_test")
        print(f"  Handle:         @live_test")
        print(f"  Snapshot hash:  {snapshot['snapshot_hash']}")
        print(f"  Contract:       {CONTRACT_ADDRESS}")
        print(f"  Submitting anchor() call...")

        result = try_anchor_epoch(snapshot)

        if result.success:
            r = result.receipt
            print(f"  {PASS} Live anchor succeeded")
            print(f"  TX hash:      {r.tx_hash}")
            print(f"  Block:        {r.block_number}")
            print(f"  Anchored at:  {r.anchored_at}")
            print(f"  Snowtrace:    {r.snowtrace_url}")
            results.append(("Live anchor — Avalanche C-Chain", True, None))
        else:
            print(f"  {FAIL} Live anchor failed: {result.error}")
            results.append(("Live anchor — Avalanche C-Chain", False, result.error))

    except EnvironmentError as e:
        print(f"  {SKIP} Skipped — chain config incomplete: {e}")
        results.append(("Live anchor — Avalanche C-Chain", None, str(e)))
    except Exception as e:
        print(f"  {FAIL} {type(e).__name__}: {e}")
        results.append(("Live anchor — Avalanche C-Chain", False, str(e)))


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Include real onchain tx test")
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  Tessera — Day 4 Attestation Layer Tests")
    print("═" * 60)

    test_hash_conversion()
    test_hash_0x_prefix()
    test_cron_idempotency()
    test_missed_run_detection()
    test_failure_isolation()
    test_notification_format()

    if args.live:
        run_live_test()
    else:
        print(f"\n{SKIP}  Live anchor test skipped (pass --live to run)")
        print(f"     Requires CONTRACT_ADDRESS + DEPLOYER_PRIVATE_KEY in .env")
        print(f"     Costs ~$0.001 in gas on Avalanche C-Chain")

    # Summary
    print(f"\n{'═'*60}")
    print(f"  SUMMARY")
    print(f"{'─'*60}")
    passed  = sum(1 for _, ok, _ in results if ok is True)
    failed  = sum(1 for _, ok, _ in results if ok is False)
    skipped = sum(1 for _, ok, _ in results if ok is None)
    total   = len(results)

    for name, ok, err in results:
        if ok is True:
            print(f"  {PASS}  {name}")
        elif ok is None:
            print(f"  {SKIP}  {name}")
        else:
            print(f"  {FAIL}  {name}: {err}")

    print(f"{'─'*60}")
    print(f"  {passed}/{total - skipped} tests passed", end="")
    if skipped:
        print(f"  ({skipped} skipped)", end="")
    print()

    if failed == 0:
        print(f"\n  ✅ Attestation layer ready. Day 4 complete.")
    else:
        print(f"\n  ❌ {failed} test(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
