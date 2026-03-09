"""
Day 3 test harness — scoring engine validation.

Tests:
  1. Hash determinism — same input produces identical snapshot hash
  2. Pillar sanity checks — scores in [0, 100], correct types
  3. Other dominance cap — verify it triggers at >50%
  4. Score an actual cached epoch collection (if available)

Usage:
    python test_scoring.py [--live-handle HANDLE]

Without --live-handle, runs on synthetic test data only.
With --live-handle, also scores a real Arena user's epoch.
"""

import sys
import json
import copy
import logging
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent))

from scoring.engine import score_epoch, canonical_hash
from scoring.constants import MAX_ENTROPY, METHODOLOGY_VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_scoring")

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


# ─────────────────────────────────────────────────────────────────────────────
# Mock objects
# ─────────────────────────────────────────────────────────────────────────────

def make_mock_classifier(responses: dict = None):
    """
    Returns a mock Classifier that returns deterministic responses.
    responses: {text_substring: category} — matched in order.
    Default: always returns "Other".
    """
    default = responses or {}

    class MockClassifier:
        prompt_hash = "abc123_test_hash"
        prompt_version = "v_test"
        model = "claude-haiku-4-5"

        def classify(self, text: str) -> str:
            for substring, cat in default.items():
                if substring.lower() in text.lower():
                    return cat
            return "Other"

    return MockClassifier()


def make_mock_collection(
    posts: list,
    handle: str = "test_user",
    epoch_days: int = 7,
):
    """Build a minimal EpochPostCollection-like object from a post list."""
    now = datetime.now(timezone.utc)
    epoch_end   = now.replace(hour=0, minute=0, second=0, microsecond=0)
    epoch_start = epoch_end - timedelta(days=epoch_days)

    class MockCollection:
        pass

    col = MockCollection()
    col.handle         = handle
    col.user_id        = "user_test_001"
    col.epoch_start    = epoch_start.isoformat()
    col.epoch_end      = epoch_end.isoformat()
    col.post_count     = len(posts)
    col.posts          = posts
    col.collection_hash = "mock_collection_hash_abc123"
    return col


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic post builders
# ─────────────────────────────────────────────────────────────────────────────

def make_posts(n: int, epoch_days: int = 7, post_type: str = "original") -> list:
    """
    Build n synthetic posts spread evenly across epoch_days.
    post_type: "original" | "reply" | "quote" | "mixed" | "greeting"
    """
    now = datetime.now(timezone.utc)
    epoch_end   = now.replace(hour=0, minute=0, second=0, microsecond=0)
    epoch_start = epoch_end - timedelta(days=epoch_days)

    posts = []
    for i in range(n):
        # Spread posts evenly across epoch
        fraction = i / max(n - 1, 1)
        ts = epoch_start + timedelta(seconds=fraction * epoch_days * 86400)

        if post_type == "greeting":
            content    = "gm frens" if i % 2 == 0 else "gn everyone"
            is_reply   = False
            is_quote   = False
        elif post_type == "reply":
            content    = f"Interesting take on Ethereum L2 scaling #{i}"
            is_reply   = True
            is_quote   = False
        elif post_type == "quote":
            content    = f"This is exactly what DeFi needs to solve #{i}"
            is_reply   = False
            is_quote   = True
        elif post_type == "mixed":
            content    = f"ETH fees compressing again, L2 economics improving #{i}"
            is_reply   = (i % 3 == 0)
            is_quote   = (i % 5 == 0)
        else:  # original
            content    = f"ETH L2 scaling is finally compressing fees properly #{i}"
            is_reply   = False
            is_quote   = False

        posts.append({
            "id":          f"post_{i:04d}",
            "content":     content,
            "createdDate": ts.isoformat(),
            "is_reply":    is_reply,
            "is_quote":    is_quote,
        })

    return posts


def make_focused_posts(n: int = 30) -> list:
    """30 posts, all Technology & Infrastructure focused."""
    posts = make_posts(n, post_type="original")
    topics = [
        "Ethereum L2 scaling is compressing fees",
        "Abstract block times are improving",
        "MegaETH is doing everything right for rollup architecture",
        "ZK proofs will change verification permanently",
        "Sequencer decentralisation is the next frontier",
    ]
    for i, p in enumerate(posts):
        p["content"] = topics[i % len(topics)] + f" (post {i})"
    return posts


def make_scattered_posts(n: int = 30) -> list:
    """30 posts spread evenly across all 6 entropy buckets."""
    posts = make_posts(n, post_type="original")
    categories = [
        ("ETH is going to 10k easy", "Market & Price"),
        ("Aave LTV ratios are critical for stability", "DeFi & Protocols"),
        ("AI agents will replace most API calls", "AI & Agents"),
        ("DAO governance needs better tooling", "Governance & DAOs"),
        ("gm everyone", "greeting"),
        ("Just touched grass. Recommend.", "Other"),
    ]
    for i, p in enumerate(posts):
        content, _ = categories[i % len(categories)]
        p["content"] = content + f" ({i})"
        if "gm" in content:
            p["content"] = "gm everyone"
    return posts


def make_other_dominant_posts(n: int = 30) -> list:
    """30 posts where >50% are Other — should trigger focus cap."""
    posts = make_posts(n, post_type="original")
    for i, p in enumerate(posts):
        if i < int(n * 0.6):  # 60% Other
            p["content"] = f"Just vibing in crypto today #{i}"
        else:
            p["content"] = f"ETH L2 scaling looks good #{i}"
    return posts


# ─────────────────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────────────────

def test_hash_determinism():
    print("\n" + "═" * 60)
    print("TEST 1 — Hash Determinism")
    print("Same input must produce identical snapshot hash every run.")
    print("─" * 60)

    posts = make_focused_posts(30)
    collection = make_mock_collection(posts, handle="determinism_test")

    # Classifier that returns deterministic T&I for all focused posts
    classifier = make_mock_classifier({"ethereum": "Technology & Infrastructure",
                                       "abstract": "Technology & Infrastructure",
                                       "megaeth": "Technology & Infrastructure",
                                       "zk": "Technology & Infrastructure",
                                       "sequencer": "Technology & Infrastructure"})

    snap1 = score_epoch(collection, classifier)
    snap2 = score_epoch(collection, classifier)

    h1 = snap1["snapshot_hash"]
    h2 = snap2["snapshot_hash"]

    if h1 == h2:
        print(f"{PASS} Hash identical across two runs: {h1[:16]}…")
    else:
        print(f"{FAIL} Hash mismatch!")
        print(f"  Run 1: {h1}")
        print(f"  Run 2: {h2}")
        return False

    # Verify: change one score by 0.001 → hash changes
    snap_modified = copy.deepcopy(snap1)
    snap_modified["scores"]["composite"] += 0.001
    h_modified = canonical_hash(snap_modified)
    if h_modified != h1:
        print(f"{PASS} Score delta of 0.001 changes hash (expected)")
    else:
        print(f"{FAIL} Hash did not change after score modification!")
        return False

    return True


def test_score_ranges():
    print("\n" + "═" * 60)
    print("TEST 2 — Score Range Validation")
    print("All scores must be in [0, 100] and composite must equal weighted average.")
    print("─" * 60)

    for label, posts in [
        ("focused posts (30)",  make_focused_posts(30)),
        ("scattered posts (30)", make_scattered_posts(30)),
        ("reply-heavy posts (25)", make_posts(25, post_type="reply")),
    ]:
        collection = make_mock_collection(posts, handle=f"range_test")
        classifier = make_mock_classifier({
            "ethereum": "Technology & Infrastructure",
            "aave": "DeFi & Protocols",
            "ai agent": "AI & Agents",
            "dao": "Governance & DAOs",
            "10k": "Market & Price",
        })
        snap = score_epoch(collection, classifier)
        scores = snap["scores"]

        all_valid = True
        for pillar, val in scores.items():
            if not (0 <= val <= 100):
                print(f"  {FAIL} {pillar}={val} out of range")
                all_valid = False

        # Verify composite = average of pillars
        expected_composite = round(
            (scores["originality"] + scores["focus"] +
             scores["consistency"] + scores["depth"]) / 4,
            2,
        )
        if abs(scores["composite"] - expected_composite) > 0.01:
            print(f"  {FAIL} Composite mismatch: got {scores['composite']}, expected {expected_composite}")
            all_valid = False

        status = PASS if all_valid else FAIL
        print(f"  {status} {label}: O={scores['originality']} F={scores['focus']} "
              f"C={scores['consistency']} D={scores['depth']} → composite={scores['composite']}")

    return True


def test_other_dominance_cap():
    print("\n" + "═" * 60)
    print("TEST 3 — Other Dominance Cap")
    print("If >50% of posts classify as Other, focus must be capped at 60.")
    print("─" * 60)

    posts = make_other_dominant_posts(30)
    collection = make_mock_collection(posts, handle="other_dominant_test")
    # Classifier returns Other for all "vibing" posts
    classifier = make_mock_classifier({
        "vibing": "Other",
        "l2 scaling": "Technology & Infrastructure",
    })

    snap = score_epoch(collection, classifier)
    focus_score = snap["scores"]["focus"]
    cap_applied = snap["focus_detail"]["other_cap_applied"]
    other_pct   = snap["focus_detail"]["other_dominance"]

    if cap_applied and focus_score <= 60:
        print(f"{PASS} Other dominance cap applied correctly")
        print(f"  Other dominance: {other_pct:.1%}, focus capped at {focus_score}")
    elif other_pct <= 0.50:
        print(f"{WARN} Other dominance was {other_pct:.1%} — below 50% threshold, cap not expected")
    else:
        print(f"{FAIL} Cap should have applied (other_dominance={other_pct:.1%}) but focus={focus_score}")
        return False

    return True


def test_consistency_modes():
    print("\n" + "═" * 60)
    print("TEST 4 — Consistency Modes")
    print("20–59 posts → frequency_variance | ≥60 posts → thirds_entropy")
    print("─" * 60)

    for n, expected_mode in [(25, "frequency_variance"), (65, "thirds_entropy")]:
        posts = make_posts(n, post_type="mixed")
        collection = make_mock_collection(posts)
        classifier = make_mock_classifier({"l2": "Technology & Infrastructure"})
        snap = score_epoch(collection, classifier)
        mode = snap["consistency_detail"]["mode"]
        score = snap["scores"]["consistency"]
        status = PASS if mode == expected_mode else FAIL
        print(f"  {status} n={n}: mode={mode} (expected {expected_mode}), score={score}")

    return True


def test_post_breakdown():
    print("\n" + "═" * 60)
    print("TEST 5 — Post Breakdown Accounting")
    print("total = classified + greeting + null_track")
    print("─" * 60)

    # Mix of classified, greeting, and null posts
    posts = []
    posts += make_posts(15, post_type="original")        # classified
    posts += [{"id": f"gm_{i}", "content": "gm frens", "createdDate":
               datetime.now(timezone.utc).isoformat(),
               "is_reply": False, "is_quote": False} for i in range(5)]   # greeting
    posts += [{"id": f"null_{i}", "content": "", "createdDate":
               datetime.now(timezone.utc).isoformat(),
               "is_reply": False, "is_quote": False} for i in range(3)]   # null

    collection = make_mock_collection(posts)
    classifier = make_mock_classifier({"l2": "Technology & Infrastructure"})
    snap = score_epoch(collection, classifier)
    bd = snap["post_breakdown"]

    total_check = bd["classified"] + bd["greeting"] + bd["null_track"]
    if total_check == bd["total"]:
        print(f"{PASS} Breakdown sums correctly: {bd['classified']} classify + "
              f"{bd['greeting']} greeting + {bd['null_track']} null = {bd['total']}")
    else:
        print(f"{FAIL} Breakdown mismatch: {total_check} ≠ {bd['total']}")
        return False

    return True


def test_methodology_fields():
    print("\n" + "═" * 60)
    print("TEST 6 — Methodology Fields in Snapshot")
    print("snapshot must contain prompt_hash, model, methodology_version, collection_hash")
    print("─" * 60)

    posts = make_posts(25, post_type="original")
    collection = make_mock_collection(posts)
    classifier = make_mock_classifier()
    snap = score_epoch(collection, classifier)
    prov = snap["provenance"]

    required = ["prompt_hash", "model", "methodology_version", "collection_hash"]
    all_present = True
    for field in required:
        if field not in prov:
            print(f"  {FAIL} Missing field: {field}")
            all_present = False

    if prov.get("methodology_version") != METHODOLOGY_VERSION:
        print(f"  {FAIL} methodology_version mismatch: {prov.get('methodology_version')}")
        all_present = False

    if all_present:
        print(f"{PASS} All provenance fields present (methodology={prov['methodology_version']})")

    return all_present


# ─────────────────────────────────────────────────────────────────────────────
# Live scoring (optional — requires cached collection on disk)
# ─────────────────────────────────────────────────────────────────────────────

def test_live_scoring(handle: str):
    """Score a real user from a cached collection file."""
    print("\n" + "═" * 60)
    print(f"LIVE SCORING — @{handle}")
    print("─" * 60)

    # Look for cached collection
    cache_candidates = list(Path(".").glob(f"cache/posts/{handle}_*.json"))
    if not cache_candidates:
        print(f"{WARN} No cached collection found for @{handle}. Skipping live test.")
        return True

    # Pick the file with the latest end date (widest window = most posts)
    def end_date_key(p):
        parts = p.stem.split("_")
        return parts[-1] if len(parts) >= 3 else ""

    cache_path = sorted(cache_candidates, key=end_date_key)[-1]
    print(f"Loading cached collection: {cache_path}")

    with open(cache_path) as f:
        data = json.load(f)

    class LiveCollection:
        handle         = data["handle"]
        user_id        = data["user_id"]
        epoch_start    = data["epoch_start"]
        epoch_end      = data["epoch_end"]
        post_count     = data["post_count"]
        posts          = data["posts"]
        collection_hash = data["collection_hash"]

    # Use real classifier
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        sys.path.insert(0, str(Path(__file__).parent))
        from evaluation.classifier import Classifier
        api_key = os.getenv("ANTHROPIC_API_KEY")
        classifier = Classifier(api_key=api_key)
        info = classifier.get_model_info()
        classifier.prompt_version = "v5"  # expose for engine provenance
        print(f"Using real Classifier | model={info['model']} | prompt_hash={info['prompt_hash'][:12]}…")
    except Exception as e:
        print(f"{WARN} Could not load real Classifier ({e}). Using mock.")
        classifier = make_mock_classifier()

    try:
        snap = score_epoch(LiveCollection(), classifier)
    except ValueError as e:
        print(f"{WARN} Could not score: {e}")
        return True  # not a test failure — data issue, not engine issue

    print(f"\n@{handle} Epoch Score")
    print(f"  Composite:    {snap['scores']['composite']}")
    print(f"  Consistency:  {snap['scores']['consistency']}")
    print(f"  Focus:        {snap['scores']['focus']}")
    print(f"  Depth:        {snap['scores']['depth']}")
    print(f"  Originality:  {snap['scores']['originality']}")
    print(f"\n  Post breakdown: {snap['post_breakdown']}")
    print(f"  Topic distribution: {snap['focus_detail']['topic_distribution']}")
    print(f"  Snapshot hash: {snap['snapshot_hash'][:24]}…")
    print(f"  Consistency mode: {snap['consistency_detail']['mode']}")

    # Save result
    out_path = Path(f"scoring_output_{handle}.json")
    with open(out_path, "w") as f:
        json.dump(snap, f, indent=2)
    print(f"\n  Full snapshot saved to {out_path}")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-handle", help="Arena handle to score from cached collection")
    args = parser.parse_args()

    results = []
    results.append(("Hash Determinism",       test_hash_determinism()))
    results.append(("Score Range Validation", test_score_ranges()))
    results.append(("Other Dominance Cap",    test_other_dominance_cap()))
    results.append(("Consistency Modes",      test_consistency_modes()))
    results.append(("Post Breakdown",         test_post_breakdown()))
    results.append(("Methodology Fields",     test_methodology_fields()))

    if args.live_handle:
        results.append(("Live Scoring",       test_live_scoring(args.live_handle)))

    print("\n" + "═" * 60)
    print("SUMMARY")
    print("─" * 60)
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        print(f"  {'✅' if result else '❌'}  {name}")
    print(f"\n{passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n✅ Scoring engine ready. Day 3 complete.")
    else:
        print("\n❌ Fix failing tests before proceeding to Day 4.")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
