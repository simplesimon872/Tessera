"""
test_day6.py — Bot layer test suite.

Tests:
  1.  Parser — is_mention correctly identifies mention notifications
  2.  Parser — non-mention notifications are skipped
  3.  Parser — strip_html removes tags correctly
  4.  Parser — claim command parsed correctly
  5.  Parser — reveal command parsed correctly
  6.  Parser — inspect command parsed correctly
  7.  Parser — inspect missing target returns error result
  8.  Parser — unknown command returns parse result with reason
  9.  Parser — old notification skipped by timestamp
  10. Parser — thread ID extracted correctly from link
  11. Poster — format_reveal produces correct structure
  12. Poster — format_claim_success contains handle and URL
  13. Poster — format_inspect_unsealed contains pressure framing
  14. Poster — format_rate_limited contains count
  15. Poster — format_unknown_command lists all 3 commands

Usage:
    python test_day6.py

No API calls made — all tests run offline.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.WARNING)

PASS = "✅"
FAIL = "❌"
results = []


# ── Test runner ───────────────────────────────────────────────────────────────

def test(name):
    def decorator(fn):
        def wrapper():
            print(f"\n{'═'*60}")
            print(f"TEST — {name}")
            print(f"{'─'*60}")
            try:
                fn()
                print(f"{PASS} {name}")
                results.append((name, True, None))
            except Exception as e:
                print(f"{FAIL} {name}: {e}")
                results.append((name, False, str(e)))
        return wrapper
    return decorator


# ── Fixtures ──────────────────────────────────────────────────────────────────

BOT_START_MS = 0  # accept all timestamps in tests

def _mention_notification(handle="simplesimon872", thread_id="a" * 36, age_ms=None):
    from datetime import timedelta
    if age_ms is None:
        ts = datetime.now(timezone.utc).isoformat()
    else:
        dt = datetime.now(timezone.utc) - timedelta(milliseconds=age_ms)
        ts = dt.isoformat()
    return {
        "id":        "notif-" + "a" * 32,
        "title":     f"@{handle} mentioned you in a thread",
        "link":      f"/{handle}/thread/{thread_id}",
        "createdOn": ts,
        "text":      "",
    }

def _thread(content="@bannerusmaximus claim", handle="simplesimon872", arena_id="user-123"):
    return {
        "id":          "a" * 36,
        "content":     f"<p>{content}</p>",
        "createdDate": datetime.now(timezone.utc).isoformat(),
        "user": {
            "ixHandle": handle,
            "id":        arena_id,
        }
    }

def _snapshot():
    return {
        "handle": "simplesimon872",
        "epoch": {
            "start": "2026-02-07T00:00:00+00:00",
            "end":   "2026-03-07T00:00:00+00:00",
        },
        "scores": {
            "composite":    47.89,
            "originality":  93.33,
            "focus":        44.47,
            "consistency":  47.08,
            "depth":         6.67,
            "consistency_mode": "frequency_variance",
            "other_cap_applied": False,
        },
        "post_breakdown": {
            "total":      45,
            "classified": 30,
            "greeting":   10,
            "null_track":  5,
            "active":     40,
        },
        "methodology": {
            "version":         "v1.0",
            "prompt_hash":     "1deff518231c",
            "model":           "claude-haiku-4-5",
            "collection_hash": "abc123",
        },
        "snapshot_hash": "x" * 64,
    }


# ── Parser tests ──────────────────────────────────────────────────────────────

@test("Parser — is_mention correctly identifies mention notifications")
def test_is_mention():
    from bot.parser import is_mention
    assert is_mention({"title": "@simplesimon872 mentioned you in a thread"}) is True
    assert is_mention({"title": "You got tipped"}) is False
    assert is_mention({"title": ""}) is False
    print("  mention/non-mention detection: ✅")


@test("Parser — non-mention notifications are skipped")
def test_non_mention_skipped():
    from bot.parser import parse_notification
    notif = {"id": "x", "title": "You got tipped", "link": "", "createdOn": datetime.now(timezone.utc).isoformat()}
    result = parse_notification(notif, {}, BOT_START_MS)
    assert result.ok is False
    assert result.reason == "not_mention"
    print(f"  Reason: {result.reason}: ✅")


@test("Parser — strip_html removes tags correctly")
def test_strip_html():
    from bot.parser import strip_html
    assert strip_html("<p>hello world</p>") == "hello world"
    assert strip_html("<p>@bannerusmaximus claim</p>") == "@bannerusmaximus claim"
    assert strip_html("<br>line two") == "line two"
    assert strip_html("no tags here") == "no tags here"
    print("  HTML stripping: ✅")


@test("Parser — claim command parsed correctly")
def test_parse_claim():
    from bot.parser import parse_notification
    notif = _mention_notification()
    thread = _thread("@bannerusmaximus claim")
    result = parse_notification(notif, thread, BOT_START_MS)
    assert result.ok is True
    assert result.command.command == "claim"
    assert result.command.issuer_handle == "simplesimon872"
    assert result.command.target_handle is None
    print(f"  command={result.command.command} issuer={result.command.issuer_handle}: ✅")


@test("Parser — reveal command parsed correctly")
def test_parse_reveal():
    from bot.parser import parse_notification
    notif = _mention_notification()
    thread = _thread("@bannerusmaximus reveal")
    result = parse_notification(notif, thread, BOT_START_MS)
    assert result.ok is True
    assert result.command.command == "reveal"
    print(f"  command={result.command.command}: ✅")


@test("Parser — inspect command parsed correctly")
def test_parse_inspect():
    from bot.parser import parse_notification
    notif = _mention_notification()
    thread = _thread("@bannerusmaximus inspect @mcversepilot")
    result = parse_notification(notif, thread, BOT_START_MS)
    assert result.ok is True
    assert result.command.command == "inspect"
    assert result.command.target_handle == "mcversepilot"
    print(f"  command={result.command.command} target={result.command.target_handle}: ✅")


@test("Parser — inspect missing target returns error result")
def test_parse_inspect_no_target():
    from bot.parser import parse_notification
    notif = _mention_notification()
    thread = _thread("@bannerusmaximus inspect")
    result = parse_notification(notif, thread, BOT_START_MS)
    assert result.ok is False
    assert result.reason == "inspect_missing_target"
    print(f"  Reason: {result.reason}: ✅")


@test("Parser — unknown command returns parse result with reason")
def test_parse_unknown():
    from bot.parser import parse_notification
    notif = _mention_notification()
    thread = _thread("@bannerusmaximus foobar")
    result = parse_notification(notif, thread, BOT_START_MS)
    assert result.ok is False
    assert "unknown_command" in result.reason
    print(f"  Reason: {result.reason}: ✅")


@test("Parser — old notification skipped by timestamp")
def test_parse_old_notification():
    from bot.parser import parse_notification
    # Notification from 1 hour ago
    notif = _mention_notification(age_ms=3_600_000)
    thread = _thread("@bannerusmaximus claim")
    bot_start_ms = datetime.now(timezone.utc).timestamp() * 1000
    result = parse_notification(notif, thread, bot_start_ms)
    assert result.ok is False
    assert result.reason == "too_old"
    print(f"  Reason: {result.reason}: ✅")


@test("Parser — thread ID extracted correctly from link")
def test_thread_id_extraction():
    from bot.parser import extract_thread_id
    thread_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    notif = {"link": f"/simplesimon872/thread/{thread_id}"}
    extracted = extract_thread_id(notif)
    assert extracted == thread_id
    print(f"  Extracted: {extracted}: ✅")


# ── Poster tests ──────────────────────────────────────────────────────────────

@test("Poster — format_reveal produces correct structure")
def test_format_reveal():
    from bot.poster import format_reveal
    snap = _snapshot()
    reply = format_reveal("simplesimon872", snap, {}, sealed=False)
    assert "@simplesimon872" in reply
    assert "47.89" in reply or "47.9" in reply
    assert "Originality" in reply
    assert "Focus" in reply
    assert "Consistency" in reply
    assert "Depth" in reply
    assert "tessera.xyz" in reply
    print(f"  All fields present: ✅")
    print(f"  Preview:\n{reply[:200]}…")


@test("Poster — format_claim_success contains handle and URL")
def test_format_claim_success():
    from bot.poster import format_claim_success
    reply = format_claim_success("simplesimon872")
    assert "@simplesimon872" in reply
    assert "tessera.xyz" in reply
    assert "Sunday" in reply
    print(f"  Handle + URL + Sunday seal: ✅")


@test("Poster — format_inspect_unsealed contains pressure framing")
def test_format_inspect_unsealed():
    from bot.poster import format_inspect_unsealed
    reply = format_inspect_unsealed("rhynelf", "mcversepilot", _snapshot())
    assert "@rhynelf" in reply
    assert "@mcversepilot" in reply
    assert "no sealed record" in reply.lower() or "unsealed" in reply.lower()
    assert "claim" in reply.lower()
    print(f"  Pressure framing present: ✅")


@test("Poster — format_rate_limited contains count")
def test_format_rate_limited():
    from bot.poster import format_rate_limited
    reply = format_rate_limited("spammer", 5)
    assert "@spammer" in reply
    assert "5" in reply
    print(f"  Rate limit message correct: ✅")


@test("Poster — format_unknown_command lists all 3 commands")
def test_format_unknown_command():
    from bot.poster import format_unknown_command
    reply = format_unknown_command("simplesimon872", "wtf")
    assert "claim" in reply
    assert "reveal" in reply
    assert "inspect" in reply
    print(f"  All 3 commands listed: ✅")


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    tests = [
        test_is_mention,
        test_non_mention_skipped,
        test_strip_html,
        test_parse_claim,
        test_parse_reveal,
        test_parse_inspect,
        test_parse_inspect_no_target,
        test_parse_unknown,
        test_parse_old_notification,
        test_thread_id_extraction,
        test_format_reveal,
        test_format_claim_success,
        test_format_inspect_unsealed,
        test_format_rate_limited,
        test_format_unknown_command,
    ]

    print("\n" + "═" * 60)
    print("  Tessera — Day 6 Bot Layer Tests")
    print("═" * 60)

    for t in tests:
        t()

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
        print(f"\n  ✅ Day 6 complete.")
    else:
        print(f"\n  ❌ {failed} test(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
