"""
bot/listener.py — Arena notification polling loop for @bannerusmaximus.

Architecture:
    - Polls every 60 seconds
    - Stores last processed notification ID in bot_state table (survives restarts)
    - Idempotent: notification_id dedup via bot_state
    - Rate limit: max 5 commands per user per hour (command_log table)
    - Global cap: max 30 commands per minute across all users
    - Backoff: 3 consecutive API failures → wait 5 minutes
    - Silence alert: logs ERROR if polling loop silent for >5 minutes

Run:
    python -m bot.listener

Requires in .env:
    ARENA_API_KEY        — bannerusmaximus bot API key
    ANTHROPIC_API_KEY    — for LLM classifier
    SUPABASE_URL         — Supabase project URL
    SUPABASE_KEY         — Supabase anon key
"""

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("bot.listener")

# ── Config ────────────────────────────────────────────────────────────────────

POLL_INTERVAL_S      = 60       # seconds between notification checks
BACKOFF_AFTER        = 3        # consecutive failures before backoff
BACKOFF_WAIT_S       = 300      # 5 minutes backoff
SILENCE_ALERT_S      = 300      # alert if no successful poll in 5 min
RATE_LIMIT_PER_USER  = 5        # max commands per user per hour
GLOBAL_CAP_PER_MIN   = 30       # max commands across all users per minute


def run():
    """Main entry point. Runs forever."""
    from ingestion.arena_client import ArenaClient
    from bot.bannerus_client import BannerusClient
    from bot.parser import parse_notification, VALID_COMMANDS, CMD_CLAIM, CMD_REVEAL, CMD_INSPECT
    from bot.handlers import handle_claim, handle_reveal, handle_inspect, handle_unknown_command
    from database.client import (
        get_bot_state, set_bot_state,
        log_command, count_recent_commands,
    )

    bannerus_token = os.getenv("BANNERUS_API_KEY", "")
    if not bannerus_token:
        raise EnvironmentError("BANNERUS_API_KEY not set in .env — this is the Bearer token for the bannerusmaximus account")

    client = BannerusClient(bearer_token=bannerus_token)

    # Bot start time — notifications older than this are skipped
    bot_start_ms = datetime.now(timezone.utc).timestamp() * 1000
    logger.info(f"@bannerusmaximus listener starting | bot_start_ms={bot_start_ms:.0f}")

    # Load last processed notification ID (survives restart)
    last_notification_id = get_bot_state("last_processed_notification_id")
    logger.info(f"Last processed notification ID: {last_notification_id or 'none (fresh start)'}")

    consecutive_failures = 0
    last_successful_poll = time.time()
    global_commands_this_minute = 0
    global_minute_start = time.time()

    # On fresh start, fast-forward past all existing notifications so we
    # don't try to process old follows/trades from before the bot launched.
    if not last_notification_id:
        logger.info("Fresh start — fast-forwarding past existing notifications…")
        try:
            existing = client.get_notifications(page_size=100)
            if existing:
                last_notification_id = existing[0].get("id", "")
                set_bot_state("last_processed_notification_id", last_notification_id)
                logger.info(f"Fast-forwarded to {last_notification_id[:8]}… — watching for NEW mentions only")
        except Exception as e:
            logger.warning(f"Could not fast-forward: {e}")

    logger.info(f"Polling every {POLL_INTERVAL_S}s — waiting for @bannerusmaximus mentions…")

    while True:
        try:
            # ── Silence alert ─────────────────────────────────────────────────
            if time.time() - last_successful_poll > SILENCE_ALERT_S:
                logger.error(
                    f"Polling loop silent for >{SILENCE_ALERT_S}s — check connectivity"
                )

            # ── Fetch notifications ───────────────────────────────────────────
            logger.info("Polling /agents/notifications…")
            notifications = client.get_notifications(page_size=100)
            consecutive_failures = 0
            last_successful_poll = time.time()

            if not notifications:
                logger.info("No notifications returned — sleeping")
                time.sleep(POLL_INTERVAL_S)
                continue

            # Find how many are new since last processed
            new_count = 0
            for n in notifications:
                if n.get("id") == last_notification_id:
                    break
                new_count += 1

            logger.info(f"Got {len(notifications)} notifications | {new_count} new since last poll")

            if new_count == 0:
                logger.info("Nothing new — sleeping")
                time.sleep(POLL_INTERVAL_S)
                continue

            # ── Reset global per-minute cap ───────────────────────────────────
            if time.time() - global_minute_start > 60:
                global_commands_this_minute = 0
                global_minute_start = time.time()

            # ── Process new notifications only ────────────────────────────────
            for notification in notifications[:new_count]:
                notification_id = notification.get("id", "")
                title = notification.get("title", "")
                ntype = notification.get("type", "?")

                if "mentioned you in a thread" in title:
                    logger.info(f"  ✉ [{ntype}] {notification_id[:8]}… | {title[:60]}")

                # Idempotency guard
                dedup_key = f"processed_notification:{notification_id}"
                if get_bot_state(dedup_key):
                    last_notification_id = notification_id
                    continue

                # Only care about mentions
                from bot.parser import is_mention
                if not is_mention(notification):
                    logger.debug(f"    Not a mention (type={ntype}) — skipping")
                    set_bot_state(dedup_key, "1")
                    last_notification_id = notification_id
                    set_bot_state("last_processed_notification_id", notification_id)
                    continue

                logger.info(f"    ✉ MENTION detected — fetching thread…")

                # Parse
                try:
                    thread_id = _extract_thread_id(notification)
                    if not thread_id:
                        logger.warning(f"    Could not extract thread ID from link: {notification.get('link')}")
                        set_bot_state(dedup_key, "1")
                        last_notification_id = notification_id
                        set_bot_state("last_processed_notification_id", notification_id)
                        continue

                    logger.info(f"    Thread ID: {thread_id}")
                    thread = client.get_thread(thread_id)
                    logger.info(f"    Thread content: {thread.get('content', '')[:80]}")
                    result = parse_notification(notification, thread, bot_start_ms)

                except Exception as e:
                    logger.warning(f"    Parse error: {e}")
                    set_bot_state(dedup_key, "1")
                    last_notification_id = notification_id
                    set_bot_state("last_processed_notification_id", notification_id)
                    continue

                if not result.ok:
                    logger.info(f"    Skipped — reason: {result.reason}")
                    set_bot_state(dedup_key, "1")
                    last_notification_id = notification_id
                    set_bot_state("last_processed_notification_id", notification_id)
                    continue

                cmd = result.command
                handle = cmd.issuer_handle
                logger.info(f"    Command: {cmd.command} | @{handle}" +
                            (f" → @{cmd.target_handle}" if cmd.target_handle else ""))

                # ── Rate limit ────────────────────────────────────────────────
                recent = count_recent_commands(handle, window_minutes=60)
                if recent >= RATE_LIMIT_PER_USER:
                    logger.warning(f"    Rate limit: @{handle} ({recent}/hr)")
                    from bot.poster import send_reply, format_rate_limited
                    try:
                        send_reply(client, format_rate_limited(handle, recent))
                    except Exception:
                        pass
                    set_bot_state(dedup_key, "1")
                    last_notification_id = notification_id
                    set_bot_state("last_processed_notification_id", notification_id)
                    continue

                # ── Global cap ────────────────────────────────────────────────
                if global_commands_this_minute >= GLOBAL_CAP_PER_MIN:
                    logger.warning(f"    Global cap hit — skipping @{handle}")
                    set_bot_state(dedup_key, "1")
                    last_notification_id = notification_id
                    set_bot_state("last_processed_notification_id", notification_id)
                    continue

                # ── Route ─────────────────────────────────────────────────────
                log_command(handle, cmd.command, cmd.target_handle)
                global_commands_this_minute += 1

                logger.info(f"    Routing to handler…")
                success = _route(cmd, client)

                if success:
                    logger.info(f"    ✅ Handled: {cmd.command} | @{handle}")
                else:
                    logger.error(f"    ❌ Handler failed: {cmd.command} | @{handle}")

                set_bot_state(dedup_key, "1")
                last_notification_id = notification_id
                set_bot_state("last_processed_notification_id", notification_id)

        except KeyboardInterrupt:
            logger.info("Shutting down — KeyboardInterrupt")
            break

        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Poll error #{consecutive_failures}: {e}", exc_info=True)

            if consecutive_failures >= BACKOFF_AFTER:
                logger.warning(
                    f"{consecutive_failures} consecutive failures — "
                    f"backing off {BACKOFF_WAIT_S}s"
                )
                time.sleep(BACKOFF_WAIT_S)
                consecutive_failures = 0
                continue

        try:
            time.sleep(POLL_INTERVAL_S)
        except KeyboardInterrupt:
            break

    uptime_s = int(time.time() * 1000 - bot_start_ms) // 1000
    logger.info(
        f"@bannerusmaximus listener stopped gracefully | "
        f"uptime={uptime_s//3600}h {(uptime_s%3600)//60}m {uptime_s%60}s"
    )


def _extract_thread_id(notification: dict) -> str | None:
    """Extract 36-char thread UUID from notification link."""
    link = notification.get("link", "")
    if len(link) >= 36:
        return link[-36:]
    return None


def _mark_processed(set_fn, dedup_key, notification_id, last_id):
    set_fn(dedup_key, "1")


def _route(cmd, client) -> bool:
    """Route a parsed command to the correct handler."""
    from bot.parser import CMD_CLAIM, CMD_REVEAL, CMD_INSPECT
    from bot.handlers import (
        handle_claim, handle_reveal, handle_inspect, handle_unknown_command
    )

    if cmd.command == CMD_CLAIM:
        return handle_claim(cmd, client)
    elif cmd.command == CMD_REVEAL:
        return handle_reveal(cmd, client)
    elif cmd.command == CMD_INSPECT:
        return handle_inspect(cmd, client)
    else:
        return handle_unknown_command(cmd, client)


if __name__ == "__main__":
    run()
