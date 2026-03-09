"""
Probe Arena agents API to find what endpoints exist.
Run from the Tessera directory with:
    python /tmp/probe_arena.py
"""
import os, sys, requests
sys.path.insert(0, r"C:\~web3dev\Tessera")
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("ARENA_API_KEY", "")
BASE    = "https://api.starsarena.com"
HEADERS = {
    "X-API-Key":  API_KEY,
    "User-Agent": "Mozilla/5.0",
    "Accept":     "application/json",
}

candidates = [
    "/agents/threads/feed/mentions",
    "/agents/threads/mentions",
    "/agents/user/mentions",
    "/agents/threads/feed/home",
    "/agents/threads/feed",
    "/agents/threads/replies",
    "/agents/threads/feed/replies",
    "/agents/notifications",
    "/agents/notifications/mentions",
]

for path in candidates:
    try:
        r = requests.get(BASE + path, headers=HEADERS, params={"page":1,"pageSize":5}, timeout=5)
        print(f"  {r.status_code}  {path}")
    except Exception as e:
        print(f"  ERR  {path}: {e}")
