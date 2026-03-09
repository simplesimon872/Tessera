"""
database/client.py — Supabase database client for Tessera.

All DB operations live here. The rest of the codebase never
imports psycopg2 or supabase directly — always goes through this module.

Pre-Day 5: reads SUPABASE_URL and SUPABASE_KEY from .env.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── Connection ────────────────────────────────────────────────────────────────

_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env"
            )
        _client = create_client(url, key)
        logger.info(f"Supabase client connected: {url[:40]}…")
    return _client


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user(handle: str) -> Optional[dict]:
    """Return user row or None if not found."""
    res = get_client().table("users").select("*").eq("handle", handle).execute()
    return res.data[0] if res.data else None


def upsert_user(handle: str, arena_user_id: str) -> dict:
    """Create user if not exists. Return user row."""
    existing = get_user(handle)
    if existing:
        return existing
    res = get_client().table("users").insert({
        "handle":        handle,
        "arena_user_id": arena_user_id,
    }).execute()
    logger.info(f"User created: @{handle}")
    return res.data[0]


def update_user_last_epoch(handle: str, epoch_id: str):
    get_client().table("users").update(
        {"last_epoch_id": epoch_id}
    ).eq("handle", handle).execute()


# ── Epochs ────────────────────────────────────────────────────────────────────

def get_epoch(handle: str, epoch_start: str) -> Optional[dict]:
    """Return epoch row for handle + start date, or None."""
    res = (
        get_client().table("epochs")
        .select("*")
        .eq("handle", handle)
        .eq("epoch_start", epoch_start)
        .execute()
    )
    return res.data[0] if res.data else None


def get_latest_epoch(handle: str) -> Optional[dict]:
    """Return the most recent epoch for a handle."""
    res = (
        get_client().table("epochs")
        .select("*")
        .eq("handle", handle)
        .order("epoch_start", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_epochs_by_status(status: str) -> list[dict]:
    """Return all epochs with a given status. Used by cron."""
    res = (
        get_client().table("epochs")
        .select("*")
        .eq("status", status)
        .order("created_at")
        .execute()
    )
    return res.data or []


def create_epoch(handle: str, epoch_start: str, epoch_end: str) -> dict:
    """Create a new epoch with status=computed. Return epoch row."""
    res = get_client().table("epochs").insert({
        "handle":      handle,
        "epoch_start": epoch_start,
        "epoch_end":   epoch_end,
        "status":      "computed",
    }).execute()
    logger.info(f"Epoch created: @{handle} | {epoch_start[:10]} → {epoch_end[:10]}")
    return res.data[0]


def update_epoch_status(epoch_id: str, status: str):
    """Update epoch status. Valid: computed, sealed, seal_failed."""
    get_client().table("epochs").update(
        {"status": status}
    ).eq("id", epoch_id).execute()
    logger.info(f"Epoch {epoch_id[:8]}… → status={status}")


def get_epoch_history(handle: str, limit: int = 10) -> list[dict]:
    """Return epoch history for a handle, newest first."""
    res = (
        get_client().table("epochs")
        .select("*, scores(*), anchors(*)")
        .eq("handle", handle)
        .order("epoch_start", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


# ── Scores ────────────────────────────────────────────────────────────────────

def store_scores(epoch_id: str, snapshot: dict) -> dict:
    """
    Store pillar scores and full snapshot JSON for an epoch.
    snapshot is the dict produced by scoring/engine.py.
    """
    scores = snapshot.get("scores", {})
    breakdown = snapshot.get("post_breakdown", {})
    methodology = snapshot.get("methodology", {})

    res = get_client().table("scores").insert({
        "epoch_id":          epoch_id,
        "originality":       scores.get("originality"),
        "focus":             scores.get("focus"),
        "consistency":       scores.get("consistency"),
        "depth":             scores.get("depth"),
        "composite":         scores.get("composite"),
        "methodology":       methodology.get("version", "v1.0"),
        "snapshot_hash":     snapshot.get("snapshot_hash"),
        "collection_hash":   methodology.get("collection_hash"),
        "prompt_hash":       methodology.get("prompt_hash"),
        "model":             methodology.get("model"),
        "consistency_mode":  scores.get("consistency_mode"),
        "other_cap_applied": scores.get("other_cap_applied", False),
        "post_total":        breakdown.get("total"),
        "post_classified":   breakdown.get("classified"),
        "post_greeting":     breakdown.get("greeting"),
        "post_null":         breakdown.get("null_track"),
        "snapshot_json":     snapshot,
    }).execute()
    logger.info(f"Scores stored: epoch {epoch_id[:8]}… | composite={scores.get('composite')}")
    return res.data[0]


def get_scores(epoch_id: str) -> Optional[dict]:
    """Return scores row for an epoch."""
    res = (
        get_client().table("scores")
        .select("*")
        .eq("epoch_id", epoch_id)
        .execute()
    )
    return res.data[0] if res.data else None


# ── Anchors ───────────────────────────────────────────────────────────────────

def store_anchor(epoch_id: str, receipt) -> dict:
    """
    Store an onchain seal receipt. receipt is an AnchorReceipt dataclass.
    """
    res = get_client().table("anchors").insert({
        "epoch_id":      epoch_id,
        "tx_hash":       receipt.tx_hash,
        "block_number":  receipt.block_number,
        "snapshot_hash": receipt.snapshot_hash,
        "anchored_at":   receipt.anchored_at,
        "snowtrace_url": receipt.snowtrace_url,
    }).execute()
    logger.info(f"Anchor stored: epoch {epoch_id[:8]}… | tx={receipt.tx_hash[:18]}…")
    return res.data[0]


def get_anchor(epoch_id: str) -> Optional[dict]:
    """Return anchor row for an epoch, or None if not yet sealed."""
    res = (
        get_client().table("anchors")
        .select("*")
        .eq("epoch_id", epoch_id)
        .execute()
    )
    return res.data[0] if res.data else None


# ── Bot state ─────────────────────────────────────────────────────────────────

def get_bot_state(key: str) -> Optional[str]:
    """Return a bot state value by key, or None."""
    res = (
        get_client().table("bot_state")
        .select("value")
        .eq("key", key)
        .execute()
    )
    return res.data[0]["value"] if res.data else None


def set_bot_state(key: str, value: str):
    """Upsert a bot state value."""
    get_client().table("bot_state").upsert(
        {"key": key, "value": value},
        on_conflict="key"
    ).execute()


# ── Command log ───────────────────────────────────────────────────────────────

def log_command(handle: str, command: str, target: Optional[str] = None):
    """Log a bot command for rate limiting."""
    get_client().table("command_log").insert({
        "handle":  handle,
        "command": command,
        "target":  target,
    }).execute()


def count_recent_commands(handle: str, window_minutes: int = 60) -> int:
    """Count commands from a handle in the last window_minutes."""
    from datetime import timedelta
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    ).isoformat()
    res = (
        get_client().table("command_log")
        .select("id", count="exact")
        .eq("handle", handle)
        .gte("issued_at", cutoff)
        .execute()
    )
    return res.count or 0


# ── Audit ─────────────────────────────────────────────────────────────────────

def get_full_audit(epoch_id: str) -> Optional[dict]:
    """
    Return everything needed for the audit page:
    epoch + scores + anchor in one call.
    """
    res = (
        get_client().table("epochs")
        .select("*, scores(*), anchors(*)")
        .eq("id", epoch_id)
        .execute()
    )
    return res.data[0] if res.data else None
