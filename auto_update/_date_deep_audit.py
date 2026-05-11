"""Deep audit: find items with suspicious published dates."""
import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

with open("data/news.json", "r", encoding="utf-8") as f:
    news = json.load(f)

print(f"=== INDONESIA: Deep date audit ===")
print(f"Total: {len(news)} items\n")

suspicious = []
for n in news:
    pub = n.get("published", "")
    fetch = n.get("fetched_date", "")
    title = n.get("title_zh") or n.get("title", "")
    summary = n.get("summary_zh") or n.get("summary", "")
    text = title + " " + summary

    issues = []
    # Check 1: title mentions a year different from published year
    years_in_text = set(re.findall(r'20[12]\d', text))
    pub_year = pub[:4] if pub else ""
    for y in years_in_text:
        if y != pub_year and int(y) < 2026:
            issues.append(f"title mentions {y} but published={pub}")

    # Check 2: published == fetched_date (might be artificially set)
    if pub and fetch and pub == fetch and pub >= "2026-05-09":
        # These are likely items whose dates were overwritten
        if any(y in text for y in ["2020", "2021", "2022", "2023", "2024", "2025"]):
            issues.append(f"published={pub}==fetched={fetch}, but text mentions older year")

    if issues:
        suspicious.append((n, issues))
        print(f"SUSPECT: [{pub}] (fetch:{fetch}) {title[:65]}")
        for iss in issues:
            print(f"  -> {iss}")
        print()

print(f"--- Found {len(suspicious)} suspicious items ---")

# Also check: items with published=2026-05-09 fetched=2026-05-09 (from our fix)
may09 = [n for n in news if n.get("published") == "2026-05-09" and n.get("fetched_date") == "2026-05-09"]
print(f"\nItems with published=fetched=2026-05-09: {len(may09)}")
for n in may09:
    title = (n.get("title_zh") or n.get("title", ""))[:65]
    print(f"  {title}")
