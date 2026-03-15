"""
bot/handlers.py — Command handlers for claim, reveal, inspect.

Each handler:
    1. Reads from DB / runs scoring if needed
    2. Formats a reply via poster.py
    3. Posts to Arena via client
    4. Returns True on success

Epoch cache: if a computed/sealed epoch already exists for the current
window, return it immediately — never recompute, never re-run the LLM.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from bot.parser import ParsedCommand
from bot.poster import (
    send_reply,
    format_claim_success,
    format_claim_already_claimed,
    format_reveal,
    format_reveal_insufficient,
    format_inspect_sealed,
    format_inspect_unsealed,
    format_inspect_insufficient,
    format_unknown_command,
    format_inspect_missing_target,
    format_error,
)
from database.client import (
    get_user, upsert_user, update_user_last_epoch,
    get_epoch, get_latest_epoch, create_epoch,
    get_scores, store_scores,
    get_anchor,
)

logger = logging.getLogger(__name__)


# ── Epoch window helper ───────────────────────────────────────────────────────

def _current_epoch_window() -> tuple[str, str]:
    """Return (epoch_start, epoch_end) for the current 30-day window."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:00+00:00")
    end   = now.strftime("%Y-%m-%dT%H:%M:00+00:00")
    return start, end


# ── Scoring pipeline ──────────────────────────────────────────────────────────

def _run_scoring_sync(handle: str) -> Optional[dict]:
    """
    Run the full scoring pipeline synchronously.
    Returns snapshot dict or None on failure.
    """
    try:
        from bot.bannerus_client import BannerusClient
        from ingestion.fetcher import fetch_posts_for_epoch
        from evaluation.classifier import Classifier

        epoch_start_str, epoch_end_str = _current_epoch_window()
        epoch_start = datetime.fromisoformat(epoch_start_str)
        epoch_end   = datetime.fromisoformat(epoch_end_str)

        client     = BannerusClient(bearer_token=os.getenv("BANNERUS_API_KEY", ""))
        classifier = Classifier(api_key=os.getenv("ANTHROPIC_API_KEY", ""), log_raw=False)

        from scoring.engine import score_epoch
        collection = fetch_posts_for_epoch(
            handle=handle,
            client=client,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
        )
        return score_epoch(collection, classifier)

    except Exception as e:
        logger.error(f"Scoring failed for @{handle}: {e}", exc_info=True)
        return None


def _get_or_score(handle: str, register: bool = True, force: bool = False) -> tuple[Optional[dict], Optional[str], bool]:
    """
    Return (snapshot, epoch_id, cached).
    Checks DB first — runs scoring only if no current epoch exists.
    Stores to DB if freshly scored.

    register=True  → full claim path: upsert_user + update_user_last_epoch
                     used by handle_claim and handle_reveal
    register=False → score-only path: saves epoch + scores but does NOT
                     register the user as claimed. Used by handle_inspect
                     so inspected accounts appear on the leaderboard as
                     unsealed without being treated as having claimed.
    """
    epoch_start, epoch_end = _current_epoch_window()

    # Check cache first (unless force=True)
    if force:
        logger.info(f"Force rescore for @{handle} — skipping cache")
    existing_epoch = None if force else get_epoch(handle, epoch_start)
    if existing_epoch:
        scores_row = get_scores(existing_epoch["id"])
        if scores_row and scores_row.get("snapshot_json"):
            logger.info(f"Returning cached epoch for @{handle}")
            return scores_row["snapshot_json"], existing_epoch["id"], True

    # Run scoring
    logger.info(f"Running fresh scoring for @{handle}")
    snapshot = _run_scoring_sync(handle)
    if snapshot is None:
        return None, None, False

    # Store epoch + scores regardless of register flag
    epoch = create_epoch(handle, epoch_start, epoch_end)
    store_scores(epoch["id"], snapshot)

    # Only register as claimed user if explicitly requested
    if register:
        arena_user_id = snapshot.get("user_id") or snapshot.get("arena_user_id", "unknown")
        upsert_user(handle, arena_user_id)
        update_user_last_epoch(handle, epoch["id"])
    else:
        logger.info(f"Scored @{handle} via inspect — saved to DB, not registered as claimed")

    return snapshot, epoch["id"], False


# ── Handlers ──────────────────────────────────────────────────────────────────

def handle_claim(cmd: ParsedCommand, client) -> bool:
    """
    claim — activate Tessera for the issuing user.

    If already claimed: return current status.
    If new: register in DB, confirm activation.
    """
    handle = cmd.issuer_handle
    logger.info(f"handle_claim: @{handle}")

    try:
        existing_user = get_user(handle)

        if existing_user:
            # Already claimed — return latest epoch info
            latest_epoch = get_latest_epoch(handle)
            scores = get_scores(latest_epoch["id"]) if latest_epoch else None
            snapshot = scores["snapshot_json"] if scores else None
            reply = format_claim_already_claimed(handle, latest_epoch or {}, snapshot)
        else:
            # New claim — register user
            upsert_user(handle, cmd.issuer_arena_id)
            reply = format_claim_success(handle)

        send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        return True

    except Exception as e:
        logger.error(f"handle_claim failed for @{handle}: {e}", exc_info=True)
        try:
            send_reply(client, format_error(handle), thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        except Exception:
            pass
        return False


def handle_reveal(cmd: ParsedCommand, client) -> bool:
    """
    reveal — show the issuing user their current epoch scores.

    Runs scoring if no current epoch exists.
    Shows unsealed scores with seal countdown if not yet sealed.
    """
    handle = cmd.issuer_handle
    logger.info(f"handle_reveal: @{handle}")

    try:
        send_reply(client, f"@{handle} — scoring in progress, give me a moment ⏳", thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        snapshot, epoch_id, cached = _get_or_score(handle, force=True)

        if snapshot is None:
            # Scoring failed — likely insufficient posts
            reply = format_reveal_insufficient(handle, 0, 0)
            send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
            return True

        # Check for insufficient posts error in snapshot
        breakdown = snapshot.get("post_breakdown", {})
        total  = breakdown.get("total", 0)
        active = breakdown.get("active", 0)
        if total < 5 or active < 1:
            reply = format_reveal_insufficient(handle, total, active)
            send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
            return True

        # Get epoch and anchor status
        epoch_start, epoch_end = _current_epoch_window()
        epoch = get_epoch(handle, epoch_start) or {}
        sealed = epoch.get("status") == "sealed"

        # Inject epoch window dates into snapshot so format_reveal can use them
        snapshot.setdefault("epoch", {})
        if not snapshot["epoch"].get("start"):
            snapshot["epoch"]["start"] = epoch_start
        if not snapshot["epoch"].get("end"):
            snapshot["epoch"]["end"] = epoch_end

        reply = format_reveal(handle, snapshot, epoch, sealed)
        send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        return True

    except Exception as e:
        logger.error(f"handle_reveal failed for @{handle}: {e}", exc_info=True)
        try:
            send_reply(client, format_error(handle), thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        except Exception:
            pass
        return False


def handle_inspect(cmd: ParsedCommand, client) -> bool:
    """
    inspect @target — show any user's latest epoch.

    If target has a sealed record: show it with TX hash.
    If target has no sealed record: show unsealed preview.
    If target has insufficient posts: say so clearly.
    """
    issuer = cmd.issuer_handle
    target = cmd.target_handle

    if not target:
        send_reply(client, format_inspect_missing_target(issuer), thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        return True

    logger.info(f"handle_inspect: @{issuer} → @{target}")

    try:
        # Check if target has a sealed epoch first
        latest_epoch = get_latest_epoch(target)

        if latest_epoch and latest_epoch.get("status") == "sealed":
            scores_row = get_scores(latest_epoch["id"])
            anchor     = get_anchor(latest_epoch["id"])
            if scores_row and scores_row.get("snapshot_json"):
                reply = format_inspect_sealed(
                    issuer, target,
                    scores_row["snapshot_json"],
                    anchor or {},
                )
                send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
                return True

        # No sealed record — run scoring for a live preview and save to DB
        # register=False: saves the score (so it appears on leaderboard) but
        # does NOT register the account as claimed.
        snapshot, epoch_id, cached = _get_or_score(target, register=False)

        if snapshot is None:
            reply = format_inspect_insufficient(issuer, target, 0, 0)
            send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
            return True

        breakdown = snapshot.get("post_breakdown", {})
        total  = breakdown.get("total", 0)
        active = breakdown.get("active", 0)
        if total < 5 or active < 1:
            reply = format_inspect_insufficient(issuer, target, total, active)
            send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
            return True

        reply = format_inspect_unsealed(issuer, target, snapshot)
        send_reply(client, reply, thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        return True

    except Exception as e:
        logger.error(f"handle_inspect failed: @{issuer} → @{target}: {e}", exc_info=True)
        try:
            send_reply(client, format_error(issuer), thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        except Exception:
            pass
        return False


def handle_unknown_command(cmd: ParsedCommand, client) -> bool:
    """Reply with available commands list."""
    try:
        send_reply(client, format_unknown_command(cmd.issuer_handle, cmd.raw_content), thread_id=cmd.thread_id, user_id=cmd.issuer_arena_id)
        return True
    except Exception as e:
        logger.error(f"handle_unknown_command failed: {e}")
        return False
