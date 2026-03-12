"""
bot/poster.py — Format and post Tessera bot replies to Arena.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _fmt(score):
    if score is None:
        return "—"
    return f"{score:.1f}"


def _days_until_seal(epoch_end_str):
    from datetime import datetime, timezone
    try:
        end = datetime.fromisoformat(epoch_end_str)
        now = datetime.now(timezone.utc)
        return max(0, (end - now).days)
    except Exception:
        return 0


def format_claim_success(handle):
    return (
        f"@{handle} — Tessera activated ✅\n\n"
        f"Your behavioral record is now live. "
        f"It will seal automatically every Sunday at midnight UTC.\n\n"
        f"Tag me with 'reveal' any time to see your current epoch score."
    )


def format_claim_already_claimed(handle, epoch, scores):
    if scores:
        composite = _fmt(scores.get("composite"))
        return (
            f"@{handle} — already claimed ✅\n\n"
            f"Latest epoch composite: {composite}\n"
            f"Status: {epoch.get('status', '—')}"
        )
    return (
        f"@{handle} — already claimed ✅\n\n"
        f"Your record is active and sealing automatically every Sunday."
    )


def format_reveal(handle, snapshot, epoch, sealed):
    scores    = snapshot.get("scores", {})
    ep        = snapshot.get("epoch", {})
    breakdown = snapshot.get("post_breakdown", {})

    epoch_start = ep.get("start", "")[:10]
    epoch_end   = ep.get("end", "")[:10]

    composite   = _fmt(scores.get("composite"))
    originality = _fmt(scores.get("originality"))
    focus       = _fmt(scores.get("focus"))
    consistency = _fmt(scores.get("consistency"))
    depth       = _fmt(scores.get("depth"))

    total_posts  = breakdown.get("total", "—")
    active_posts = breakdown.get("active", "—")

    if sealed:
        seal_line = "Sealed onchain ✅"
    else:
        days = _days_until_seal(ep.get("end", ""))
        seal_line = f"Seals automatically in {days} day{'s' if days != 1 else ''} (Sunday midnight UTC)"

    return (
        f"@{handle} — Epoch {epoch_start} → {epoch_end}\n\n"
        f"Composite     {composite}\n"
        f"Originality   {originality}\n"
        f"Focus         {focus}\n"
        f"Consistency   {consistency}\n"
        f"Depth         {depth}\n\n"
        f"Posts: {total_posts} total, {active_posts} active\n\n"
        f"{seal_line}"
        + (f"\n\n⚠️ Low sample size ({total_posts} posts) — scores are indicative only. More posts = more accurate." if isinstance(total_posts, int) and total_posts < 20 else "")
    )


def format_reveal_insufficient(handle, total, active):
    return (
        f"@{handle} — not enough posts to score yet\n\n"
        f"Found {total} posts, {active} active after routing. "
        f"Minimum is 5 posts to generate a score.\n\n"
        f"Keep posting and tag me with 'reveal' again."
    )


def format_inspect_sealed(issuer, target, snapshot, anchor):
    scores = snapshot.get("scores", {})
    ep     = snapshot.get("epoch", {})

    epoch_start = ep.get("start", "")[:10]
    epoch_end   = ep.get("end", "")[:10]

    composite   = _fmt(scores.get("composite"))
    originality = _fmt(scores.get("originality"))
    focus       = _fmt(scores.get("focus"))
    consistency = _fmt(scores.get("consistency"))
    depth       = _fmt(scores.get("depth"))

    tx = anchor.get("tx_hash", "")[:18] + "…" if anchor.get("tx_hash") else "—"
    profile_url = f"https://tessera-8x7.pages.dev/{target}"

    return (
        f"@{issuer} — here's @{target}'s latest sealed record\n\n"
        f"Epoch {epoch_start} → {epoch_end}\n\n"
        f"Composite     {composite}\n"
        f"Originality   {originality}\n"
        f"Focus         {focus}\n"
        f"Consistency   {consistency}\n"
        f"Depth         {depth}\n\n"
        f"Sealed onchain ✅  TX: {tx}\n\n"
        f"Full record: <a href=\"{profile_url}\">{profile_url}</a>"
    )


def format_inspect_unsealed(issuer, target, snapshot):
    scores = snapshot.get("scores", {})
    ep     = snapshot.get("epoch", {})

    epoch_start = ep.get("start", "")[:10]
    epoch_end   = ep.get("end", "")[:10]

    composite   = _fmt(scores.get("composite"))
    originality = _fmt(scores.get("originality"))
    focus       = _fmt(scores.get("focus"))
    consistency = _fmt(scores.get("consistency"))
    depth       = _fmt(scores.get("depth"))

    profile_url = f"https://tessera-8x7.pages.dev/{target}"

    return (
        f"@{issuer} — @{target} has no sealed record yet. "
        f"Here's what their epoch looks like right now:\n\n"
        f"Epoch {epoch_start} → {epoch_end}\n\n"
        f"Composite     {composite}\n"
        f"Originality   {originality}\n"
        f"Focus         {focus}\n"
        f"Consistency   {consistency}\n"
        f"Depth         {depth}\n\n"
        f"Full record: <a href=\"{profile_url}\">{profile_url}</a>\n\n"
        f"@{target} — to seal your record, post: @bannerusmaximus claim"
    )


def format_inspect_insufficient(issuer, target, total, active):
    return (
        f"@{issuer} — @{target} doesn't have enough posts to score yet\n\n"
        f"Found {total} posts, {active} active after routing. "
        f"Minimum is 5 posts to generate a score.\n\n"
        f"No Tessera record exists for @{target} yet."
    )


def format_rate_limited(handle, count):
    return (
        f"@{handle} — slow down ✋\n\n"
        f"You've sent {count} commands in the last hour. "
        f"Limit is 5. Try again later."
    )


def format_unknown_command(handle, raw):
    return (
        f"@{handle} — didn't recognise that command.\n\n"
        f"Post one of these to use Tessera:\n"
        f"  @bannerusmaximus claim\n"
        f"  @bannerusmaximus reveal\n"
        f"  @bannerusmaximus inspect @handle"
    )


def format_inspect_missing_target(handle):
    return (
        f"@{handle} — inspect needs a target handle.\n\n"
        f"Usage: @bannerusmaximus inspect @handle"
    )


def format_error(handle):
    return (
        f"@{handle} — something went wrong on my end. "
        f"Try again in a few minutes."
    )


def format_seal_notification(handle, epoch, anchor):
    epoch_start = epoch.get("epoch_start", "")[:10]
    epoch_end   = epoch.get("epoch_end", "")[:10]
    tx = anchor.get("tx_hash", "")
    return (
        f"@{handle} — your Tessera epoch has been sealed onchain ✅\n\n"
        f"Epoch: {epoch_start} → {epoch_end}\n"
        f"TX: {tx[:18]}…"
    )


def send_reply(client, content, thread_id: str = None, user_id: str = None):
    """
    Post a reply to Arena.

    If thread_id and user_id are provided, replies in-thread under the
    triggering post using /threads/answer (confirmed working endpoint).
    Falls back to a standalone top-level post if either is missing.
    """
    try:
        if thread_id and user_id:
            thread = client.create_reply(content, thread_id, user_id)
        else:
            thread = client.create_post(content)
        logger.info(f"Posted reply | id={thread.get('id', '?')[:8]}…")
        return thread
    except Exception as e:
        logger.error(f"Failed to post reply: {e}", exc_info=True)
        raise
