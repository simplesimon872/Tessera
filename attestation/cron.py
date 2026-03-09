"""
cron.py — Weekly sealing cron for Tessera.

Runs every Sunday midnight UTC. Finds all epochs with status='computed',
seals each one onchain, posts an Arena notification to the user.

Design principles:
  - Idempotent: if an epoch already has a tx_hash, it is skipped. Always.
  - Never silently drops failures: failed seals marked 'seal_failed' for retry.
  - Missed run detection: on startup, checks if last run was > 7 days ago
    and executes immediately if so.
  - One failure in a batch does not abort the rest.

Pre-DB (Day 4): state stored in JSON files on disk.
Post-Day 5:     swap in the Supabase DB calls where marked.

Usage:
    # Run once manually:
    python -m attestation.cron --run-now

    # Start the weekly scheduler:
    python -m attestation.cron
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import schedule

# Project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from attestation.sealer import try_anchor_epoch, AnchorReceipt
from config.chain import snowtrace_tx_url

logger = logging.getLogger(__name__)

# ── State files (pre-DB) ──────────────────────────────────────────────────────
# Replace these with DB calls on Day 5.

STATE_DIR         = Path(__file__).parent.parent / "cron_state"
LAST_RUN_FILE     = STATE_DIR / "last_seal_run.json"
EPOCHS_DIR        = Path(__file__).parent.parent / "scoring_output"   # scored snapshots
SEALED_DIR        = STATE_DIR / "sealed"    # completed receipts
FAILED_DIR        = STATE_DIR / "failed"    # failed attempts for retry

MISSED_RUN_THRESHOLD_DAYS = 7
ALERT_SILENCE_HOURS       = 25


# ── Startup ───────────────────────────────────────────────────────────────────

def initialise():
    """Create state directories. Safe to call multiple times."""
    for d in [STATE_DIR, SEALED_DIR, FAILED_DIR, EPOCHS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── Last-run tracking ─────────────────────────────────────────────────────────

def _read_last_run() -> datetime | None:
    if not LAST_RUN_FILE.exists():
        return None
    data = json.loads(LAST_RUN_FILE.read_text())
    return datetime.fromisoformat(data["last_seal_run"])


def _write_last_run():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    LAST_RUN_FILE.write_text(json.dumps({"last_seal_run": now}, indent=2))


def _check_missed_run() -> bool:
    """Return True if the last run was > MISSED_RUN_THRESHOLD_DAYS ago."""
    last = _read_last_run()
    if last is None:
        logger.warning("No last_seal_run found — first run or state lost.")
        return True
    age = datetime.now(timezone.utc) - last
    if age > timedelta(days=MISSED_RUN_THRESHOLD_DAYS):
        logger.warning(
            f"Missed run detected: last seal was {age.days}d {age.seconds//3600}h ago. "
            f"Executing immediately."
        )
        return True
    return False


# ── Epoch discovery (pre-DB) ──────────────────────────────────────────────────
# Day 5: replace with DB query:
#   SELECT * FROM epochs WHERE status = 'computed'

def _get_computed_epochs() -> list[dict]:
    """
    Load all scored snapshots that haven't been sealed yet.

    File convention: scoring_output/{handle}_{epoch_start}.json
    A snapshot is 'computed' if it has a 'snapshot_hash' and no 'tx_hash'.
    """
    computed = []
    for path in EPOCHS_DIR.glob("*.json"):
        try:
            snapshot = json.loads(path.read_text())
            if "snapshot_hash" not in snapshot:
                continue
            if "tx_hash" in snapshot and snapshot["tx_hash"]:
                logger.debug(f"Already sealed, skipping: {path.name}")
                continue
            # Check not already in sealed directory
            handle = snapshot.get("handle", "")
            epoch_start = snapshot.get("epoch", {}).get("start", "")[:10]  # date part
            sealed_path = SEALED_DIR / f"{handle}_{epoch_start}.json"
            if sealed_path.exists():
                logger.debug(f"Sealed receipt exists, skipping: {path.name}")
                continue
            snapshot["_source_path"] = str(path)
            computed.append(snapshot)
        except Exception as e:
            logger.error(f"Failed to load epoch file {path.name}: {e}")
    return computed


# ── Status updates (pre-DB) ───────────────────────────────────────────────────
# Day 5: replace with:
#   UPDATE epochs SET status='sealed' WHERE id=epoch_id
#   INSERT INTO anchors (epoch_id, tx_hash, block_number, snapshot_hash, anchored_at)

def _mark_sealed(snapshot: dict, receipt: AnchorReceipt):
    handle = snapshot.get("handle", "unknown")
    epoch_start = snapshot.get("epoch", {}).get("start", "")[:10]
    sealed_record = {
        "handle":        handle,
        "epoch_start":   snapshot.get("epoch", {}).get("start"),
        "epoch_end":     snapshot.get("epoch", {}).get("end"),
        "snapshot_hash": receipt.snapshot_hash,
        "tx_hash":       receipt.tx_hash,
        "block_number":  receipt.block_number,
        "anchored_at":   receipt.anchored_at,
        "snowtrace_url": receipt.snowtrace_url,
    }
    path = SEALED_DIR / f"{handle}_{epoch_start}.json"
    path.write_text(json.dumps(sealed_record, indent=2))
    logger.info(f"Sealed record written: {path.name}")


def _mark_failed(snapshot: dict, error: str):
    handle = snapshot.get("handle", "unknown")
    epoch_start = snapshot.get("epoch", {}).get("start", "")[:10]
    failed_record = {
        "handle":      handle,
        "epoch_start": snapshot.get("epoch", {}).get("start"),
        "epoch_end":   snapshot.get("epoch", {}).get("end"),
        "error":       error,
        "failed_at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    }
    path = FAILED_DIR / f"{handle}_{epoch_start}.json"
    path.write_text(json.dumps(failed_record, indent=2))
    logger.warning(f"Failure record written: {path.name}")


# ── Arena notification ────────────────────────────────────────────────────────
# Day 6: wire up the real Arena API post here.
# For Day 4, this logs what the notification would say.

def _post_notification(handle: str, receipt: AnchorReceipt, epoch: dict):
    epoch_start = epoch.get("start", "")[:10]
    epoch_end   = epoch.get("end", "")[:10]
    message = (
        f"@{handle} — Epoch [{epoch_start} → {epoch_end}] sealed.\n"
        f"TX: {receipt.tx_hash}\n"
        f"tessera.xyz/{handle}"
    )
    # TODO Day 6: POST to Arena Agents API
    logger.info(f"[Arena notification — stub] {message}")


# ── Core seal loop ────────────────────────────────────────────────────────────

def run_seal_batch() -> dict:
    """
    Seal all computed epochs. Returns a summary dict.

    Called by the weekly scheduler and by --run-now.
    Idempotent: safe to call multiple times on the same epoch.
    One failure does not abort the rest of the batch.
    """
    run_start = datetime.now(timezone.utc)
    logger.info("═══════════════════════════════════════════")
    logger.info(f"  Tessera seal batch starting | {run_start.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    logger.info("═══════════════════════════════════════════")

    epochs = _get_computed_epochs()
    logger.info(f"  Epochs to seal: {len(epochs)}")

    if not epochs:
        logger.info("  Nothing to seal. Batch complete.")
        _write_last_run()
        return {"sealed": 0, "failed": 0, "skipped": 0}

    sealed = 0
    failed = 0

    for snapshot in epochs:
        handle = snapshot.get("handle", "unknown")
        epoch = snapshot.get("epoch", {})
        epoch_start = epoch.get("start", "")[:10]

        logger.info(f"───────────────────────────────────────────")
        logger.info(f"  Sealing @{handle} | epoch_start={epoch_start}")

        result = try_anchor_epoch(snapshot)

        if result.success:
            _mark_sealed(snapshot, result.receipt)
            _post_notification(handle, result.receipt, epoch)
            sealed += 1
            logger.info(
                f"  ✅ @{handle} sealed | "
                f"tx={result.receipt.tx_hash[:18]}… | "
                f"block={result.receipt.block_number}"
            )
        else:
            _mark_failed(snapshot, result.error)
            failed += 1
            logger.error(f"  ❌ @{handle} failed | {result.error}")

        # Brief pause between transactions — avoid nonce collisions
        time.sleep(2)

    _write_last_run()

    run_end = datetime.now(timezone.utc)
    duration = (run_end - run_start).seconds

    logger.info("═══════════════════════════════════════════")
    logger.info(f"  Seal batch complete | {duration}s")
    logger.info(f"  Sealed: {sealed} | Failed: {failed} | Total: {len(epochs)}")
    logger.info("═══════════════════════════════════════════")

    if failed > 0:
        logger.warning(
            f"{failed} epoch(s) failed to seal. "
            f"They are marked 'seal_failed' and will retry on the next run."
        )

    return {"sealed": sealed, "failed": failed, "skipped": 0}


# ── Scheduler ─────────────────────────────────────────────────────────────────

def start_scheduler():
    """
    Start the weekly cron. Runs every Sunday at midnight UTC.

    Also checks for missed runs on startup and executes immediately if needed.
    Runs a 25-hour silence check every hour.
    """
    logger.info("Tessera seal cron starting.")

    # Missed run check
    if _check_missed_run():
        logger.info("Executing missed run immediately.")
        run_seal_batch()

    # Weekly schedule — every Sunday midnight UTC
    schedule.every().sunday.at("00:00").do(run_seal_batch)

    # Hourly silence check
    schedule.every().hour.do(_check_silence)

    logger.info("Scheduler running. Next seal: Sunday 00:00 UTC.")
    logger.info("Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)


def _check_silence():
    """Alert if cron has not run within ALERT_SILENCE_HOURS."""
    last = _read_last_run()
    if last is None:
        return
    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    if age_hours > ALERT_SILENCE_HOURS:
        logger.critical(
            f"ALERT: Seal cron has not run in {age_hours:.1f} hours "
            f"(threshold: {ALERT_SILENCE_HOURS}h). Investigate immediately."
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Tessera seal cron")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Execute one seal batch immediately and exit (don't start scheduler)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    initialise()

    if args.run_now:
        logger.info("--run-now flag set. Executing single batch.")
        summary = run_seal_batch()
        print(f"\nBatch complete: {summary}")
    else:
        start_scheduler()


if __name__ == "__main__":
    main()
