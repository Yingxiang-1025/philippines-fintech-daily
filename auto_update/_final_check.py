"""Final verification: check generated HTML pages for date consistency."""
import sys, io, re, json
from datetime import datetime, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

today = datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
month_prefix = datetime.now().strftime("%Y-%m")

with open("data/news.json", "r", encoding="utf-8") as f:
    news = json.load(f)

print(f"=== FINAL DATE CONSISTENCY CHECK ===")
print(f"Today: {today}, Yesterday: {yesterday}, Month: {month_prefix}")
print(f"Total items in DB: {len(news)}")

# 1. Items without valid published date
no_date = [n for n in news if not n.get("published") or len(n["published"]) != 10]
print(f"\nItems without valid published date: {len(no_date)}")

# 2. Items with pre-2026 published date
pre2026 = [n for n in news if n.get("published", "9999") < "2026-01-01"]
print(f"Items with pre-2026 published date: {len(pre2026)}")
for n in pre2026:
    print(f"  [{n.get('published')}] {(n.get('title_zh') or n.get('title',''))[:50]}")

# 3. Yesterday items check
yn = [n for n in news if n.get("published") == yesterday]
print(f"\nYesterday ({yesterday}): {len(yn)} items")

# 4. Monthly items check
mn = [n for n in news if n.get("published", "").startswith(month_prefix)]
print(f"This month ({month_prefix}): {len(mn)} items")

# 5. Read generated yesterday.html and verify item count
try:
    with open("../pages/yesterday.html", "r", encoding="utf-8") as f:
        html = f.read()
    # Count cards in yesterday page
    card_count = html.count('class="card')
    header_match = re.search(r'昨日要闻 \((\d+) 条\)', html)
    if header_match:
        header_count = int(header_match.group(1))
        print(f"\nYesterday page: header says {header_count} items, found {card_count} cards")
        if header_count != len(yn):
            print(f"  WARNING: header count ({header_count}) != DB count ({len(yn)})")
    else:
        print(f"\nYesterday page: no header found (maybe empty), cards={card_count}")
except Exception as e:
    print(f"\nFailed to check yesterday.html: {e}")

# 6. Check for date-divider mismatches in section pages
import os
pages_dir = "../pages"
for fname in os.listdir(pages_dir):
    if not fname.endswith(".html"):
        continue
    with open(os.path.join(pages_dir, fname), "r", encoding="utf-8") as f:
        html = f.read()
    # Find date dividers and card published dates
    dividers = re.findall(r'class="date-divider">([\d-]+)<', html)
    card_dates = re.findall(r'<span>(20\d{2}-\d{2}-\d{2})</span>', html)
    pre2026_in_page = [d for d in card_dates if d < "2026-01-01"]
    if pre2026_in_page:
        print(f"  WARNING: {fname} has pre-2026 dates: {pre2026_in_page}")

print("\n=== CHECK COMPLETE ===")
