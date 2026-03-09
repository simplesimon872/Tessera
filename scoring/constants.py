"""
Tessera scoring constants — locked for v1.0.
Nothing in this file changes without a methodology version bump.
"""

import math

# ─── Taxonomy ────────────────────────────────────────────────────────────────

ALLOWED_CATEGORIES = [
    "Market & Price",
    "Technology & Infrastructure",
    "DeFi & Protocols",
    "AI & Agents",
    "Governance & DAOs",
    "Other",
    "Null",
]

# The 6 active buckets used for entropy calculation.
# Null is excluded from entropy — it has no topical signal.
ENTROPY_BUCKETS = [
    "Market & Price",
    "Technology & Infrastructure",
    "DeFi & Protocols",
    "AI & Agents",
    "Governance & DAOs",
    "Other",
]

# ─── Entropy ─────────────────────────────────────────────────────────────────

# Theoretical maximum entropy for a uniform distribution over 6 buckets.
# Hardcoded — never derived at runtime.
MAX_ENTROPY = math.log2(6)  # ≈ 2.585

# If Other classifications exceed this fraction of total posts,
# cap focus score at FOCUS_OTHER_CAP.
# Meme-heavy/lifestyle accounts would score as artificially hyper-focused
# due to collapsed entropy. Document in audit trail.
OTHER_DOMINANCE_THRESHOLD = 0.50
FOCUS_OTHER_CAP = 60.0

# ─── Thresholds ──────────────────────────────────────────────────────────────

MIN_POST_THRESHOLD = 5           # Below this → reject entirely
CONSISTENCY_FULL_MODE_THRESHOLD = 60  # ≥ this → thirds-based entropy mode
                                       # 20–59 → frequency variance mode

# ─── Methodology ─────────────────────────────────────────────────────────────

METHODOLOGY_VERSION = "v1.0"
COMPOSITE_WEIGHTS = {
    "consistency": 0.25,
    "focus":       0.25,
    "depth":       0.25,
    "originality": 0.25,
}
