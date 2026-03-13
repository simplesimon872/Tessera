"""
Tessera — Topic Classifier
Deterministic LLM wrapper around Claude for post classification.

v2: True batch classification — sends up to BATCH_SIZE posts in a single
API call and parses the array response. Reduces LLM calls from N posts
to ceil(N / BATCH_SIZE) calls.

Usage:
    from evaluation.classifier import Classifier
    clf = Classifier(api_key)

    # Single post
    result = clf.classify("Ethereum L2 fees dropping fast.")
    # {"category": "Technology & Infrastructure"}

    # Batch (much faster)
    results = clf.classify_batch(posts)  # posts = list of dicts with id + content
"""

import json
import hashlib
import logging
from pathlib import Path
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Rate limiting — only needed on free tier (5 RPM)
# Paid tier has no per-minute cap, set FREE_TIER = False
# ─────────────────────────────────────────────────────────────
import time as _time

FREE_TIER = False          # set True only if on free Anthropic tier
FREE_TIER_DELAY = 13       # seconds between requests on free tier
BATCH_SIZE = 25            # posts per LLM call — tune down if hitting token limits

class _RateLimiter:
    def __init__(self):
        self._last_call = 0.0

    def wait(self):
        if not FREE_TIER:
            return
        elapsed = _time.time() - self._last_call
        if elapsed < FREE_TIER_DELAY:
            wait = FREE_TIER_DELAY - elapsed
            logger.info(f"Free tier rate limit — waiting {wait:.1f}s")
            _time.sleep(wait)
        self._last_call = _time.time()

_rate_limiter = _RateLimiter()

# ─────────────────────────────────────────────────────────────
# Locked taxonomy — do not modify without methodology version bump
# ─────────────────────────────────────────────────────────────
ALLOWED_CATEGORIES = [
    "Market & Price",
    "Technology & Infrastructure",
    "DeFi & Protocols",
    "AI & Agents",
    "Governance & DAOs",
    "Other",
    "Null",
]

ALLOWED_CATEGORIES_SET = set(ALLOWED_CATEGORIES)

MODEL       = "claude-haiku-4-5"
TEMPERATURE = 0          # non-negotiable for determinism
MAX_TOKENS  = 50         # single post — category label only
BATCH_MAX_TOKENS = 2048  # batch response — array of N labels
MAX_RETRIES = 2


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent / "prompt_v5.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}"
        )
    return prompt_path.read_text(encoding="utf-8").strip()


def compute_prompt_hash(prompt_text: str) -> str:
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


class Classifier:
    """
    Deterministic topic classifier.
    Same input always produces same output.
    Null is a valid classification, not an error.
    """

    def __init__(self, api_key: str, log_raw: bool = True):
        self.client = Anthropic(api_key=api_key)
        self.prompt = _load_prompt()
        self.prompt_hash = compute_prompt_hash(self.prompt)
        self.model = MODEL
        self.prompt_version = "v5"
        self.log_raw = log_raw
        self._raw_log_path = Path("evaluation/raw_outputs")
        if log_raw:
            self._raw_log_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Classifier initialised | prompt_hash={self.prompt_hash[:12]}... | "
            f"model={MODEL} | batch_size={BATCH_SIZE} | free_tier={FREE_TIER}"
        )

    # ── Single post ───────────────────────────────────────────────────────────

    def classify(self, text: str) -> dict:
        """
        Classify a single post. Returns {"category": "<label>"}.
        Never raises — returns {"category": "Null"} on failure.
        """
        if not text or len(text.split()) < 2:
            return {"category": "Null"}

        full_prompt = f"{self.prompt}\n\nPost:\n{text}"

        for attempt in range(MAX_RETRIES + 1):
            try:
                _rate_limiter.wait()
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                raw = response.content[0].text.strip()
                if self.log_raw:
                    self._log_raw(text, raw, attempt)
                result = self._parse_single(raw)
                if result is not None:
                    return result
                logger.warning(f"Invalid schema on attempt {attempt + 1}: {raw[:80]}")
            except Exception as e:
                logger.error(f"API error on attempt {attempt + 1}: {e}")

        logger.warning("Classification failed after retries, returning Null")
        return {"category": "Null"}

    # ── Batch classification ──────────────────────────────────────────────────

    def classify_batch(self, posts: list[dict]) -> list[dict]:
        """
        Classify a list of post dicts using batched LLM calls.

        Sends up to BATCH_SIZE posts per API call instead of one call
        per post. For 300 posts at BATCH_SIZE=25, this is 12 LLM calls
        instead of 300.

        Each post dict must have 'id' and 'content'.
        Returns the input list with 'category' added to each dict.
        """
        if not posts:
            return []

        # Split into batches
        batches = [
            posts[i:i + BATCH_SIZE]
            for i in range(0, len(posts), BATCH_SIZE)
        ]

        logger.info(
            f"Classifying {len(posts)} posts in {len(batches)} batches "
            f"of up to {BATCH_SIZE} (was {len(posts)} individual calls)"
        )

        results = []
        for batch_num, batch in enumerate(batches):
            logger.info(f"  Batch {batch_num + 1}/{len(batches)} — {len(batch)} posts")
            classified = self._classify_batch_llm(batch)
            results.extend(classified)

        logger.info(f"Batch classification complete — {len(results)} posts classified")
        return results

    def _classify_batch_llm(self, batch: list[dict]) -> list[dict]:
        """
        Send one batch of posts to the LLM. Returns posts with category added.
        Falls back to individual classification if batch call fails.
        """
        # Build numbered post list for the prompt
        numbered = ""
        for i, post in enumerate(batch):
            content = post.get("content", "").replace("\n", " ").strip()
            numbered += f"{i + 1}. {content}\n"

        batch_prompt = (
            f"{self.prompt}\n\n"
            f"Classify each of the following {len(batch)} posts.\n"
            f"Return ONLY a JSON array with one object per post in order.\n"
            f"Each object must have exactly: {{\"n\": <number>, \"category\": \"<label>\"}}\n"
            f"No other text. No markdown. No explanation.\n\n"
            f"Posts:\n{numbered}"
        )

        for attempt in range(MAX_RETRIES + 1):
            try:
                _rate_limiter.wait()
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=BATCH_MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[{"role": "user", "content": batch_prompt}]
                )
                raw = response.content[0].text.strip()
                parsed = self._parse_batch_response(raw, len(batch))

                if parsed is not None:
                    # Merge categories back into post dicts
                    result = []
                    for i, post in enumerate(batch):
                        result.append({
                            **post,
                            "category": parsed[i],
                        })
                    return result

                logger.warning(
                    f"Batch parse failed on attempt {attempt + 1}, "
                    f"raw[:200]={raw[:200]}"
                )

            except Exception as e:
                logger.error(f"Batch API error on attempt {attempt + 1}: {e}")

        # Batch failed — fall back to individual classification
        logger.warning(
            f"Batch classification failed after {MAX_RETRIES + 1} attempts — "
            f"falling back to individual classification for {len(batch)} posts"
        )
        result = []
        for post in batch:
            cat = self.classify(post.get("content", ""))
            result.append({**post, "category": cat["category"]})
        return result

    def _parse_batch_response(self, raw: str, expected_count: int) -> list[str] | None:
        """
        Parse batch LLM response into a list of category strings.
        Returns None if response is malformed.
        """
        cleaned = raw.strip()

        # Strip markdown fences
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, list):
            return None

        if len(parsed) != expected_count:
            logger.warning(
                f"Batch response length mismatch: expected {expected_count}, "
                f"got {len(parsed)}"
            )
            return None

        categories = []
        for item in parsed:
            if not isinstance(item, dict):
                return None
            cat = item.get("category")
            if cat not in ALLOWED_CATEGORIES_SET:
                # Invalid category — substitute Null rather than failing entire batch
                logger.warning(f"Unknown category in batch response: {cat!r} — using Null")
                cat = "Null"
            categories.append(cat)

        return categories

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_single(self, raw: str) -> dict | None:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        category = parsed.get("category")
        if category not in ALLOWED_CATEGORIES_SET:
            return None
        return {"category": category}

    def _log_raw(self, text: str, raw: str, attempt: int):
        import time
        log_entry = {
            "timestamp": time.time(),
            "text_preview": text[:100],
            "raw_response": raw,
            "attempt": attempt,
            "prompt_hash": self.prompt_hash,
        }
        log_file = self._raw_log_path / "raw_outputs.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_model_info(self) -> dict:
        return {
            "model": MODEL,
            "temperature": TEMPERATURE,
            "prompt_hash": self.prompt_hash,
            "taxonomy_version": "v1.0",
            "allowed_categories": ALLOWED_CATEGORIES,
        }


class _RateLimiter:
    def __init__(self):
        self._last_call = 0.0

    def wait(self):
        if not FREE_TIER:
            return
        elapsed = _time.time() - self._last_call
        if elapsed < FREE_TIER_DELAY:
            wait = FREE_TIER_DELAY - elapsed
            logger.info(f"Free tier rate limit — waiting {wait:.1f}s")
            _time.sleep(wait)
        self._last_call = _time.time()

_rate_limiter = _RateLimiter()

# ─────────────────────────────────────────────────────────────
# Locked taxonomy — do not modify without methodology version bump
# ─────────────────────────────────────────────────────────────
ALLOWED_CATEGORIES = [
    "Market & Price",
    "Technology & Infrastructure",
    "DeFi & Protocols",
    "AI & Agents",
    "Governance & DAOs",
    "Other",
    "Null",
]

ALLOWED_CATEGORIES_SET = set(ALLOWED_CATEGORIES)

MODEL = "claude-haiku-4-5"
TEMPERATURE = 0          # non-negotiable
MAX_TOKENS = 50          # category label only — no room for rambling
MAX_RETRIES = 2          # retry only on invalid JSON schema, not on Null


def _load_prompt() -> str:
    """
    Load prompt from file. Never construct at runtime.
    The prompt is a versioned artifact, not a string.
    """
    prompt_path = Path(__file__).parent / "prompt_v5.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}\n"
            "Create evaluation/prompt_v1.txt before running the classifier."
        )
    return prompt_path.read_text(encoding="utf-8").strip()


def compute_prompt_hash(prompt_text: str) -> str:
    """SHA-256 of the prompt text. Store this with every baseline."""
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


class Classifier:
    """
    Deterministic topic classifier.
    Same input always produces same output.
    Null is a valid classification, not an error.
    """

    def __init__(self, api_key: str, log_raw: bool = True):
        self.client = Anthropic(api_key=api_key)
        self.prompt = _load_prompt()
        self.prompt_hash = compute_prompt_hash(self.prompt)
        self.model = MODEL           # expose for scoring engine provenance
        self.prompt_version = "v5"  # expose for scoring engine provenance
        self.log_raw = log_raw
        self._raw_log_path = Path("evaluation/raw_outputs")
        if log_raw:
            self._raw_log_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Classifier initialised | prompt_hash={self.prompt_hash[:12]}... | model={MODEL}")

    def classify(self, text: str) -> dict:
        """
        Classify a single post.

        Returns: {"category": "<exact string from ALLOWED_CATEGORIES>"}

        Never raises on bad LLM output — returns {"category": "Null"} instead.
        Only retries on invalid JSON schema (max MAX_RETRIES times).
        """
        if not text or len(text.split()) < 2:
            return {"category": "Null"}

        full_prompt = f"{self.prompt}\n\nPost:\n{text}"

        for attempt in range(MAX_RETRIES + 1):
            try:
                _rate_limiter.wait()
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[{"role": "user", "content": full_prompt}]
                )

                raw = response.content[0].text.strip()

                # Log raw output before parsing
                if self.log_raw:
                    self._log_raw(text, raw, attempt)

                result = self._parse_and_validate(raw)
                if result is not None:
                    return result

                logger.warning(f"Invalid schema on attempt {attempt + 1}: {raw[:80]}")

            except Exception as e:
                logger.error(f"API error on attempt {attempt + 1}: {e}")

        # All retries exhausted — return Null
        logger.warning(f"Classification failed after {MAX_RETRIES + 1} attempts, returning Null")
        return {"category": "Null"}

    def _parse_and_validate(self, raw: str) -> dict | None:
        """
        Parse JSON and validate category is in allowed list.
        Returns None if invalid — caller handles retry logic.
        """
        # Strip markdown code fences if model wraps response (e.g. ```json ... ```)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None

        category = parsed.get("category")
        if category not in ALLOWED_CATEGORIES_SET:
            return None

        # Return only the category — no extra fields
        return {"category": category}

    def _log_raw(self, text: str, raw: str, attempt: int):
        """Log raw API response to disk for drift analysis."""
        import time
        log_entry = {
            "timestamp": time.time(),
            "text_preview": text[:100],
            "raw_response": raw,
            "attempt": attempt,
            "prompt_hash": self.prompt_hash,
        }
        log_file = self._raw_log_path / "raw_outputs.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def classify_batch(self, posts: list[dict]) -> list[dict]:
        """
        Classify a list of post dicts.
        Each dict must have an 'id' and 'content' field.
        Returns list with classification added.
        """
        results = []
        for i, post in enumerate(posts):
            text = post.get("content", "")
            result = self.classify(text)
            results.append({
                **post,
                "category": result["category"],
            })
            if (i + 1) % 10 == 0:
                logger.info(f"Classified {i + 1}/{len(posts)} posts")
        return results

    def get_model_info(self) -> dict:
        """Return classifier metadata for storage with baseline."""
        return {
            "model": MODEL,
            "temperature": TEMPERATURE,
            "prompt_hash": self.prompt_hash,
            "taxonomy_version": "v1.0",
            "allowed_categories": ALLOWED_CATEGORIES,
        }
