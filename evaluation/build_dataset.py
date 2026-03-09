"""
Tessera — Dataset Builder
Extracts posts from cached Arena JSON files for manual labelling.

Run this to generate the initial dataset.json template,
then manually add true_label and notes to each entry.

Usage:
    python evaluation/build_dataset.py

Output:
    evaluation/dataset_unlabelled.json  ← fill in true_label + notes
    evaluation/dataset.json             ← rename when done labelling
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

CACHE_DIR = Path("cache/posts")
EVAL_DIR = Path("evaluation")
OUTPUT_PATH = EVAL_DIR / "dataset_unlabelled.json"

# Target composition based on rubric coverage requirements
TARGET_COMPOSITION = {
    "sarcasm_ironic": 15,
    "very_short": 10,
    "quote_commentary": 10,
    "mixed_domain": 15,
    "personal_lifestyle": 10,
    "memecoin_culture": 10,
    "distributed_main_buckets": 30,
}


def load_all_cached_posts() -> list[dict]:
    """Load all posts from cached Arena JSON files."""
    all_posts = []
    cache_files = list(CACHE_DIR.glob("*.json"))

    if not cache_files:
        print(f"❌ No cached posts found in {CACHE_DIR}")
        print("Run test_ingestion.py first to fetch and cache posts.")
        sys.exit(1)

    for cache_file in cache_files:
        with open(cache_file, encoding="utf-8") as f:
            collection = json.load(f)
        posts = collection.get("posts", [])
        handle = collection.get("handle", "unknown")
        for post in posts:
            post["source_handle"] = handle
        all_posts.extend(posts)
        print(f"  Loaded {len(posts)} posts from {cache_file.name}")

    return all_posts


def build_dataset_template(posts: list[dict], target: int = 100) -> list[dict]:
    """
    Build a template dataset from cached posts.
    Filters to posts with meaningful content, deduplicates,
    and formats for manual labelling.
    """
    # Filter: skip empty content, skip very short (< 3 chars after strip)
    filtered = [
        p for p in posts
        if p.get("content") and len(p["content"].strip()) >= 3
    ]

    # Deduplicate by content
    seen = set()
    deduped = []
    for p in filtered:
        content_key = p["content"].strip()[:100]
        if content_key not in seen:
            seen.add(content_key)
            deduped.append(p)

    print(f"\nTotal posts available: {len(deduped)} (after dedup)")
    print(f"Selecting up to {target} for dataset\n")

    # Sort by length to get variety — mix short and long
    deduped.sort(key=lambda x: len(x.get("content", "")))

    # Take a spread across the length distribution
    selected = []
    step = max(1, len(deduped) // target)
    for i in range(0, min(len(deduped), len(deduped)), step):
        if len(selected) >= target:
            break
        selected.append(deduped[i])

    # Fill remaining if needed
    if len(selected) < target:
        remaining = [p for p in deduped if p not in selected]
        selected.extend(remaining[:target - len(selected)])

    # Format for manual labelling
    dataset = []
    for i, post in enumerate(selected[:target]):
        dataset.append({
            "id": f"post_{i+1:03d}",
            "text": post["content"].strip(),
            "source_handle": post.get("source_handle", "unknown"),
            "source_id": post.get("id", ""),
            "created_at": post.get("created_at", ""),
            "is_reply": post.get("is_reply", False),
            "is_quote": post.get("is_quote", False),
            "true_label": "",      # ← FILL THIS IN
            "notes": ""            # ← optional, add if useful
        })

    return dataset


def main():
    EVAL_DIR.mkdir(exist_ok=True)

    print("Loading cached posts...")
    posts = load_all_cached_posts()

    dataset = build_dataset_template(posts, target=100)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"✅ Dataset template written to {OUTPUT_PATH}")
    print(f"   {len(dataset)} posts ready for labelling\n")
    print("Next steps:")
    print("  1. Read RUBRIC.md in full before labelling")
    print("  2. Label all 100 posts in one sitting")
    print("  3. Fill in 'true_label' for each entry (must match ALLOWED_CATEGORIES exactly)")
    print("  4. Add 'notes' where helpful")
    print("  5. Rename to dataset.json when complete")
    print(f"\nAllowed labels:")
    from evaluation.classifier import ALLOWED_CATEGORIES
    for cat in ALLOWED_CATEGORIES:
        print(f"    \"{cat}\"")


if __name__ == "__main__":
    main()
