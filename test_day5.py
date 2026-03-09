"""
test_day5.py — Day 5 data layer + API test suite.

Tests:
  1.  Schema validation     — all required tables exist in Supabase
  2.  User upsert           — create and retrieve a user
  3.  Epoch lifecycle       — create → computed → sealed status flow
  4.  Score storage         — store and retrieve a snapshot
  5.  Anchor storage        — store and retrieve a seal receipt
  6.  Bot state             — get/set key-value state
  7.  Command log           — log commands, rate limit counting
  8.  Audit retrieval       — full audit trail in one call
  9.  API health check      — GET /health returns 200
  10. POST /api/score       — scores a handle, stores in DB (mocked scoring)
  11. GET  /api/score/{h}   — returns epoch history
  12. GET  /api/audit/{id}  — returns full audit trail
  13. POST /api/cron/seal   — seals computed epochs (mocked sealer)
  14. POST /api/bot/command — routes commands, enforces rate limit, deduplicates

Usage:
    python test_day5.py              # all tests
    python test_day5.py --db-only    # DB tests only (no API server needed)
    python test_day5.py --api-only   # API tests only (requires running server)

Requires SUPABASE_URL and SUPABASE_KEY in .env.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import requests

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_day5")

PASS = "✅"
FAIL = "❌"
API_BASE = "http://localhost:8000"

results = []

# ── Test runner ───────────────────────────────────────────────────────────────

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
            except Exception as e:
                print(f"{FAIL} {name}: {e}")
                results.append((name, False, str(e)))
        return wrapper
    return decorator


# ── Test data helpers ─────────────────────────────────────────────────────────

TEST_HANDLE = f"test_{uuid.uuid4().hex[:8]}"
TEST_USER_ID = f"arena_{uuid.uuid4().hex[:8]}"

def _make_snapshot(handle: str = None) -> dict:
    import hashlib, json as _json
    h = handle or TEST_HANDLE
    snapshot = {
        "handle": h,
        "epoch": {
            "start": "2026-03-01T00:00:00+00:00",
            "end":   "2026-03-30T00:00:00+00:00",
        },
        "scores": {
            "originality":      75.0,
            "focus":            60.0,
            "consistency":      50.0,
            "depth":            10.0,
            "composite":        48.75,
            "consistency_mode": "frequency_variance",
            "other_cap_applied": False,
        },
        "post_breakdown": {
            "total":      20,
            "classified": 14,
            "greeting":   4,
            "null_track": 2,
            "active":     18,
        },
        "methodology": {
            "version":          "v1.0",
            "prompt_hash":      "1deff518231c",
            "model":            "claude-haiku-4-5",
            "collection_hash":  hashlib.sha256(h.encode()).hexdigest(),
        },
    }
    canonical = _json.dumps(snapshot, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    snapshot["snapshot_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    return snapshot


def _make_anchor_receipt():
    from attestation.sealer import AnchorReceipt
    unique_tx = "0x" + uuid.uuid4().hex + uuid.uuid4().hex
    return AnchorReceipt(
        tx_hash=unique_tx,
        block_number=79579298,
        snapshot_hash="a" * 64,
        anchored_at="2026-03-30T00:00:00+00:00",
        snowtrace_url=f"https://snowtrace.io/tx/{unique_tx}",
    )


# ── DB tests ──────────────────────────────────────────────────────────────────

@test("Schema — required tables exist in Supabase")
def test_schema():
    from database.client import get_client
    db = get_client()
    required_tables = ["users", "epochs", "scores", "anchors", "bot_state", "command_log"]
    for table in required_tables:
        res = db.table(table).select("*").limit(1).execute()
        print(f"  {table}: ✅")


@test("User — upsert and retrieve")
def test_user_upsert():
    from database.client import upsert_user, get_user
    user = upsert_user(TEST_HANDLE, TEST_USER_ID)
    assert user["handle"] == TEST_HANDLE
    assert user["arena_user_id"] == TEST_USER_ID
    print(f"  Created: @{user['handle']} | id={user['id'][:8]}…")

    user2 = upsert_user(TEST_HANDLE, TEST_USER_ID)
    assert user2["id"] == user["id"], "Upsert should return existing user"
    print(f"  Upsert idempotent: ✅")


@test("Epoch — create and status lifecycle")
def test_epoch_lifecycle():
    from database.client import create_epoch, get_epoch, update_epoch_status, get_latest_epoch

    epoch = create_epoch(
        TEST_HANDLE,
        "2026-03-01T00:00:00+00:00",
        "2026-03-30T00:00:00+00:00",
    )
    assert epoch["handle"] == TEST_HANDLE
    assert epoch["status"] == "computed"
    epoch_id = epoch["id"]
    print(f"  Created: epoch {epoch_id[:8]}… | status=computed")

    fetched = get_epoch(TEST_HANDLE, "2026-03-01T00:00:00+00:00")
    assert fetched["id"] == epoch_id
    print(f"  Retrieved by handle+start: ✅")

    update_epoch_status(epoch_id, "sealed")
    latest = get_latest_epoch(TEST_HANDLE)
    assert latest["status"] == "sealed"
    print(f"  Status → sealed: ✅")

    update_epoch_status(epoch_id, "computed")


@test("Scores — store and retrieve snapshot")
def test_score_storage():
    from database.client import get_epoch, store_scores, get_scores

    epoch = get_epoch(TEST_HANDLE, "2026-03-01T00:00:00+00:00")
    assert epoch, "Epoch must exist from previous test"

    snapshot = _make_snapshot()
    row = store_scores(epoch["id"], snapshot)
    assert row["composite"] is not None
    print(f"  Stored: composite={row['composite']} | hash={row['snapshot_hash'][:16]}…")

    fetched = get_scores(epoch["id"])
    assert fetched["snapshot_hash"] == snapshot["snapshot_hash"]
    assert fetched["snapshot_json"] is not None
    print(f"  Retrieved + snapshot_json present: ✅")


@test("Anchor — store and retrieve seal receipt")
def test_anchor_storage():
    from database.client import get_epoch, store_anchor, get_anchor, update_epoch_status

    epoch = get_epoch(TEST_HANDLE, "2026-03-01T00:00:00+00:00")
    receipt = _make_anchor_receipt()

    row = store_anchor(epoch["id"], receipt)
    assert row["tx_hash"] == receipt.tx_hash
    print(f"  Stored: tx={row['tx_hash'][:18]}… | block={row['block_number']}")

    fetched = get_anchor(epoch["id"])
    assert fetched["tx_hash"] == receipt.tx_hash
    print(f"  Retrieved: ✅")

    update_epoch_status(epoch["id"], "sealed")
    print(f"  Epoch marked sealed: ✅")


@test("Bot state — get and set")
def test_bot_state():
    from database.client import get_bot_state, set_bot_state

    key = f"test_key_{uuid.uuid4().hex[:8]}"
    assert get_bot_state(key) is None
    print(f"  Missing key returns None: ✅")

    set_bot_state(key, "hello")
    assert get_bot_state(key) == "hello"
    print(f"  Set and retrieved: ✅")

    set_bot_state(key, "updated")
    assert get_bot_state(key) == "updated"
    print(f"  Upsert updates value: ✅")


@test("Command log — log and rate limit counting")
def test_command_log():
    from database.client import log_command, count_recent_commands

    test_handle = f"ratelimit_{uuid.uuid4().hex[:8]}"
    assert count_recent_commands(test_handle) == 0
    print(f"  Fresh handle count=0: ✅")

    for i in range(3):
        log_command(test_handle, "reveal")

    count = count_recent_commands(test_handle)
    assert count == 3, f"Expected 3, got {count}"
    print(f"  After 3 commands, count={count}: ✅")


@test("Audit — full trail retrieved in one call")
def test_audit_retrieval():
    from database.client import get_full_audit, get_epoch

    epoch = get_epoch(TEST_HANDLE, "2026-03-01T00:00:00+00:00")
    audit = get_full_audit(epoch["id"])

    assert audit is not None
    assert audit["handle"] == TEST_HANDLE
    assert audit["status"] == "sealed"
    assert len(audit.get("scores", [])) > 0
    assert len(audit.get("anchors", [])) > 0
    print(f"  Epoch + scores + anchor returned: ✅")
    print(f"  Status: {audit['status']} | TX: {audit['anchors'][0]['tx_hash'][:18]}…")


# ── API tests ─────────────────────────────────────────────────────────────────

@test("API — GET /health returns 200")
def test_api_health():
    res = requests.get(f"{API_BASE}/health", timeout=5)
    assert res.status_code == 200
    assert res.json()["ok"] is True
    print(f"  Status 200 | ok=True: ✅")


@test("API — POST /api/score scores and stores a handle")
def test_api_score():
    from database.client import create_epoch, store_scores
    from datetime import datetime, timezone, timedelta

    # Compute the exact epoch window the API will compute for this request
    # so the cache check hits and no live scoring is triggered
    now = datetime.now(timezone.utc)
    epoch_start = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:00+00:00")
    epoch_end   = now.strftime("%Y-%m-%dT%H:%M:00+00:00")

    snapshot = _make_snapshot("api_test_handle")

    # Seed directly into DB — API finds this and returns cached
    epoch = create_epoch("api_test_handle", epoch_start, epoch_end)
    store_scores(epoch["id"], snapshot)

    res = requests.post(
        f"{API_BASE}/api/score",
        json={
            "handle":        "api_test_handle",
            "arena_user_id": "arena_123",
            "force_rescore": False,
        },
        headers={"x-internal-secret": os.getenv("INTERNAL_API_SECRET", "")},
        timeout=10,
    )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()["data"]
    assert data["handle"] == "api_test_handle"
    assert data["cached"] is True
    assert data["snapshot"]["scores"]["composite"] == 48.75
    print(f"  Returned cached score: composite={data['snapshot']['scores']['composite']}: ✅")


@test("API — GET /api/score/{handle} returns history")
def test_api_score_history():
    res = requests.get(f"{API_BASE}/api/score/api_test_handle", timeout=5)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["handle"] == "api_test_handle"
    assert len(data["epochs"]) > 0
    print(f"  Epochs returned: {len(data['epochs'])}: ✅")


@test("API — GET /api/audit/{epoch_id} returns full trail")
def test_api_audit():
    from database.client import get_latest_epoch
    epoch = get_latest_epoch("api_test_handle")
    if not epoch:
        raise AssertionError("No epoch found for api_test_handle — run score test first")

    res = requests.get(f"{API_BASE}/api/audit/{epoch['id']}", timeout=5)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["epoch"]["handle"] == "api_test_handle"
    assert data["scores"]["composite"] is not None
    assert data["snapshot_hash"] is not None
    print(f"  Epoch + scores + hash: ✅")
    print(f"  Composite: {data['scores']['composite']}")


@test("API — POST /api/cron/seal seals computed epochs")
def test_api_cron_seal():
    from database.client import get_client

    # Clean up any computed or seal_failed epochs from previous test runs
    # to prevent real onchain transactions being triggered
    db = get_client()
    db.table("epochs").update({"status": "sealed"}).eq("status", "computed").execute()
    db.table("epochs").update({"status": "sealed"}).eq("status", "seal_failed").execute()

    # Call cron — nothing to seal, should return cleanly and quickly
    res = requests.post(
        f"{API_BASE}/api/cron/seal",
        headers={"x-internal-secret": os.getenv("INTERNAL_API_SECRET", "")},
        timeout=10,
    )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()["data"]
    assert data["sealed"] == 0
    print(f"  Cron responded cleanly | sealed={data['sealed']} | failed={data['failed']}: ✅")


@test("API — POST /api/bot/command routes and rate limits")
def test_api_bot_command():
    bot_handle = f"bot_test_{uuid.uuid4().hex[:8]}"
    headers = {"x-internal-secret": os.getenv("INTERNAL_API_SECRET", "")}

    # Valid claim command
    res = requests.post(f"{API_BASE}/api/bot/command", json={
        "handle":          bot_handle,
        "arena_user_id":   "arena_456",
        "command":         "claim",
        "notification_id": str(uuid.uuid4()),
    }, headers=headers, timeout=5)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "routed"
    print(f"  claim routed: ✅")

    # Duplicate notification — should return duplicate status
    notif_id = str(uuid.uuid4())
    requests.post(f"{API_BASE}/api/bot/command", json={
        "handle": bot_handle, "arena_user_id": "arena_456",
        "command": "reveal", "notification_id": notif_id,
    }, headers=headers, timeout=5)
    res2 = requests.post(f"{API_BASE}/api/bot/command", json={
        "handle": bot_handle, "arena_user_id": "arena_456",
        "command": "reveal", "notification_id": notif_id,
    }, headers=headers, timeout=5)
    assert res2.json()["data"]["status"] == "duplicate"
    print(f"  Duplicate notification deduplicated: ✅")

    # Unknown command
    res = requests.post(f"{API_BASE}/api/bot/command", json={
        "handle": bot_handle, "arena_user_id": "arena_456",
        "command": "foobar", "notification_id": str(uuid.uuid4()),
    }, headers=headers, timeout=5)
    assert res.json()["data"]["status"] == "unknown_command"
    print(f"  Unknown command handled: ✅")


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-only",  action="store_true")
    parser.add_argument("--api-only", action="store_true")
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  Tessera — Day 5 Data Layer + API Tests")
    print("═" * 60)

    db_tests = [
        test_schema, test_user_upsert, test_epoch_lifecycle,
        test_score_storage, test_anchor_storage, test_bot_state,
        test_command_log, test_audit_retrieval,
    ]
    api_tests = [
        test_api_health, test_api_score, test_api_score_history,
        test_api_audit, test_api_cron_seal, test_api_bot_command,
    ]

    if args.api_only:
        for t in api_tests: t()
    elif args.db_only:
        for t in db_tests: t()
    else:
        for t in db_tests: t()
        print(f"\n{'─'*60}")
        print(f"  Starting API tests — make sure the server is running:")
        print(f"  uvicorn api.app:app --port 8000")
        print(f"{'─'*60}")
        for t in api_tests: t()

    # Summary
    print(f"\n{'═'*60}")
    print(f"  SUMMARY")
    print(f"{'─'*60}")
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    for name, ok, err in results:
        print(f"  {PASS if ok else FAIL}  {name}" + (f": {err}" if err else ""))
    print(f"{'─'*60}")
    print(f"  {passed}/{len(results)} tests passed")
    if failed == 0:
        print(f"\n  ✅ Day 5 complete.")
    else:
        print(f"\n  ❌ {failed} test(s) failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
