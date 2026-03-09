"""
Arena API client for Tessera ingestion layer.
Handles auth, rate limiting, and all API calls.
"""

import time
import logging
from datetime import datetime, timezone
from collections import deque
import requests

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Enforces Arena API rate limits:
    - 100 GET requests per minute
    - 1,000 total requests per hour (global)
    Uses a sliding window approach.
    """

    def __init__(self):
        self.minute_window = deque()   # timestamps of requests in last 60s
        self.hour_window = deque()     # timestamps of requests in last 3600s
        self.MINUTE_LIMIT = 95         # stay under 100, buffer of 5
        self.HOUR_LIMIT = 950          # stay under 1000, buffer of 50

    def wait_if_needed(self):
        now = time.time()

        # Purge expired timestamps
        while self.minute_window and self.minute_window[0] < now - 60:
            self.minute_window.popleft()
        while self.hour_window and self.hour_window[0] < now - 3600:
            self.hour_window.popleft()

        # Check minute limit
        if len(self.minute_window) >= self.MINUTE_LIMIT:
            wait = 60 - (now - self.minute_window[0]) + 0.5
            logger.warning(f"Rate limit: minute window full, waiting {wait:.1f}s")
            time.sleep(wait)
            now = time.time()

        # Check hour limit
        if len(self.hour_window) >= self.HOUR_LIMIT:
            wait = 3600 - (now - self.hour_window[0]) + 1
            logger.warning(f"Rate limit: hour window full, waiting {wait:.1f}s")
            time.sleep(wait)
            now = time.time()

        self.minute_window.append(now)
        self.hour_window.append(now)

    @property
    def requests_this_minute(self):
        now = time.time()
        return sum(1 for t in self.minute_window if t > now - 60)

    @property
    def requests_this_hour(self):
        now = time.time()
        return sum(1 for t in self.hour_window if t > now - 3600)


class ArenaClient:
    """
    Arena Agents API client.
    All methods return parsed JSON or raise on error.
    """

    BASE_URL = "https://api.starsarena.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://starsarena.com",
        "Referer": "https://starsarena.com/"
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            **self.HEADERS,
            "X-API-Key": api_key
        })

    def _get(self, path: str, params: dict = None) -> dict:
        self.rate_limiter.wait_if_needed()
        url = f"{self.BASE_URL}{path}"
        logger.debug(f"GET {path} | params={params} | "
                     f"min={self.rate_limiter.requests_this_minute} "
                     f"hr={self.rate_limiter.requests_this_hour}")
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    # -------------------------------------------------------------------------
    # User lookups
    # -------------------------------------------------------------------------

    def get_user_by_handle(self, handle: str) -> dict:
        """
        Resolve a handle to a full user object (including userId UUID).
        This is always step 1 before fetching posts.
        """
        data = self._get("/agents/user/handle", params={"handle": handle})
        return data["user"]

    def get_user_by_id(self, user_id: str) -> dict:
        data = self._get("/agents/user/id", params={"userId": user_id})
        return data["user"]

    def get_me(self) -> dict:
        data = self._get("/agents/user/me")
        return data["user"]

    # -------------------------------------------------------------------------
    # Post fetching
    # -------------------------------------------------------------------------

    def fetch_epoch_posts(
        self,
        user_id: str,
        epoch_start: datetime,
        epoch_end: datetime
    ) -> list[dict]:
        """
        Fetch all posts by a user within the epoch window.

        Paginates through feed/user and stops as soon as a post's
        createdAt falls before epoch_start. Does not pull full history.

        Returns a list of cleaned post dicts.
        """
        posts = []
        page = 1
        page_size = 20
        done = False

        epoch_start_str = epoch_start.isoformat()
        epoch_end_str = epoch_end.isoformat()

        logger.info(f"Fetching posts for userId={user_id} "
                    f"window={epoch_start.date()} → {epoch_end.date()}")

        while not done:
            data = self._get(
                "/agents/threads/feed/user",
                params={"userId": user_id, "page": page, "pageSize": page_size}
            )

            threads = data.get("threads", [])

            if not threads:
                break

            for thread in threads:
                created = thread.get("createdAt", "")

                # Hit the boundary — everything older is outside the window
                if created < epoch_start_str:
                    done = True
                    break

                # Within the epoch window
                if created <= epoch_end_str:
                    posts.append(self._clean_post(thread))

            # Check pagination
            pagination = data.get("pagination", {})
            if not pagination.get("hasNextPage", False):
                break

            page += 1

        logger.info(f"Fetched {len(posts)} posts in epoch window")
        return posts

    def _clean_post(self, thread: dict) -> dict:
        """
        Extract and normalise only the fields we need.
        Strips HTML from content before storage.
        """
        return {
            "id": thread.get("id"),
            "content": self._strip_html(thread.get("content", "")),
            "content_raw": thread.get("content", ""),   # keep original too
            "created_at": thread.get("createdAt"),
            "user_id": thread.get("userId"),
            "is_reply": thread.get("threadId") is not None,
            "parent_thread_id": thread.get("threadId"),
            "is_quote": thread.get("quotedThreadId") is not None,
            "quoted_thread_id": thread.get("quotedThreadId"),
        }

    @staticmethod
    def _strip_html(html: str) -> str:
        """Remove HTML tags from post content before LLM processing."""
        import re
        # Replace <br> tags with spaces
        text = re.sub(r"<br\s*/?>", " ", html, flags=re.IGNORECASE)
        # Remove all other tags
        text = re.sub(r"<[^>]+>", "", text)
        # Collapse whitespace
        text = " ".join(text.split())
        return text.strip()

    # -------------------------------------------------------------------------
    # Notifications + thread fetch (bot use — agents API)
    # -------------------------------------------------------------------------

    def get_notifications(self, page_size: int = 100) -> list[dict]:
        """
        Fetch latest notifications via /agents/notifications.
        Structure confirmed: id, createdOn, title, text, link, type.
        Mention notifications have title ending "mentioned you in a thread"
        and link ending in the 36-char thread UUID.
        """
        data = self._get(
            "/agents/notifications",
            params={"page": 1, "pageSize": page_size}
        )
        return data.get("notifications", [])

    def get_thread(self, thread_id: str) -> dict:
        """
        Fetch full thread by ID via agents endpoint.
        """
        data = self._get("/agents/threads", params={"threadId": thread_id})
        return data.get("thread", {})

    # -------------------------------------------------------------------------
    # Posting (bot use)
    # -------------------------------------------------------------------------

    def _post(self, path: str, body: dict) -> dict:
        self.rate_limiter.wait_if_needed()
        url = f"{self.BASE_URL}{path}"
        response = self.session.post(url, json=body)
        response.raise_for_status()
        return response.json()

    def create_post(self, content: str) -> dict:
        """
        Create a new top-level post via agents endpoint.
        Always a new thread — never a reply.
        Returns full thread dict from response.
        """
        data = self._post("/agents/threads", {
            "content":       content,
            "files":         [],
            "privacyType":   0,
            "hasURLPreview": False,
        })
        return data.get("thread", {})
