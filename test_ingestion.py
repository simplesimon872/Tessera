"""
Test the ingestion pipeline against real Arena accounts.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import (
    ArenaClient,
    fetch_posts_for_epoch,
    post_stats,
    current_epoch_window,
    InsufficientPostsError,
)

# Configure logging — set to DEBUG to see every API call
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)

# ─────────────────────────────────────────────
# Test handles — replace with real Arena handles
# Pick 3 accounts with different posting styles:
#   - one heavy poster (60+ posts/week)
#   - one moderate poster (25-60 posts/week)
#   - one to test the rejection case (<25 posts)
# ─────────────────────────────────────────────
TEST_HANDLES = [
    "0xMaximusDM",   # your own account — good starting point
    "simplesimon872",
    "realwarrior313",
    "jasonmdesimone",
    "monteegeez",
    "toneweb3",
    "collincusce",
    "thedazzlenovak",
    "pappiabraham",
    "kingzli",
    "cryptopepper3",
    "McVersePilot",
    "tfoacount",
    "spicy_rich",
    "honeybear9000",
    "choppersats",
    "benafflegg",
    "kamran_masood90",
    "benbirtrolum",
    "LilliVibe",
    "vucacavu",
    "alin_reaper05",
    "nochillavax",
    "masudkhan03",
    "rajgm185523",
    "dj_rustbucket",
    "alifsk95",
    "vaijan2258",
    "mk4433648421365",
    "Ace0fTrades",
    "shamwise8",
    "ncconnois",
    "loft_40",
    "lyagamii_",
    "JiriOhem",
    "The_Grinkett",
    "Blake4Liberty",
    "OneWingedShadow",
    "gratefulrecover",
    "LITS_BIZ",
    "briischamp",
    "KINGETH22",
    "InterestedBrain",
    "VucaCavu",
    "rhynelf",
    "jacobsi58989463",
    "702Philip",
    "William24_20_18",
    "MykePayn3",
    "jasonmdesimone"
]


def test_handle(client: ArenaClient, handle: str):
    print(f"\n{'─' * 60}")
    print(f"Testing @{handle}")
    print('─' * 60)

    epoch_start, epoch_end = current_epoch_window()
    print(f"Epoch window: {epoch_start.date()} → {epoch_end.date()}")

    try:
        collection = fetch_posts_for_epoch(
            handle=handle,
            client=client,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            cache_dir=Path("cache/posts")
        )

        stats = post_stats(collection)

        print(f"\n✅ Success")
        print(f"   User ID:      {collection.user_id}")
        print(f"   Posts:        {collection.post_count}")
        print(f"   Originals:    {stats['originals']} ({stats['originality_ratio']*100:.0f}%)")
        print(f"   Replies:      {stats['replies']} ({stats['reply_ratio']*100:.0f}%)")
        print(f"   Quotes:       {stats['quotes']}")
        print(f"   Hash:         {collection.collection_hash[:24]}...")
        print(f"\n   Sample post:")
        if collection.posts:
            sample = collection.posts[0]
            print(f"   [{sample['created_at'][:10]}] "
                  f"{'[reply] ' if sample['is_reply'] else ''}"
                  f"{'[quote] ' if sample['is_quote'] else ''}"
                  f"{sample['content'][:120]}...")

    except InsufficientPostsError as e:
        print(f"\n⚠️  Rejected: {e}")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        raise


def main():
    api_key = os.getenv("ARENA_API_KEY")
    if not api_key:
        print("❌ ARENA_API_KEY not found in .env")
        sys.exit(1)

    client = ArenaClient(api_key)

    # Confirm connection first
    print("Confirming API connection...")
    me = client.get_me()
    print(f"✅ Connected as: {me['userName']} (@{me['handle']})")
    print(f"   Agent ID: {me['id']}")

    # Run tests
    for handle in TEST_HANDLES:
        test_handle(client, handle)

    print(f"\n{'─' * 60}")
    print("Ingestion test complete.")
    print(f"Rate usage: {client.rate_limiter.requests_this_hour} requests this hour")


if __name__ == "__main__":
    main()
