"""
Ingestion orchestrator for Tessera.

Given a handle and an epoch window, produces a validated post collection
ready for the scoring engine.

Usage:
    from ingestion.fetcher import fetch_posts_for_epoch
    result = fetch_posts_for_epoch("some_handle", epoch_start, epoch_end)
"""

import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

from ingestion.arena_client import ArenaClient

logger = logging.getLogger(__name__)

# Locked parameters — do not change without version bump
MIN_POST_THRESHOLD = 5
EPOCH_DAYS = 7


@dataclass
class EpochPostCollection:
    """
    The raw post collection for one epoch.
    This is what gets hashed and passed to the scoring engine.
    """
    handle: str
    user_id: str
    epoch_start: str       # ISO 8601
    epoch_end: str         # ISO 8601
    post_count: int
    posts: list
    fetched_at: str        # ISO 8601 — when this collection was built
    collection_hash: str   # SHA-256 of the post data


class InsufficientPostsError(Exception):
    """Raised when a user has fewer than MIN_POST_THRESHOLD posts in the epoch."""
    pass


class AutomatedAccountError(Exception):
    """Raised when a handle is detected as an automated agent account."""
    pass


def is_automated_account(handle: str, user_data: dict = None) -> bool:
    """
    Detect Arena AI agent accounts.
    Two signals:
    1. Handle ends with '_agent' (Arena naming convention for all registered agents)
    2. API user object contains agent flag (when available)
    """
    if handle.lower().endswith("_agent"):
        return True
    if user_data:
        # Arena API sets flag=4 on agent accounts based on observed data
        if user_data.get("flag") == 4:
            return True
    return False


# ─────────────────────────────────────────────────────────────
# Post pre-classification tracks
# Runs before the LLM classifier — routes posts to correct pipeline
# ─────────────────────────────────────────────────────────────
TRACK_CLASSIFY = "classify"   # send to LLM topic classifier
TRACK_GREETING = "greeting"   # gm/gn/ge posts — behaviorally meaningful, topically empty
TRACK_NULL     = "null"       # too short or empty for any analysis

import re as _re
_GREETING_PATTERN = _re.compile(r'^g[mne]\b', _re.IGNORECASE)


def pre_classify(post: dict) -> str:
    """
    Route a post to the correct processing track before topic classification.

    Tracks:
        TRACK_CLASSIFY — send to LLM topic classifier, counts in all pillars
        TRACK_GREETING — gm/gn/ge posts, excluded from entropy, counted in
                         consistency (regularity signal) and depth (if reply)
        TRACK_NULL     — excluded from all pillar calculations

    Greeting posts are behaviourally meaningful on Arena — daily GM posts with
    active reply engagement are a strong consistency signal. They are Null for
    topic classification but not discarded. This is documented v1.0 methodology.
    """
    content = post.get("content", "").strip()

    if not content:
        return TRACK_NULL

    # Greeting pattern: gm, gn, ge with optional short suffix
    if _GREETING_PATTERN.match(content) and len(content.split()) < 6:
        return TRACK_GREETING

    # Too short for meaningful classification
    if len(content.split()) < 2:
        return TRACK_NULL

    return TRACK_CLASSIFY


def current_epoch_window() -> tuple[datetime, datetime]:
    """Returns (start, end) for the most recent completed 7-day epoch."""
    now = datetime.now(timezone.utc)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=EPOCH_DAYS)
    return start, end


def fetch_posts_for_epoch(
    handle: str,
    client: ArenaClient,
    epoch_start: datetime = None,
    epoch_end: datetime = None,
    cache_dir: Path = None
) -> EpochPostCollection:
    """
    Full ingestion pipeline for one user/epoch.

    1. Resolve handle → userId (with cache)
    2. Fetch posts within epoch window
    3. Validate minimum post threshold
    4. Build and hash the collection
    5. Optionally cache to disk

    Raises InsufficientPostsError if post count < MIN_POST_THRESHOLD.
    """

    # Default to the most recent completed epoch
    if epoch_start is None or epoch_end is None:
        epoch_start, epoch_end = current_epoch_window()

    logger.info(f"Starting ingestion for @{handle} | "
                f"epoch {epoch_start.date()} → {epoch_end.date()}")

    # Step 1: Resolve handle → userId
    logger.info(f"Resolving handle @{handle}")
    user = client.get_user_by_handle(handle)
    user_id = user.get("id") or user.get("userId")
    if not user_id:
        logger.error(f"User object for @{handle} has no id field. Keys: {list(user.keys())}")
        raise KeyError(f"Cannot resolve user ID for @{handle} — API returned: {user}")
    logger.info(f"Resolved: {user.get('userName')} (id={user_id})")

    # Step 2: Bot detection gate
    if is_automated_account(handle, user):
        raise AutomatedAccountError(
            f"@{handle} appears to be an automated agent account. "
            f"Tessera analyzes human behavioral records only."
        )

    # Step 2: Fetch posts in window
    posts = client.fetch_epoch_posts(user_id, epoch_start, epoch_end)

    # Step 3: Validate minimum threshold
    if len(posts) < MIN_POST_THRESHOLD:
        raise InsufficientPostsError(
            f"@{handle} has {len(posts)} posts in this epoch window. "
            f"Minimum required: {MIN_POST_THRESHOLD}. "
            f"Cannot produce a reliable behavioral analysis."
        )

    # Step 4: Build collection and hash
    collection_data = {
        "handle": handle,
        "user_id": user_id,
        "epoch_start": epoch_start.isoformat(),
        "epoch_end": epoch_end.isoformat(),
        "posts": posts
    }

    collection_hash = hashlib.sha256(
        json.dumps(collection_data, sort_keys=True).encode()
    ).hexdigest()

    collection = EpochPostCollection(
        handle=handle,
        user_id=user_id,
        epoch_start=epoch_start.isoformat(),
        epoch_end=epoch_end.isoformat(),
        post_count=len(posts),
        posts=posts,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        collection_hash=collection_hash
    )

    logger.info(f"Collection built: {len(posts)} posts, hash={collection_hash[:12]}...")

    # Step 5: Cache to disk if requested
    if cache_dir:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{handle}_{epoch_start.date()}_{epoch_end.date()}.json"
        cache_path = cache_dir / filename
        with open(cache_path, "w") as f:
            json.dump(asdict(collection), f, indent=2)
        logger.info(f"Cached to {cache_path}")

    return collection


def load_cached_collection(path: Path) -> EpochPostCollection:
    """Load a previously cached collection from disk."""
    with open(path) as f:
        data = json.load(f)
    return EpochPostCollection(**data)


def post_stats(collection: EpochPostCollection) -> dict:
    """Quick summary stats for a collection — useful for debugging."""
    posts = collection.posts
    replies = [p for p in posts if p["is_reply"]]
    quotes = [p for p in posts if p["is_quote"]]
    originals = [p for p in posts if not p["is_reply"] and not p["is_quote"]]

    return {
        "total": len(posts),
        "originals": len(originals),
        "replies": len(replies),
        "quotes": len(quotes),
        "reply_ratio": round(len(replies) / len(posts), 3),
        "originality_ratio": round(len(originals) / len(posts), 3),
    }
