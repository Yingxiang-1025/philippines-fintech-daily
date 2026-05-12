"""Fix all 3 sites: resolve Google News URLs, correct dates, remove cross-country contamination."""
import json, re, sys, io, os, time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def resolve_google_news_url(gn_url: str) -> str:
    if "news.google.com" not in gn_url:
        return gn_url
    try:
        resp = requests.head(gn_url, allow_redirects=True, timeout=10,
                             headers={"User-Agent": "Mozilla/5.0"})
        final = resp.url
        if final and "news.google.com" not in final:
            return final
    except Exception:
        pass
    return gn_url


def extract_date_from_url(url: str):
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


TH_EXCLUDE = [
    "AdaKami", "Asetku", "Kredivo", "OJK", "Investree",
    "KoinWorks", "Modalku", "Danamas", "Amartha", "Kredit Pintar",
    "pinjaman online", "pinjol", "Indonesia GDP", "印度尼西亚",
    "Indonesia fintech", "Indonesian fintech", "Indonesia BNPL",
    "Indonesia lending", "Jakarta", "Akulaku", "GoPayLater", "Tokopedia",
]

ID_EXCLUDE = [
    "PAYPAYA", "เพย์พาญ่า", "Bank of Thailand", "BOT Thailand",
    "PromptPay", "TrueMoney", "กู้เงิน", "สินเชื่อ",
    "BSP Philippines", "Bangko Sentral", "Philippines fintech",
    "UnionBank Philippines", "GCash", "Maya Philippines",
]


def fix_site(data_path: str, exclude_kws: list, site_name: str):
    print(f"\n{'='*60}")
    print(f"  Fixing {site_name}: {data_path}")
    print(f"{'='*60}")

    with open(data_path, "r", encoding="utf-8") as f:
        news = json.load(f)
    print(f"  Loaded {len(news)} items")

    resolved = 0
    date_fixed = 0
    removed = 0
    clean_news = []

    for i, item in enumerate(news):
        title = item.get("title", "") + " " + item.get("title_zh", "")
        summary = item.get("summary", "") + " " + item.get("summary_zh", "")
        text = (title + " " + summary).lower()

        # Cross-country check
        excluded = False
        for kw in exclude_kws:
            if kw.lower() in text:
                print(f"  REMOVE (cross-country '{kw}'): {item.get('title_zh', item.get('title', ''))[:50]}")
                excluded = True
                removed += 1
                break
        if excluded:
            continue

        url = item.get("url", "")
        if "news.google.com" in url:
            actual = resolve_google_news_url(url)
            if actual != url:
                item["url"] = actual
                resolved += 1
                print(f"  RESOLVED URL [{i}]: ...{actual[-60:]}")

                url_date = extract_date_from_url(actual)
                if url_date:
                    pub = item.get("published", "")
                    if url_date != pub:
                        url_year = int(url_date[:4])
                        if url_year < 2026:
                            print(f"  REMOVE (old url_date={url_date}): {item.get('title_zh', item.get('title', ''))[:50]}")
                            removed += 1
                            continue
                        print(f"  DATE FIX: {pub} -> {url_date} : {item.get('title_zh', item.get('title', ''))[:40]}")
                        item["published"] = url_date
                        date_fixed += 1

            time.sleep(0.3)

        clean_news.append(item)

    print(f"\n  Results: resolved={resolved}, date_fixed={date_fixed}, removed={removed}")
    print(f"  Final: {len(clean_news)} items (was {len(news)})")

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(clean_news, f, ensure_ascii=False, indent=2)
    print(f"  Saved!")


sites = [
    (r"d:\17AI\3cursor\2news\auto_update\data\news.json", [], "Philippines"),
    (r"d:\17AI\3cursor\2news-id\auto_update\data\news.json", ID_EXCLUDE, "Indonesia"),
    (r"d:\17AI\3cursor\2news-th\auto_update\data\news.json", TH_EXCLUDE, "Thailand"),
]

for data_path, exclude, name in sites:
    if os.path.exists(data_path):
        fix_site(data_path, exclude, name)
    else:
        print(f"  SKIP {name}: {data_path} not found")
