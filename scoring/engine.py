"""
Tessera scoring engine — Day 3.

score_epoch(collection, classifier) → EpochSnapshot

Four pillars:
    Originality   — API-derived, no LLM
    Focus         — LLM topic classification + Shannon entropy
    Consistency   — API-derived, two modes based on post count
    Depth         — API-derived, engagement behaviour

Composite = equal-weight average of all four (25% each).

All scores are 0–100, rounded to 2 decimal places.
Snapshot hash is deterministic: canonical JSON → SHA-256.
"""

import json
import math
import hashlib
import logging
import statistics
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

from scoring.constants import (
    ENTROPY_BUCKETS,
    MAX_ENTROPY,
    OTHER_DOMINANCE_THRESHOLD,
    FOCUS_OTHER_CAP,
    MIN_POST_THRESHOLD,
    CONSISTENCY_FULL_MODE_THRESHOLD,
    METHODOLOGY_VERSION,
    COMPOSITE_WEIGHTS,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PostBreakdown:
    total: int
    classified: int      # sent to LLM, counts in all pillars
    greeting: int        # gm/gn/ge — consistency + depth only, not entropy
    null_track: int      # excluded from all pillars
    active: int          # classified + greeting — total "live" posts


@dataclass
class OriginalityResult:
    score: float         # 0–100
    original_count: int
    reply_count: int
    quote_count: int
    active_posts: int


@dataclass
class FocusResult:
    score: float               # 0–100
    entropy: float             # raw Shannon entropy
    max_entropy: float         # log2(6) — hardcoded
    topic_distribution: dict   # {category: count}
    other_dominance: float     # fraction of posts classified Other
    other_cap_applied: bool    # True if focus was capped due to Other dominance


@dataclass
class ConsistencyResult:
    score: float
    mode: str                  # "thirds_entropy" | "frequency_variance"
    active_posts: int
    # thirds_entropy mode
    window_entropies: Optional[list] = None   # [H1, H2, H3]
    entropy_std: Optional[float] = None
    # frequency_variance mode
    window_post_counts: Optional[list] = None  # [c1, c2, c3]
    frequency_cv: Optional[float] = None        # coefficient of variation


@dataclass
class DepthResult:
    score: float
    reply_ratio: float
    quote_ratio: float
    participation_rate: float   # (replies + quotes) / active
    active_posts: int


@dataclass
class EpochSnapshot:
    # Identity
    handle: str
    user_id: str
    epoch_start: str    # ISO 8601, no milliseconds
    epoch_end: str      # ISO 8601, no milliseconds
    scored_at: str      # ISO 8601, no milliseconds

    # Post breakdown
    post_breakdown: PostBreakdown

    # Pillar results
    originality: OriginalityResult
    focus: FocusResult
    consistency: ConsistencyResult
    depth: DepthResult

    # Scores (rounded to 2dp — these are what get hashed)
    scores: dict        # {consistency, focus, depth, originality, composite}

    # Provenance
    prompt_hash: str
    prompt_version: str
    model: str
    methodology_version: str
    collection_hash: str

    # Canonical hash — computed last, after all fields are set
    snapshot_hash: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Track routing (mirrors fetcher.py — scoring engine owns its own copy)
# ─────────────────────────────────────────────────────────────────────────────

import re as _re
_GREETING_RE = _re.compile(r'^g[mne]\b', _re.IGNORECASE)
TRACK_CLASSIFY = "classify"
TRACK_GREETING = "greeting"
TRACK_NULL = "null"


def _pre_classify(post: dict) -> str:
    """Route post to processing track before LLM classification."""
    content = post.get("content", "").strip()
    if not content:
        return TRACK_NULL
    if _GREETING_RE.match(content) and len(content.split()) < 6:
        return TRACK_GREETING
    if len(content.split()) < 2:
        return TRACK_NULL
    return TRACK_CLASSIFY


# ─────────────────────────────────────────────────────────────────────────────
# Pillar 1 — Originality
# API-derived. No LLM.
# ─────────────────────────────────────────────────────────────────────────────

def _score_originality(posts: list, active_posts: int) -> OriginalityResult:
    """
    Originality = original posts / active posts, scaled 0–100.
    Original = not a reply AND not a quote.
    Active = classified + greeting tracks (null excluded).
    """
    originals = [p for p in posts if not p.get("is_reply") and not p.get("is_quote")]
    replies   = [p for p in posts if p.get("is_reply")]
    quotes    = [p for p in posts if p.get("is_quote")]

    if active_posts == 0:
        score = 0.0
    else:
        score = round((len(originals) / active_posts) * 100, 2)

    return OriginalityResult(
        score=score,
        original_count=len(originals),
        reply_count=len(replies),
        quote_count=len(quotes),
        active_posts=active_posts,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pillar 2 — Focus (Domain Entropy)
# LLM classifications → Shannon entropy → normalized focus score.
# ─────────────────────────────────────────────────────────────────────────────

def _shannon_entropy(distribution: dict) -> float:
    """
    Shannon entropy of a category distribution.
    Only counts ENTROPY_BUCKETS. Null excluded.
    Returns 0.0 if no posts.
    """
    total = sum(distribution.get(cat, 0) for cat in ENTROPY_BUCKETS)
    if total == 0:
        return 0.0

    H = 0.0
    for cat in ENTROPY_BUCKETS:
        count = distribution.get(cat, 0)
        if count > 0:
            p = count / total
            H -= p * math.log2(p)
    return H


def _score_focus(classified_posts: list, classifications: dict) -> FocusResult:
    """
    Focus = 100 × (1 − entropy / max_entropy).
    High focus = low entropy = concentrated topic distribution.

    Other dominance guard: if Other > 50% of classified posts,
    cap focus at 60. Meme/lifestyle accounts collapse entropy
    artificially — document this cap in the audit trail.
    """
    # Build topic distribution
    topic_dist = {cat: 0 for cat in ENTROPY_BUCKETS}
    topic_dist["Null"] = 0

    for post_id, category in classifications.items():
        if category in topic_dist:
            topic_dist[category] += 1

    # Entropy over active buckets only
    entropy = _shannon_entropy(topic_dist)

    # Other dominance check
    classified_count = sum(topic_dist.get(c, 0) for c in ENTROPY_BUCKETS + ["Null"])
    other_count = topic_dist.get("Other", 0)
    other_dominance = (other_count / classified_count) if classified_count > 0 else 0.0

    # Raw focus score
    raw_focus = 100.0 * (1.0 - (entropy / MAX_ENTROPY)) if MAX_ENTROPY > 0 else 0.0
    raw_focus = max(0.0, min(100.0, raw_focus))

    # Apply Other dominance cap
    other_cap_applied = False
    if other_dominance > OTHER_DOMINANCE_THRESHOLD:
        raw_focus = min(raw_focus, FOCUS_OTHER_CAP)
        other_cap_applied = True
        logger.warning(
            f"Other dominance cap applied: {other_dominance:.1%} of posts → Other. "
            f"Focus capped at {FOCUS_OTHER_CAP}."
        )

    return FocusResult(
        score=round(raw_focus, 2),
        entropy=round(entropy, 4),
        max_entropy=round(MAX_ENTROPY, 4),
        topic_distribution=topic_dist,
        other_dominance=round(other_dominance, 4),
        other_cap_applied=other_cap_applied,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pillar 3 — Consistency
# API-derived. Two modes based on post count.
# ─────────────────────────────────────────────────────────────────────────────

def _split_into_thirds_by_time(posts: list, epoch_start: datetime, epoch_end: datetime) -> tuple:
    """Split posts into three equal time windows. Returns (third1, third2, third3)."""
    total_seconds = (epoch_end - epoch_start).total_seconds()
    third = total_seconds / 3
    t1_end = epoch_start.timestamp() + third
    t2_end = epoch_start.timestamp() + 2 * third

    t1, t2, t3 = [], [], []
    for post in posts:
        ts = post.get("_ts")
        if ts is None:
            continue
        if ts <= t1_end:
            t1.append(post)
        elif ts <= t2_end:
            t2.append(post)
        else:
            t3.append(post)
    return t1, t2, t3


def _score_consistency(
    active_posts: list,
    classifications: dict,
    epoch_start: datetime,
    epoch_end: datetime,
) -> ConsistencyResult:
    """
    Two modes:
    ≥ 60 active posts: thirds-based topic entropy (std of entropy across windows)
    20–59 active posts: frequency variance (cv of post counts across windows)

    Low variance / low entropy drift = consistent = high score.
    """
    n = len(active_posts)
    t1, t2, t3 = _split_into_thirds_by_time(active_posts, epoch_start, epoch_end)

    if n >= CONSISTENCY_FULL_MODE_THRESHOLD:
        # ── Thirds entropy mode ──
        # Compute topic distribution for each third of classified posts only
        def _dist_for_posts(posts_subset):
            dist = {cat: 0 for cat in ENTROPY_BUCKETS + ["Null"]}
            for p in posts_subset:
                cat = classifications.get(p.get("id") or p.get("postId"))
                if cat and cat in dist:
                    dist[cat] += 1
            return dist

        H1 = _shannon_entropy(_dist_for_posts(t1))
        H2 = _shannon_entropy(_dist_for_posts(t2))
        H3 = _shannon_entropy(_dist_for_posts(t3))

        try:
            entropy_std = statistics.stdev([H1, H2, H3])
        except statistics.StatisticsError:
            entropy_std = 0.0

        stability = 1.0 - (entropy_std / MAX_ENTROPY)
        stability = max(0.0, min(1.0, stability))
        score = round(stability * 100, 2)

        return ConsistencyResult(
            score=score,
            mode="thirds_entropy",
            active_posts=n,
            window_entropies=[round(H1, 4), round(H2, 4), round(H3, 4)],
            entropy_std=round(entropy_std, 4),
        )

    else:
        # ── Frequency variance mode ──
        counts = [len(t1), len(t2), len(t3)]
        mean_count = statistics.mean(counts)

        if mean_count == 0:
            score = 0.0
            cv = 0.0
        else:
            try:
                std_count = statistics.stdev(counts)
            except statistics.StatisticsError:
                std_count = 0.0
            cv = std_count / mean_count
            # cv=0 → perfectly uniform = score 100
            # cv=1 → highly bursty = score ~0
            # Cap cv at 1.0 for score floor at 0
            score = round(max(0.0, (1.0 - min(cv, 1.0))) * 100, 2)

        return ConsistencyResult(
            score=score,
            mode="frequency_variance",
            active_posts=n,
            window_post_counts=counts,
            frequency_cv=round(cv, 4) if mean_count > 0 else None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Pillar 4 — Depth
# API-derived. Engagement behaviour.
# v1.0 definition: reply ratio + quote ratio + participation rate.
# Reply depth traversal deferred to v1.1 — documented limitation.
# ─────────────────────────────────────────────────────────────────────────────

def _score_depth(active_posts: list) -> DepthResult:
    """
    Depth = engagement behaviour.

    Components:
        reply_ratio       = replies / active
        quote_ratio       = quotes / active
        participation_rate = (replies + quotes) / active

    Score = participation_rate × 100.
    All three components recorded in audit trail for transparency.

    v1.0 known limitation: does not measure conversational reply depth
    (nested thread traversal). Documented in methodology.
    """
    n = len(active_posts)
    if n == 0:
        return DepthResult(
            score=0.0,
            reply_ratio=0.0,
            quote_ratio=0.0,
            participation_rate=0.0,
            active_posts=0,
        )

    replies = sum(1 for p in active_posts if p.get("is_reply"))
    quotes  = sum(1 for p in active_posts if p.get("is_quote"))

    reply_ratio        = replies / n
    quote_ratio        = quotes / n
    participation_rate = (replies + quotes) / n

    score = round(participation_rate * 100, 2)

    return DepthResult(
        score=score,
        reply_ratio=round(reply_ratio, 4),
        quote_ratio=round(quote_ratio, 4),
        participation_rate=round(participation_rate, 4),
        active_posts=n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Canonical snapshot + hash
# ─────────────────────────────────────────────────────────────────────────────

def canonical_hash(snapshot_dict: dict) -> str:
    """
    Deterministic SHA-256 of a snapshot dict.
    Rules (non-negotiable):
      - sort_keys=True for deterministic key order
      - separators=(',',':') for no whitespace
      - ensure_ascii=False to preserve unicode
      - All scores must be rounded to 2dp BEFORE calling this
      - Timestamps must be ISO 8601 with no milliseconds BEFORE calling this
    """
    canonical = json.dumps(
        snapshot_dict,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _normalise_timestamp(dt: datetime) -> str:
    """Strip milliseconds. ISO 8601 with UTC offset."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def _attach_timestamps(posts: list) -> list:
    """
    Parse createdDate → unix timestamp on each post for time-window splitting.
    Stored as _ts (float). Non-destructive to other fields.
    """
    enriched = []
    for p in posts:
        p = dict(p)
        raw = p.get("createdDate") or p.get("created_at") or ""
        try:
            if raw:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                p["_ts"] = dt.timestamp()
            else:
                p["_ts"] = None
        except (ValueError, AttributeError):
            p["_ts"] = None
        enriched.append(p)
    return enriched


def score_epoch(
    collection,      # EpochPostCollection from fetcher
    classifier,      # Classifier instance from evaluation/classifier.py
) -> EpochSnapshot:
    """
    Full scoring pipeline for one epoch.

    1. Pre-classify posts into tracks (classify / greeting / null)
    2. Run LLM topic classifier on TRACK_CLASSIFY posts
    3. Score four pillars
    4. Build and hash snapshot

    Returns a fully populated EpochSnapshot.
    """
    posts = _attach_timestamps(collection.posts)
    epoch_start = datetime.fromisoformat(collection.epoch_start.replace("Z", "+00:00"))
    epoch_end   = datetime.fromisoformat(collection.epoch_end.replace("Z", "+00:00"))
    scored_at   = datetime.now(timezone.utc)

    # ── Step 1: Track routing ─────────────────────────────────────────────
    classified_posts = []
    greeting_posts   = []
    null_posts       = []

    for post in posts:
        track = _pre_classify(post)
        if track == TRACK_CLASSIFY:
            classified_posts.append(post)
        elif track == TRACK_GREETING:
            greeting_posts.append(post)
        else:
            null_posts.append(post)

    active_posts = classified_posts + greeting_posts
    breakdown = PostBreakdown(
        total=len(posts),
        classified=len(classified_posts),
        greeting=len(greeting_posts),
        null_track=len(null_posts),
        active=len(active_posts),
    )

    logger.info(
        f"Post breakdown: {breakdown.total} total | "
        f"{breakdown.classified} classify | "
        f"{breakdown.greeting} greeting | "
        f"{breakdown.null_track} null"
    )

    # Gate: need enough active posts to score
    if breakdown.active < MIN_POST_THRESHOLD:
        raise ValueError(
            f"Only {breakdown.active} active posts after track routing. "
            f"Minimum required: {MIN_POST_THRESHOLD}."
        )

    # ── Step 2: LLM topic classification (batched) ──────────────────────
    logger.info(f"Running batch classification on {len(classified_posts)} posts...")
    classified_with_cats = classifier.classify_batch(classified_posts)

    classifications = {}  # post_id → category
    for post in classified_with_cats:
        post_id = post.get("id") or post.get("postId") or str(id(post))
        classifications[post_id] = post.get("category", "Null")
        logger.debug(f"  {str(post_id)[:8]}… → {classifications[post_id]}")

    logger.info(f"Classified {len(classifications)} posts via LLM (batched)")

    # ── Step 3: Score four pillars ────────────────────────────────────────
    originality = _score_originality(active_posts, breakdown.active)
    focus       = _score_focus(classified_posts, classifications)
    consistency = _score_consistency(active_posts, classifications, epoch_start, epoch_end)
    depth       = _score_depth(active_posts)

    # ── Step 4: Composite ────────────────────────────────────────────────
    composite = round(
        sum([
            originality.score * COMPOSITE_WEIGHTS["originality"],
            focus.score       * COMPOSITE_WEIGHTS["focus"],
            consistency.score * COMPOSITE_WEIGHTS["consistency"],
            depth.score       * COMPOSITE_WEIGHTS["depth"],
        ]),
        2,
    )

    scores = {
        "originality":  round(originality.score, 2),
        "focus":        round(focus.score, 2),
        "consistency":  round(consistency.score, 2),
        "depth":        round(depth.score, 2),
        "composite":    composite,
    }

    # ── Step 5: Build snapshot dict (pre-hash) ───────────────────────────
    snap_dict = {
        "handle":       collection.handle,
        "user_id":      collection.user_id,
        "epoch_start":  _normalise_timestamp(epoch_start),
        "epoch_end":    _normalise_timestamp(epoch_end),
        "scored_at":    _normalise_timestamp(scored_at),
        "post_breakdown": {
            "total":      breakdown.total,
            "classified": breakdown.classified,
            "greeting":   breakdown.greeting,
            "null_track": breakdown.null_track,
            "active":     breakdown.active,
        },
        "scores": scores,
        "focus_detail": {
            "entropy":             focus.entropy,
            "max_entropy":         focus.max_entropy,
            "topic_distribution":  focus.topic_distribution,
            "other_dominance":     focus.other_dominance,
            "other_cap_applied":   focus.other_cap_applied,
        },
        "consistency_detail": {
            "mode":                consistency.mode,
            "active_posts":        consistency.active_posts,
            "window_entropies":    consistency.window_entropies,
            "entropy_std":         consistency.entropy_std,
            "window_post_counts":  consistency.window_post_counts,
            "frequency_cv":        consistency.frequency_cv,
        },
        "depth_detail": {
            "reply_ratio":         depth.reply_ratio,
            "quote_ratio":         depth.quote_ratio,
            "participation_rate":  depth.participation_rate,
        },
        "originality_detail": {
            "original_count":  originality.original_count,
            "reply_count":     originality.reply_count,
            "quote_count":     originality.quote_count,
        },
        "provenance": {
            "prompt_hash":         classifier.prompt_hash,
            "prompt_version":      classifier.prompt_version,
            "model":               classifier.model,
            "methodology_version": METHODOLOGY_VERSION,
            "collection_hash":     collection.collection_hash,
        },
    }

    # ── Step 6: Canonical hash ───────────────────────────────────────────
    snap_hash = canonical_hash(snap_dict)
    snap_dict["snapshot_hash"] = snap_hash

    logger.info(
        f"Epoch scored for @{collection.handle} | "
        f"composite={composite} | hash={snap_hash[:12]}…"
    )
    logger.info(
        f"  Originality={scores['originality']} | "
        f"Focus={scores['focus']} | "
        f"Consistency={scores['consistency']} | "
        f"Depth={scores['depth']}"
    )

    return snap_dict
