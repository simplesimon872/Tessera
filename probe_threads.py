"""
Probe /threads/feed/user to see raw response structure.
Run from Tessera root: python probe_threads.py
"""
import os, json, requests
from dotenv import load_dotenv
load_dotenv()

token   = os.getenv("BANNERUS_API_KEY")
user_id = "66e9b3be-8cb3-43a9-84df-565c6244cdf3"  # simplesimon872

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
}

# Try 1: userId param
print("=== /threads/feed/user?userId= ===")
r = requests.get(
    "https://api.arena.social/threads/feed/user",
    params={"userId": user_id, "page": 1, "pageSize": 5},
    headers=headers,
    timeout=10
)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Top-level keys: {list(data.keys())}")
threads = data.get("threads", data.get("data", data.get("posts", [])))
print(f"Thread count: {len(threads)}")
if threads:
    print(f"First thread keys: {list(threads[0].keys())}")
    print(f"First thread createdAt: {threads[0].get('createdAt', threads[0].get('createdDate', threads[0].get('created_at', 'NOT FOUND')))}")
    print(f"First thread snippet: {str(threads[0])[:300]}")
else:
    print(f"Raw response: {json.dumps(data, indent=2)[:1000]}")

# Try 2: id param instead of userId
print("\n=== /threads/feed/user?id= ===")
r2 = requests.get(
    "https://api.arena.social/threads/feed/user",
    params={"id": user_id, "page": 1, "pageSize": 5},
    headers=headers,
    timeout=10
)
print(f"Status: {r2.status_code}")
data2 = r2.json()
print(f"Top-level keys: {list(data2.keys())}")

# Try 3: no auth, public endpoint
print("\n=== /threads/feed/user (no auth) ===")
r3 = requests.get(
    "https://api.arena.social/threads/feed/user",
    params={"userId": user_id, "page": 1, "pageSize": 5},
    timeout=10
)
print(f"Status: {r3.status_code}")
