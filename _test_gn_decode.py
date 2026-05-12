"""Test decoding Google News RSS URLs to actual article URLs."""
import json, sys, io, re, base64
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def decode_google_news_url(gn_url: str) -> str:
    """Try to decode a Google News RSS article URL to the actual article URL."""
    if "news.google.com" not in gn_url:
        return gn_url

    # Method 1: Follow redirects with GET
    try:
        resp = requests.get(gn_url, allow_redirects=True, timeout=12,
                           headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        if resp.url and "news.google.com" not in resp.url:
            return resp.url
        # Check for meta refresh or JS redirect in body
        text = resp.text[:3000]
        meta_match = re.search(r'<meta[^>]+url=(https?://[^"\'>\s]+)', text, re.I)
        if meta_match:
            return meta_match.group(1)
        # Check for data-url or href
        href_match = re.search(r'data-n-au="(https?://[^"]+)"', text)
        if href_match:
            return href_match.group(1)
    except Exception as e:
        print(f"  GET failed: {e}")

    # Method 2: Try base64 decode from URL path
    try:
        article_id = gn_url.split("/articles/")[1].split("?")[0]
        # Google News uses modified base64
        padded = article_id + "=" * (4 - len(article_id) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        # Look for URL pattern in decoded bytes
        urls = re.findall(rb'https?://[^\x00-\x1f\x7f-\xff]+', decoded)
        if urls:
            return urls[0].decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  Base64 decode failed: {e}")

    return gn_url


# Test with a few Indonesia Google News URLs
with open(r"d:\17AI\3cursor\2news-id\auto_update\data\news.json", "r", encoding="utf-8") as f:
    news = json.load(f)

gn_items = [n for n in news if "news.google.com" in n.get("url", "")]
print(f"Found {len(gn_items)} Google News URLs in Indonesia data\n")

for item in gn_items[:5]:
    url = item["url"]
    pub = item.get("published", "?")
    title = (item.get("title_zh") or item.get("title", ""))[:55]
    print(f"[{pub}] {title}")
    print(f"  GN: {url[:80]}...")
    actual = decode_google_news_url(url)
    if actual != url:
        print(f"  RESOLVED: {actual[:100]}")
        # Check for date in resolved URL
        url_date_m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", actual)
        if url_date_m:
            url_date = f"{url_date_m.group(1)}-{url_date_m.group(2)}-{url_date_m.group(3)}"
            match = "MATCH" if url_date == pub else f"MISMATCH (url={url_date}, pub={pub})"
            print(f"  URL Date: {url_date} -> {match}")
    else:
        print(f"  NOT RESOLVED")
    print()
