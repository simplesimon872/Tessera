import os, sys, json, requests
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

r = requests.get(BASE + "/agents/notifications", headers=HEADERS, params={"page":1,"pageSize":5}, timeout=5)
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2)[:3000])
