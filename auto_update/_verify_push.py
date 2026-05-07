"""Verify push content matches the country."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
from notifier import build_message, WEBSITE_URL

with open("data/news.json", "r", encoding="utf-8") as f:
    news = json.load(f)

today = [n for n in news if n.get("fetched_date") == "2026-05-07"]
print(f"Today items: {len(today)}")
print(f"Website URL: {WEBSITE_URL}")
msg = build_message(today, "2026-05-07")
if msg:
    print(f"\n--- PUSH CONTENT ---")
    print(msg[:800])
    print("--- END ---")
    indonesia_words = ["indonesia", "印尼", "印度尼西亚", "ojk", "adakami"]
    thailand_words = ["thailand", "泰国", "paypaya", "เพย์พาญ่า", "bot thailand"]
    msg_lower = msg.lower()
    for w in indonesia_words:
        if w in msg_lower:
            print(f"  WARNING: found Indonesia marker '{w}' in PH push!")
    for w in thailand_words:
        if w in msg_lower:
            print(f"  WARNING: found Thailand marker '{w}' in PH push!")
    print("  Country check: OK" if not any(w in msg_lower for w in indonesia_words + thailand_words) else "")
