import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
from notifier import build_message

with open("data/news.json", "r", encoding="utf-8") as f:
    news = json.load(f)

today = [n for n in news if n.get("fetched_date") == "2026-05-07"]
print(f"PH today items: {len(today)}")
for i, n in enumerate(today[:5], 1):
    tz = n.get("title_zh") or n.get("title", "")
    print(f"  [{i}] {tz[:60]}")

msg = build_message(today, "2026-05-07")
if msg:
    print(f"\nMSG length: {len(msg)}")
    print("--- MSG START ---")
    print(msg)
    print("--- MSG END ---")
else:
    print("\nNO MSG (empty today)")
