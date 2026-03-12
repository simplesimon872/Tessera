"""
bot/parser.py — Parse Arena notifications into bot commands.

Confirmed notification structure from FJ bot + Arena API:
    notification.title  — e.g. "@handle mentioned you in a thread"
    notification.link   — e.g. "/handle/thread/<thread_uuid>"
    notification.createdOn — ISO timestamp

Thread content comes back as HTML — we strip it before parsing.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

BOT_HANDLE = "bannerusmaximus"

MENTION_SUFFIX         = "mentioned you in a thread"
MENTION_SUFFIX_COMMENT = "mentioned you in a comment"
REPLY_SUFFIX           = "replied:"

# Valid commands
CMD_CLAIM   = "claim"
CMD_REVEAL  = "reveal"
CMD_INSPECT = "inspect"

VALID_COMMANDS = {CMD_CLAIM, CMD_REVEAL, CMD_INSPECT}


@dataclass
class ParsedCommand:
    """A validated, parsed command from a notification."""
    notification_id:  str
    thread_id:        str
    issuer_handle:    str
    issuer_arena_id:  str
    command:          str                    # claim | reveal | inspect
    target_handle:    Optional[str] = None   # inspect only
    raw_content:      str = ""


@dataclass
class ParseResult:
    """Result of attempting to parse a notification."""
    ok:       bool
    command:  Optional[ParsedCommand] = None
    reason:   Optional[str] = None           # why it was skipped/rejected


def is_mention(notification: dict) -> bool:
    """
    Return True if notification is a @mention.
    Handles both variants confirmed from Arena API:
      - "mentioned you in a thread"
      - "mentioned you in a comment"
    """
    title = notification.get("title", "").strip()
    return title.endswith(MENTION_SUFFIX) or title.endswith(MENTION_SUFFIX_COMMENT)


def is_reply_to_bot(notification: dict) -> bool:
    """
    Return True if notification is a direct reply to one of the bot's posts.
    Title format confirmed from Arena API: "[Name] replied:"
    Note: this catches ALL replies in threads — we filter out non-command
    replies downstream in parse_reply_notification via parse_reply_command.
    """
    title = notification.get("title", "").strip()
    return title.endswith(REPLY_SUFFIX)


def parse_reply_command(thread_content: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse a command from a plain reply (no @bannerusmaximus prefix required).

    Someone replying to a bot post only needs to write the command word.
    Supports:
        "claim"
        "reveal"
        "inspect @handle"
        "inspect handle"

    Returns (command, target_handle) — target_handle without @ prefix.
    """
    text = strip_html(thread_content).lower().strip()

    # Remove any @bannerusmaximus mention if they included it anyway
    tokens = text.split()
    tokens = [t for t in tokens if not t.startswith("@0x") and t != f"@{BOT_HANDLE}"]
    if not tokens:
        return None, None

    command = tokens[0].strip().lower()

    if command not in VALID_COMMANDS:
        return None, None

    target = None
    if command == CMD_INSPECT and len(tokens) >= 2:
        target = tokens[1].lstrip("@").strip().lower()
        if not target:
            target = None

    return command, target


def extract_thread_id(notification: dict) -> Optional[str]:
    """
    Extract thread UUID from notification link.
    Link format: /handle/thread/<uuid> or similar.
    UUID is always the last 36 chars.
    Confirmed from FJ bot: link.slice(-36)
    """
    link = notification.get("link", "")
    if len(link) >= 36:
        return link[-36:]
    return None


def strip_html(html: str) -> str:
    """
    Strip HTML tags from thread content.
    More robust than FJ's magic-number splice approach.
    """
    text = re.sub(r"<br\s*/?>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = " ".join(text.split())
    return text.strip()


def parse_command(thread_content: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse command keyword and optional target from thread content.

    Strips the @bannerusmaximus mention, then reads the first keyword.

    Examples:
        "@bannerusmaximus claim"            → ("claim", None)
        "@bannerusmaximus reveal"           → ("reveal", None)
        "@bannerusmaximus inspect @rhynelf" → ("inspect", "rhynelf")
        "@bannerusmaximus foobar"           → ("foobar", None)

    Returns (command, target_handle) — target_handle without @ prefix.
    """
    text = strip_html(thread_content).lower().strip()

    # Tokenise and strip all @bot mentions (handle or wallet address format)
    # Keep remaining tokens intact so "inspect @target" still works.
    # Bot mention is always first token — anything starting with @0x or
    # matching the bot handle is removed from the front.
    tokens_raw = text.split()
    # Drop leading @mentions (the bot tag, however it renders)
    while tokens_raw and tokens_raw[0].startswith("@"):
        tokens_raw.pop(0)
    text = " ".join(tokens_raw)

    # Tokenise
    tokens = text.split()
    if not tokens:
        return None, None

    command = tokens[0].strip().lower()

    # Extract target for inspect
    target = None
    if command == CMD_INSPECT and len(tokens) >= 2:
        target = tokens[1].lstrip("@").strip().lower()
        if not target:
            target = None

    return command, target


def parse_notification(
    notification: dict,
    thread: dict,
    since_ms: float,
) -> ParseResult:
    """
    Attempt to parse a notification into a ParsedCommand.

    Args:
        notification: Raw notification dict from Arena API
        thread:       Full thread dict fetched from Arena API
        since_ms:     Bot start timestamp in ms — ignore older notifications

    Returns ParseResult with ok=True and a ParsedCommand, or ok=False with reason.
    """
    notification_id = notification.get("id", "")

    # Only process mentions
    if not is_mention(notification):
        return ParseResult(ok=False, reason="not_mention")

    # Time check — ignore notifications from before bot started
    from datetime import datetime, timezone
    created_on = notification.get("createdOn", "")
    try:
        noti_dt = datetime.fromisoformat(created_on.replace("Z", "+00:00"))
        noti_ms = noti_dt.timestamp() * 1000
        if noti_ms < since_ms:
            return ParseResult(ok=False, reason="too_old")
    except Exception:
        return ParseResult(ok=False, reason="bad_timestamp")

    # Extract thread ID
    thread_id = extract_thread_id(notification)
    if not thread_id:
        return ParseResult(ok=False, reason="no_thread_id")

    # Extract issuer info from thread
    user = thread.get("user", {})
    issuer_handle   = user.get("ixHandle", "")
    issuer_arena_id = user.get("id", "") or user.get("userId", "")

    if not issuer_handle:
        return ParseResult(ok=False, reason="no_issuer_handle")

    # Parse command from content
    raw_content = thread.get("content", "")
    command, target = parse_command(raw_content)

    if not command:
        return ParseResult(ok=False, reason="no_command")

    if command not in VALID_COMMANDS:
        return ParseResult(
            ok=False,
            reason=f"unknown_command:{command}",
        )

    if command == CMD_INSPECT and not target:
        return ParseResult(ok=False, reason="inspect_missing_target")

    return ParseResult(
        ok=True,
        command=ParsedCommand(
            notification_id=notification_id,
            thread_id=thread_id,
            issuer_handle=issuer_handle,
            issuer_arena_id=issuer_arena_id,
            command=command,
            target_handle=target,
            raw_content=raw_content,
        )
    )


def parse_reply_notification(
    notification: dict,
    thread: dict,
    since_ms: float,
) -> ParseResult:
    """
    Parse a reply-to-bot notification into a ParsedCommand.

    Same as parse_notification but:
    - Triggered by "replied to your thread" notifications
    - Uses parse_reply_command (no @bannerusmaximus prefix needed)
    - Allows bare command words: "claim", "reveal", "inspect @handle"
    """
    notification_id = notification.get("id", "")

    if not is_reply_to_bot(notification):
        return ParseResult(ok=False, reason="not_a_reply")

    # Time check
    from datetime import datetime, timezone
    created_on = notification.get("createdOn", "")
    try:
        noti_dt = datetime.fromisoformat(created_on.replace("Z", "+00:00"))
        noti_ms = noti_dt.timestamp() * 1000
        if noti_ms < since_ms:
            return ParseResult(ok=False, reason="too_old")
    except Exception:
        return ParseResult(ok=False, reason="bad_timestamp")

    # Extract thread ID
    thread_id = extract_thread_id(notification)
    if not thread_id:
        return ParseResult(ok=False, reason="no_thread_id")

    # Extract issuer info from thread
    user = thread.get("user", {})
    issuer_handle   = user.get("ixHandle", "")
    issuer_arena_id = user.get("id", "") or user.get("userId", "")

    if not issuer_handle:
        return ParseResult(ok=False, reason="no_issuer_handle")

    # Parse bare command (no @bannerusmaximus prefix required)
    raw_content = thread.get("content", "")
    command, target = parse_reply_command(raw_content)

    if not command:
        return ParseResult(ok=False, reason="no_command")

    if command == CMD_INSPECT and not target:
        return ParseResult(ok=False, reason="inspect_missing_target")

    return ParseResult(
        ok=True,
        command=ParsedCommand(
            notification_id=notification_id,
            thread_id=thread_id,
            issuer_handle=issuer_handle,
            issuer_arena_id=issuer_arena_id,
            command=command,
            target_handle=target,
            raw_content=raw_content,
        )
    )
