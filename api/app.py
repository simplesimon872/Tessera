"""
api/app.py — Tessera internal API.

Endpoints:
    POST /api/score              — score a handle, store epoch + scores
    GET  /api/score/{handle}     — retrieve epoch history
    GET  /api/audit/{epoch_id}   — full audit trail
    POST /api/cron/seal          — trigger weekly seal batch (scheduler only)
    POST /api/bot/command        — receive and route bot commands (Day 6)

Run locally:
    uvicorn api.app:app --reload --port 8000

All responses follow a consistent envelope:
    { "ok": true,  "data": {...} }
    { "ok": false, "error": "..." }
"""

import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.client import (
    get_user, upsert_user, update_user_last_epoch,
    get_epoch, get_latest_epoch, create_epoch,
    update_epoch_status, get_epoch_history,
    get_epochs_by_status,
    store_scores, get_scores,
    store_anchor, get_anchor,
    get_full_audit,
    log_command, count_recent_commands,
    get_bot_state, set_bot_state,
)
from attestation.sealer import try_anchor_epoch

logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tessera Internal API",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tessera.xyz", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────
# Simple shared secret for internal endpoints.
# The bot and cron use this header. tessera.xyz uses GET-only public endpoints.

INTERNAL_SECRET = os.getenv("INTERNAL_API_SECRET", "")

def _require_internal(x_internal_secret: Optional[str] = Header(None)):
    if not INTERNAL_SECRET:
        return  # dev mode — no secret set, allow all
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Response helpers ──────────────────────────────────────────────────────────

def ok(data: dict) -> dict:
    return {"ok": True, "data": data}

def err(message: str, status: int = 400):
    raise HTTPException(status_code=status, detail={"ok": False, "error": message})


# ── Request models ────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    handle: str
    arena_user_id: str
    force_rescore: bool = False   # if True, re-score even if recent epoch exists

class BotCommandRequest(BaseModel):
    handle: str
    arena_user_id: str
    command: str                  # 'claim' | 'reveal' | 'inspect'
    target_handle: Optional[str] = None   # for inspect only
    notification_id: str          # Arena notification ID — idempotency key


# ── POST /api/score ───────────────────────────────────────────────────────────

@app.post("/api/score")
async def score_handle(req: ScoreRequest):
    """
    Score a handle for the current epoch window.
    Stores epoch + scores rows in DB.
    Returns the scored snapshot.

    Idempotent: if a computed/sealed epoch already exists for this window,
    returns the cached result unless force_rescore=True.
    """
    _require_internal()

    handle = req.handle.lower().strip()
    now = datetime.now(timezone.utc)
    epoch_start = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:00+00:00")
    epoch_end   = now.strftime("%Y-%m-%dT%H:%M:00+00:00")

    # Return cached if exists and not forcing rescore
    if not req.force_rescore:
        existing_epoch = get_epoch(handle, epoch_start)
        if existing_epoch:
            scores = get_scores(existing_epoch["id"])
            if scores and scores.get("snapshot_json"):
                logger.info(f"Returning cached scores: @{handle}")
                return ok({
                    "handle":   handle,
                    "cached":   True,
                    "epoch_id": existing_epoch["id"],
                    "status":   existing_epoch["status"],
                    "snapshot": scores["snapshot_json"],
                })

    # Run scoring pipeline
    try:
        snapshot = await _run_scoring(handle, epoch_start, epoch_end)
    except ValueError as e:
        err(str(e), status=422)
    except Exception as e:
        logger.error(f"Scoring failed: @{handle} | {e}", exc_info=True)
        err(f"Scoring failed: {e}", status=500)

    # Upsert user
    upsert_user(handle, req.arena_user_id)

    # Store epoch
    epoch = create_epoch(handle, epoch_start, epoch_end)
    epoch_id = epoch["id"]

    # Store scores
    store_scores(epoch_id, snapshot)

    # Update user's last epoch
    update_user_last_epoch(handle, epoch_id)

    logger.info(f"Scored and stored: @{handle} | composite={snapshot['scores']['composite']}")

    return ok({
        "handle":   handle,
        "cached":   False,
        "epoch_id": epoch_id,
        "status":   "computed",
        "snapshot": snapshot,
    })


# ── GET /api/score/{handle} ───────────────────────────────────────────────────

@app.get("/api/score/{handle}")
async def get_score_history(handle: str, limit: int = 10):
    """
    Return epoch history for a handle.
    Public endpoint — no auth required.
    Used by tessera.xyz profile page.
    """
    handle = handle.lower().strip()
    user = get_user(handle)
    history = get_epoch_history(handle, limit=limit)

    return ok({
        "handle":  handle,
        "claimed": user is not None,
        "claimed_at": user["claimed_at"] if user else None,
        "epochs":  history,
    })


# ── GET /api/audit/{epoch_id} ─────────────────────────────────────────────────

@app.get("/api/audit/{epoch_id}")
async def get_audit(epoch_id: str):
    """
    Full audit trail for an epoch.
    Public endpoint — used by tessera.xyz audit page.

    Returns: epoch metadata + pillar scores + snapshot hash
             + anchor (tx_hash, block, snowtrace_url) if sealed
             + full snapshot_json for hash reproduction
    """
    audit = get_full_audit(epoch_id)
    if not audit:
        err(f"Epoch not found: {epoch_id}", status=404)

    # Build clean audit response
    scores_row = audit.get("scores", [{}])
    scores_row = scores_row[0] if isinstance(scores_row, list) and scores_row else scores_row
    anchors_row = audit.get("anchors", [{}])
    anchors_row = anchors_row[0] if isinstance(anchors_row, list) and anchors_row else anchors_row

    return ok({
        "epoch": {
            "id":          audit["id"],
            "handle":      audit["handle"],
            "epoch_start": audit["epoch_start"],
            "epoch_end":   audit["epoch_end"],
            "status":      audit["status"],
        },
        "scores": {
            "originality":       scores_row.get("originality"),
            "focus":             scores_row.get("focus"),
            "consistency":       scores_row.get("consistency"),
            "depth":             scores_row.get("depth"),
            "composite":         scores_row.get("composite"),
            "consistency_mode":  scores_row.get("consistency_mode"),
            "other_cap_applied": scores_row.get("other_cap_applied"),
        },
        "methodology": {
            "version":        scores_row.get("methodology"),
            "prompt_hash":    scores_row.get("prompt_hash"),
            "model":          scores_row.get("model"),
            "weights":        "25% each — originality, focus, consistency, depth",
        },
        "post_breakdown": {
            "total":      scores_row.get("post_total"),
            "classified": scores_row.get("post_classified"),
            "greeting":   scores_row.get("post_greeting"),
            "null":       scores_row.get("post_null"),
        },
        "snapshot_hash": scores_row.get("snapshot_hash"),
        "snapshot_json": scores_row.get("snapshot_json"),  # for hash reproduction
        "anchor": {
            "tx_hash":       anchors_row.get("tx_hash"),
            "block_number":  anchors_row.get("block_number"),
            "anchored_at":   anchors_row.get("anchored_at"),
            "snowtrace_url": anchors_row.get("snowtrace_url"),
        } if anchors_row else None,
        "disclaimer": (
            "Tessera does not evaluate truthfulness, moral alignment, or content quality. "
            "It evaluates structural behavioral properties only."
        ),
    })


# ── POST /api/cron/seal ───────────────────────────────────────────────────────

@app.post("/api/cron/seal")
async def trigger_seal(x_internal_secret: Optional[str] = Header(None)):
    """
    Trigger the weekly seal batch.
    Called by the scheduler (Railway cron / external cron service).
    Never called by users.

    Idempotent: already-sealed epochs are skipped.
    """
    _require_internal(x_internal_secret)

    computed_epochs = _get_computed_epochs_from_db()
    if not computed_epochs:
        logger.info("Cron seal: nothing to seal.")
        return ok({"sealed": 0, "failed": 0, "message": "Nothing to seal."})

    sealed = 0
    failed = 0
    failures = []

    for epoch in computed_epochs:
        epoch_id = epoch["id"]
        handle   = epoch["handle"]

        # Idempotency: skip if already has anchor
        existing_anchor = get_anchor(epoch_id)
        if existing_anchor:
            logger.info(f"Already sealed, skipping: @{handle} epoch {epoch_id[:8]}…")
            continue

        # Get snapshot from scores table
        scores_row = get_scores(epoch_id)
        if not scores_row or not scores_row.get("snapshot_json"):
            logger.error(f"No snapshot found for epoch {epoch_id[:8]}…, skipping")
            failed += 1
            continue

        snapshot = scores_row["snapshot_json"]
        result = try_anchor_epoch(snapshot)

        if result.success:
            store_anchor(epoch_id, result.receipt)
            update_epoch_status(epoch_id, "sealed")
            sealed += 1
            logger.info(f"Sealed: @{handle} | tx={result.receipt.tx_hash[:18]}…")
        else:
            update_epoch_status(epoch_id, "seal_failed")
            failed += 1
            failures.append({"handle": handle, "error": result.error})
            logger.error(f"Seal failed: @{handle} | {result.error}")

    # Update last seal run
    set_bot_state(
        "last_seal_run",
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    )

    return ok({
        "sealed":   sealed,
        "failed":   failed,
        "failures": failures,
    })


def _get_computed_epochs_from_db() -> list[dict]:
    """Get all epochs with status=computed OR seal_failed (retry)."""
    computed = get_epochs_by_status("computed")
    failed   = get_epochs_by_status("seal_failed")
    return computed + failed


# ── POST /api/bot/command ─────────────────────────────────────────────────────

@app.post("/api/bot/command")
async def bot_command(req: BotCommandRequest):
    """
    Receive and route bot commands from the Arena polling loop.

    Idempotent: notification_id used as dedup key.
    Rate limited: max 5 commands per user per hour.

    Day 6 will flesh out the full command handlers.
    This stub validates, rate-limits, logs, and returns a routing decision.
    """
    _require_internal()

    handle  = req.handle.lower().strip()
    command = req.command.lower().strip()

    # Idempotency check — has this notification already been processed?
    processed_key = f"processed_notification:{req.notification_id}"
    if get_bot_state(processed_key):
        logger.info(f"Duplicate notification {req.notification_id[:8]}…, skipping")
        return ok({"status": "duplicate", "message": "Already processed."})

    # Rate limit check
    recent = count_recent_commands(handle, window_minutes=60)
    if recent >= 5:
        logger.warning(f"Rate limit hit: @{handle} ({recent} commands in last hour)")
        log_command(handle, command, req.target_handle)
        return ok({
            "status":  "rate_limited",
            "message": f"@{handle} — you've sent {recent} commands in the last hour. Limit is 5. Try again later.",
        })

    # Log command
    log_command(handle, command, req.target_handle)

    # Mark notification processed
    set_bot_state(processed_key, "1")

    # Route — full handlers wired in Day 6
    if command == "claim":
        return ok({"status": "routed", "command": "claim", "handle": handle})
    elif command == "reveal":
        return ok({"status": "routed", "command": "reveal", "handle": handle})
    elif command == "inspect":
        if not req.target_handle:
            return ok({"status": "error", "message": "inspect requires a target @handle"})
        return ok({"status": "routed", "command": "inspect", "handle": handle, "target": req.target_handle})
    else:
        return ok({
            "status":  "unknown_command",
            "message": (
                f"@{handle} — unknown command '{command}'. "
                f"Available: claim · reveal · inspect @handle"
            ),
        })


# ── Scoring pipeline (internal) ───────────────────────────────────────────────

async def _run_scoring(handle: str, epoch_start: str, epoch_end: str) -> dict:
    """
    Wire ingestion → scoring engine together.
    Returns canonical snapshot dict.

    Day 6+: This will also check the cache before hitting the Arena API.
    """
    from datetime import datetime
    from ingestion.arena_client import ArenaClient
    from ingestion.fetcher import fetch_posts_for_epoch
    from evaluation.classifier import Classifier
    from scoring.engine import score_epoch

    client = ArenaClient(api_key=os.getenv("ARENA_API_KEY", ""))
    classifier = Classifier(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    epoch_start_dt = datetime.fromisoformat(epoch_start)
    epoch_end_dt = datetime.fromisoformat(epoch_end)

    collection = fetch_posts_for_epoch(
        handle=handle,
        client=client,
        epoch_start=epoch_start_dt,
        epoch_end=epoch_end_dt,
    )
    snapshot = score_epoch(collection, classifier.classify)
    return snapshot


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"ok": True, "service": "tessera-api", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
