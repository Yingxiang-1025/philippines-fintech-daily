"""Regenerate pages with validation and show results."""
import sys, io, logging
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

from fetcher import load_existing_news
from generator import generate_all_pages, get_next_vol_number

news = load_existing_news()
print(f"Loaded {len(news)} items")

# Don't increment vol, just use current
from config import DATA_DIR
vol_file = DATA_DIR / "vol_counter.txt"
if vol_file.exists():
    vol = int(vol_file.read_text().strip())
else:
    vol = 1

generate_all_pages(news, vol_number=vol)
print("Done.")
