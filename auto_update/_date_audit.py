"""Audit: compare news published dates with display dates."""
import json, sys, io
from datetime import datetime, timedelta
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

with open("data/news.json", "r", encoding="utf-8") as f:
    news = json.load(f)

today = datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

print(f"=== PHILIPPINES DATE AUDIT ({today}) ===")
print(f"Total items: {len(news)}")

# 1. Check published date distribution
pub_dates = Counter(n.get("published", "MISSING") for n in news)
print(f"\n--- Published date distribution ---")
for d, c in sorted(pub_dates.items(), reverse=True)[:15]:
    marker = " <-- yesterday" if d == yesterday else (" <-- today" if d == today else "")
    print(f"  {d}: {c} items{marker}")

# 2. Check for items with missing published
missing = [n for n in news if not n.get("published")]
if missing:
    print(f"\n!!! {len(missing)} items with MISSING published date:")
    for n in missing[:5]:
        print(f"  title: {(n.get('title_zh') or n.get('title',''))[:50]}")

# 3. Check fetched_date vs published mismatch
print(f"\n--- Fetched vs Published mismatch ---")
mismatches = 0
for n in news:
    pub = n.get("published", "")
    fetch = n.get("fetched_date", "")
    if pub and fetch and pub != fetch:
        pass  # Normal - article published on different day than fetched
    if pub == today and fetch != today:
        mismatches += 1
        title = (n.get("title_zh") or n.get("title", ""))[:50]
        print(f"  pub={pub} fetch={fetch} {title}")
print(f"  Items published today but not fetched today: {mismatches}")

# 4. Check specific items - show title_zh, published, fetched_date, sections
print(f"\n--- Sample items (last 10 by published date) ---")
sorted_news = sorted(news, key=lambda x: x.get("published", ""), reverse=True)
for n in sorted_news[:10]:
    pub = n.get("published", "?")
    fetch = n.get("fetched_date", "?")
    title = (n.get("title_zh") or n.get("title", ""))[:60]
    secs = n.get("sections", [])
    print(f"  [{pub}] (fetch:{fetch}) [{','.join(secs)}] {title}")

# 5. Check yesterday's news for push
yn = [n for n in news if n.get("published") == yesterday]
print(f"\n--- Yesterday ({yesterday}): {len(yn)} items ---")
for n in yn[:5]:
    title = (n.get("title_zh") or n.get("title", ""))[:60]
    print(f"  {title}")
