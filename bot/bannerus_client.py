"""
bot/bannerus_client.py — Arena API client for the @bannerusmaximus account.

Uses the standard Arena REST API (api.arena.social) with Bearer token auth.
This is separate from ArenaClient which uses the agents API (api.starsarena.com).

Handles:
    - Notifications polling
    - Thread fetching
    - Post creation
    - User lookup by handle

Requires in .env:
    BANNERUS_API_KEY — Bearer token for the bannerusmaximus account
                       (the long string shown in Arena API docs curl examples)
"""

import logging
import time
from collections import deque

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.arena.social"

MENTION_SUFFIX = "mentioned you in a thread"


class BannerusClient:
    """
    Thin client for the bannerusmaximus account using the standard Arena API.
    Bearer token auth — same as shown in Arena API docs.
    """

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Accept":        "application/json",
            "Content-Type":  "application/json",
            "User-Agent":    "Mozilla/5.0",
        })
        self._minute_window = deque()
        self.MINUTE_LIMIT = 8   # api docs show x-ratelimit-limit: 10, stay under

    def _throttle(self):
        """Simple per-minute rate limiter."""
        now = time.time()
        while self._minute_window and self._minute_window[0] < now - 60:
            self._minute_window.popleft()
        if len(self._minute_window) >= self.MINUTE_LIMIT:
            wait = 60 - (now - self._minute_window[0]) + 0.5
            logger.warning(f"Rate limit — waiting {wait:.1f}s")
            time.sleep(wait)
        self._minute_window.append(time.time())

    def _get(self, path: str, params: dict = None) -> dict:
        self._throttle()
        url = f"{BASE_URL}{path}"
        logger.debug(f"GET {path} params={params}")
        r = self.session.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def _post_req(self, path: str, body: dict) -> dict:
        self._throttle()
        url = f"{BASE_URL}{path}"
        logger.debug(f"POST {path}")
        r = self.session.post(url, json=body, timeout=10)
        r.raise_for_status()
        return r.json()

    # ── Notifications ─────────────────────────────────────────────────────────

    def get_notifications(self, page: int = 1, page_size: int = 100) -> list[dict]:
        """
        Fetch notifications for the bannerusmaximus account.
        Returns list of notification dicts, newest first.

        Confirmed structure:
            id, createdOn, title, text, link, type, isSeen, isDeleted
        Mention notifications:
            title ends with "mentioned you in a thread"
            link ends with 36-char thread UUID
        """
        data = self._get("/notifications", params={"page": page, "pageSize": page_size})
        return data.get("notifications", [])

    # ── Threads ───────────────────────────────────────────────────────────────

    def get_thread(self, thread_id: str) -> dict:
        """
        Fetch full thread by ID.
        Returns thread dict with content, user, createdDate.
        """
        data = self._get("/threads", params={"threadId": thread_id})
        return data.get("thread", {})

    # ── Posting ───────────────────────────────────────────────────────────────

    def create_post(self, content: str) -> dict:
        """
        Create a new top-level post as @bannerusmaximus.
        Returns full thread dict from response.
        """
        data = self._post_req("/threads", {
            "content":       content,
            "files":         [],
            "privacyType":   0,
            "hasURLPreview": False,
        })
        thread = data.get("thread", {})
        logger.info(f"Posted | id={str(thread.get('id', '?'))[:8]}…")
        return thread

    def create_reply(self, content: str, thread_id: str, user_id: str) -> dict:
        """
        Post a reply to an existing thread as @bannerusmaximus.

        Uses the /threads/answer endpoint on api.starsarena.com —
        confirmed working from StarsBeggar repo. Note: different base URL
        from the rest of this client (api.arena.social vs api.starsarena.com).

        Body requires threadId + userId of the post being replied to.
        Content is wrapped in <div> tags as Arena renders HTML.
        """
        self._throttle()
        url = "https://api.starsarena.com/threads/answer"
        logger.debug(f"POST threads/answer thread={thread_id[:8]}…")
        r = self.session.post(url, json={
            "content":  f"<div>{content}</div>",
            "threadId": thread_id,
            "userId":   user_id,
            "files":    [],
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        thread = data.get("thread", {})
        logger.info(f"Replied | thread={thread_id[:8]}… | id={str(thread.get('id', '?'))[:8]}…")
        return thread

    # ── User lookup ───────────────────────────────────────────────────────────

    def get_user_by_handle(self, handle: str) -> dict:
        """
        Resolve a handle to a user object.
        Returns user dict with id, ixHandle, dynamicAddress.
        """
        data = self._get("/user/handle", params={"handle": handle})
        return data.get("user", {})

    # ── Post fetching ─────────────────────────────────────────────────────────

    def fetch_epoch_posts(
        self,
        user_id: str,
        epoch_start,
        epoch_end,
    ) -> list[dict]:
        """
        Fetch all posts by a user within the epoch window.
        Uses /threads/feed/user on api.arena.social (regular API).
        Paginates and stops when posts fall before epoch_start.
        """
        from ingestion.arena_client import ArenaClient  # reuse _clean_post + _strip_html
        posts = []
        page = 1
        page_size = 20
        done = False

        epoch_start_str = epoch_start.isoformat()
        epoch_end_str   = epoch_end.isoformat()

        logger.info(
            f"Fetching posts for userId={user_id} "
            f"window={epoch_start.date()} → {epoch_end.date()}"
        )

        while not done:
            data = self._get(
                "/threads/feed/user",
                params={"userId": user_id, "page": page, "pageSize": page_size}
            )

            threads = data.get("threads", [])
            if not threads:
                break

            for thread in threads:
                created = thread.get("createdDate", "")

                # Skip posts outside window (e.g. pinned posts)
                if not created or created < epoch_start_str or created > epoch_end_str:
                    continue

                posts.append(_clean_post(thread))

            pagination = data.get("pagination", {})
            if not pagination.get("hasNextPage", False):
                break

            page += 1

        logger.info(f"Fetched {len(posts)} posts in epoch window")
        return posts


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()


def _clean_post(thread: dict) -> dict:
    return {
        "id":               thread.get("id"),
        "content":          _strip_html(thread.get("content", "")),
        "content_raw":      thread.get("content", ""),
        "created_at":       thread.get("createdDate"),
        "user_id":          thread.get("userId"),
        "is_reply":         thread.get("answerId") is not None,
        "parent_thread_id": thread.get("answerId"),
        "is_quote":         thread.get("repostId") is not None,
        "quoted_thread_id": thread.get("repostId"),
    }
