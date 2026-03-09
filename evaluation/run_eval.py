"""
Tessera — Evaluation Framework
Day 2: Baseline generation, determinism testing, and drift detection.

Run from the tessera/ project root:
    python evaluation/run_eval.py --mode determinism
    python evaluation/run_eval.py --mode baseline
    python evaluation/run_eval.py --mode drift

Requires:
    - ANTHROPIC_API_KEY in .env
    - evaluation/dataset.json (labelled posts)
    - evaluation/prompt_v1.txt (frozen prompt)
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from evaluation.classifier import Classifier, ALLOWED_CATEGORIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.json"
BASELINE_PATH = EVAL_DIR / "baseline_results.json"


# ─────────────────────────────────────────────────────────────
# Determinism Test
# ─────────────────────────────────────────────────────────────

DETERMINISM_TEST_POSTS = [
    {
        "id": "det_sarcasm",
        "text": "Oh sure, another 'revolutionary' L2 that's definitely not just a fork. Very impressive stuff.",
        "description": "Sarcasm — should classify consistently despite ironic tone"
    },
    {
        "id": "det_short",
        "text": "gm frens",
        "description": "Very short post — should return Null consistently"
    },
    {
        "id": "det_meme",
        "text": "DOGE SEASON IS HERE WE ARE ALL GONNA MAKE IT 🚀🚀🚀",
        "description": "Meme/culture post — should return Other consistently"
    },
    {
        "id": "det_mixed",
        "text": "The Aave governance proposal to adjust WBTC LTV looks bullish for price honestly, yield farmers will rotate hard",
        "description": "Mixed domain (DeFi + Price) — should classify consistently to one category"
    },
]


def run_determinism_test(classifier: Classifier, runs: int = 10) -> bool:
    """
    Run each test post N times and verify identical output every time.
    Returns True if all tests pass, False if any non-determinism detected.
    """
    print("\n" + "═" * 60)
    print("DETERMINISM TEST")
    print("═" * 60)
    print(f"Running {runs} classifications per post on {len(DETERMINISM_TEST_POSTS)} test posts\n")

    all_passed = True

    for post in DETERMINISM_TEST_POSTS:
        print(f"Testing: {post['description']}")
        print(f"Text: \"{post['text'][:80]}\"")

        results = []
        for i in range(runs):
            print(f"  Run {i+1}/{runs}...", end=" ", flush=True)
            result = classifier.classify(post["text"])
            results.append(result["category"])
            print(result["category"])

        unique = set(results)
        passed = len(unique) == 1

        if passed:
            print(f"✅ PASS — All {runs} runs returned: \"{results[0]}\"\n")
        else:
            print(f"❌ FAIL — Non-deterministic output detected!")
            print(f"   Got {len(unique)} different results: {unique}")
            print(f"   Distribution: {Counter(results)}\n")
            all_passed = False

    if all_passed:
        print("✅ All determinism tests passed. Safe to proceed.\n")
    else:
        print("❌ Determinism tests FAILED. Fix prompt before proceeding.\n")

    return all_passed


# ─────────────────────────────────────────────────────────────
# Baseline Generation
# ─────────────────────────────────────────────────────────────

def run_baseline(classifier: Classifier) -> dict:
    """
    Run classifier against the full frozen dataset.
    Compute accuracy, null rate, category distribution, and confusion matrix.
    Store as baseline_results.json.
    """
    if not DATASET_PATH.exists():
        print(f"❌ Dataset not found at {DATASET_PATH}")
        print("Create evaluation/dataset.json before running baseline.")
        sys.exit(1)

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    print("\n" + "═" * 60)
    print(f"BASELINE EVALUATION — {len(dataset)} posts")
    print("═" * 60)

    correct = 0
    null_count = 0
    predicted_labels = []
    true_labels = []
    confusion = {}

    for i, entry in enumerate(dataset):
        post_id = entry["id"]
        text = entry["text"]
        true_label = entry["true_label"]

        result = classifier.classify(text)
        pred_label = result["category"]

        predicted_labels.append(pred_label)
        true_labels.append(true_label)

        if pred_label == true_label:
            correct += 1
        if pred_label == "Null":
            null_count += 1

        # Build confusion matrix
        if true_label not in confusion:
            confusion[true_label] = {}
        confusion[true_label][pred_label] = confusion[true_label].get(pred_label, 0) + 1

        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{len(dataset)} posts classified")

    accuracy = round(correct / len(dataset), 4)
    null_rate = round(null_count / len(dataset), 4)
    category_distribution = dict(Counter(predicted_labels))

    # Ensure all categories present in distribution (even if zero)
    for cat in ALLOWED_CATEGORIES:
        if cat not in category_distribution:
            category_distribution[cat] = 0

    model_info = classifier.get_model_info()

    baseline = {
        "accuracy": accuracy,
        "null_rate": null_rate,
        "correct": correct,
        "total": len(dataset),
        "category_distribution": category_distribution,
        "confusion_matrix": confusion,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_hash": model_info["prompt_hash"],
        "prompt_version": "v5",
        "model": model_info["model"],
        "temperature": model_info["temperature"],
        "taxonomy_version": model_info["taxonomy_version"],
    }

    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    print(f"\n{'─' * 60}")
    print(f"BASELINE RESULTS")
    print(f"{'─' * 60}")
    print(f"Accuracy:     {accuracy:.1%}  ({correct}/{len(dataset)} correct)")
    print(f"Null rate:    {null_rate:.1%}  ({null_count} posts)")
    print(f"Prompt hash:  {model_info['prompt_hash'][:24]}...")
    print(f"\nCategory distribution:")
    for cat, count in sorted(category_distribution.items(), key=lambda x: -x[1]):
        print(f"  {cat:<35} {count:>4} posts")
    print(f"\nBaseline saved to {BASELINE_PATH}")

    return baseline


# ─────────────────────────────────────────────────────────────
# Drift Detection
# ─────────────────────────────────────────────────────────────

def run_drift_check(classifier: Classifier) -> bool:
    """
    Compare current classifier output against stored baseline.
    Fails if classification change exceeds 5%.
    Call this every time the prompt is modified.
    """
    if not BASELINE_PATH.exists():
        print("❌ No baseline found. Run --mode baseline first.")
        sys.exit(1)
    if not DATASET_PATH.exists():
        print("❌ Dataset not found.")
        sys.exit(1)

    with open(BASELINE_PATH, encoding="utf-8") as f:
        baseline = json.load(f)
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    print("\n" + "═" * 60)
    print("DRIFT DETECTION")
    print("═" * 60)

    # Check prompt hash
    current_hash = classifier.prompt_hash
    baseline_hash = baseline["prompt_hash"]
    if current_hash != baseline_hash:
        print(f"⚠️  Prompt has changed!")
        print(f"   Baseline hash: {baseline_hash[:24]}...")
        print(f"   Current hash:  {current_hash[:24]}...")
    else:
        print(f"✅ Prompt unchanged (hash match)")

    # Re-classify dataset
    print(f"\nRe-classifying {len(dataset)} posts...")
    changes = 0
    changed_posts = []

    for entry in dataset:
        result = classifier.classify(entry["text"])
        current_label = result["category"]
        baseline_label = entry.get("baseline_label")

        if baseline_label and current_label != baseline_label:
            changes += 1
            changed_posts.append({
                "id": entry["id"],
                "text": entry["text"][:80],
                "baseline": baseline_label,
                "current": current_label
            })

    change_rate = changes / len(dataset)
    threshold = 0.05  # 5%

    print(f"\nClassification changes: {changes}/{len(dataset)} ({change_rate:.1%})")

    if change_rate > threshold:
        print(f"❌ DRIFT DETECTED — {change_rate:.1%} exceeds {threshold:.0%} threshold")
        print(f"\nFirst 5 changed posts:")
        for p in changed_posts[:5]:
            print(f"  [{p['id']}] \"{p['text']}\"")
            print(f"    Baseline: {p['baseline']}  →  Current: {p['current']}")
        print("\nReject this prompt change.")
        return False
    else:
        print(f"✅ PASS — {change_rate:.1%} change rate is within {threshold:.0%} threshold")
        return True


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Tessera evaluation framework")
    parser.add_argument(
        "--mode",
        choices=["determinism", "baseline", "drift"],
        required=True,
        help="determinism: test consistency | baseline: generate baseline | drift: check for drift"
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        sys.exit(1)

    classifier = Classifier(api_key=api_key, log_raw=True)
    print(f"Classifier ready | model={classifier.get_model_info()['model']} | "
          f"prompt_hash={classifier.prompt_hash[:12]}...")

    if args.mode == "determinism":
        passed = run_determinism_test(classifier)
        sys.exit(0 if passed else 1)

    elif args.mode == "baseline":
        passed = run_determinism_test(classifier, runs=5)
        if not passed:
            print("❌ Fix determinism before generating baseline.")
            sys.exit(1)
        run_baseline(classifier)

    elif args.mode == "drift":
        passed = run_drift_check(classifier)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
