"""Full regeneration with validation and data cleanup."""
import sys, io, json, logging
from datetime import datetime, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

from config import DATA_DIR
from fetcher import load_existing_news, save_news
from generator import generate_all_pages
from translator import translate_news_item

news = load_existing_news()
print(f"Loaded {len(news)} items")

# Step 1: Retranslate any items missing Chinese
retrans = 0
for n in news:
    title_zh = n.get("title_zh", "")
    summary_zh = n.get("summary_zh", "")
    if not title_zh or not summary_zh:
        translate_news_item(n)
        retrans += 1
if retrans:
    print(f"Retranslated {retrans} items")

# Step 2: Remove items with bad/missing dates
before = len(news)
news = [n for n in news if n.get("published") and len(n["published"]) == 10 and n["published"] >= "2026-01-01"]
if len(news) < before:
    print(f"Removed {before - len(news)} invalid items")

# Step 3: Save cleaned data
save_news(news)

# Step 4: Regenerate pages (don't increment vol)
vol_file = DATA_DIR / "vol_counter.txt"
vol = int(vol_file.read_text().strip()) if vol_file.exists() else 1
generate_all_pages(news, vol_number=vol)

# Step 5: Summary
today = datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
yn = [n for n in news if n.get("published") == yesterday]
mn = [n for n in news if n.get("published", "").startswith(datetime.now().strftime("%Y-%m"))]
print(f"\n=== RESULT ===")
print(f"Total: {len(news)} | Yesterday ({yesterday}): {len(yn)} | This month: {len(mn)}")
print(f"Pre-2026: {sum(1 for n in news if n.get('published','') < '2026-01-01')}")
print(f"No date: {sum(1 for n in news if not n.get('published'))}")
print("Done.")
