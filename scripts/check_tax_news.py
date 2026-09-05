"""Weekly check for Vietnamese tax-law news via Google News RSS.

Fetches recent articles for a list of tax-related keywords, skips
anything already recorded in data/tax_news.json, appends the new
items there, and pushes an ntfy notification for anything new.
"""

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "tax_news.json")

KEYWORDS = [
    "thuế thu nhập cá nhân",
    "thuế giá trị gia tăng",
    "thuế thu nhập doanh nghiệp",
    "thuế tiêu thụ đặc biệt",
    "thuế xuất nhập khẩu",
    "thuế bảo vệ môi trường",
    "thuế sử dụng đất",
    "thuế tài nguyên",
    "lệ phí trước bạ",
    "thuế nhà thầu nước ngoài",
    "thuế hộ kinh doanh",
    "thuế chuyển nhượng bất động sản",
]

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=vi&gl=VN&ceid=VN:vi"
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "10"))


def fetch_rss(keyword: str) -> list[dict]:
    query = urllib.parse.quote(f'"{keyword}"')
    url = RSS_URL.format(query=query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)
    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source = (item.findtext("source") or "").strip()
        if title and link:
            items.append(
                {
                    "keyword": keyword,
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "source": source,
                }
            )
    return items


def parse_pub_date(pub_date: str) -> datetime | None:
    # RFC 822 style, e.g. "Thu, 04 Sep 2026 03:00:00 GMT"
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            dt = datetime.strptime(pub_date, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def link_id(link: str) -> str:
    return hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]


def load_seen() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen_ids": [], "articles": []}


def save_seen(data: dict) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def notify(new_items: list[dict]) -> None:
    if not NTFY_TOPIC:
        print("NTFY_TOPIC not set, skipping notification.", file=sys.stderr)
        return

    MAX_BODY_BYTES = 3500  # stay well under ntfy's ~4096 byte message cap

    if len(new_items) == 1:
        item = new_items[0]
        title = f"Tin thuế mới: {item['keyword']}"
        body = f"{item['title']}\n{item['link']}"
    else:
        title = f"{len(new_items)} tin thuế mới"
        lines = []
        shown_count = 0
        for it in new_items:
            line = f"- {it['title']}\n  {it['link']}"
            candidate = "\n\n".join(lines + [line])
            if len(candidate.encode("utf-8")) > MAX_BODY_BYTES:
                break
            lines.append(line)
            shown_count += 1
        body = "\n\n".join(lines)
        if shown_count < len(new_items):
            body += f"\n\n... và {len(new_items) - shown_count} tin khác (xem data/tax_news.json trên repo)."

    # Use ntfy's JSON publish endpoint (not the header-based one) since headers
    # must be ASCII and our titles/messages contain Vietnamese diacritics.
    payload = json.dumps(
        {"topic": NTFY_TOPIC, "title": title, "message": body},
        ensure_ascii=False,
    ).encode("utf-8")
    last_error = None
    for attempt in range(3):
        req = urllib.request.Request(
            NTFY_SERVER.rstrip("/") + "/",
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp.read()
            return
        except urllib.error.HTTPError as exc:
            last_error = exc
            detail = exc.read().decode("utf-8", "replace")
            print(f"ntfy attempt {attempt + 1} failed: HTTP {exc.code} {detail}", file=sys.stderr)
        except urllib.error.URLError as exc:
            last_error = exc
            print(f"ntfy attempt {attempt + 1} failed: {exc}", file=sys.stderr)
        time.sleep(2 * (attempt + 1))

    assert last_error is not None
    raise last_error


def main() -> None:
    data = load_seen()
    seen_ids = set(data.get("seen_ids", []))
    now = datetime.now(timezone.utc)
    new_items = []

    for keyword in KEYWORDS:
        try:
            items = fetch_rss(keyword)
        except Exception as exc:  # network hiccups shouldn't kill the whole run
            print(f"Failed to fetch '{keyword}': {exc}", file=sys.stderr)
            continue

        for item in items:
            pub_dt = parse_pub_date(item["pub_date"])
            if pub_dt and (now - pub_dt).days > MAX_AGE_DAYS:
                continue

            iid = link_id(item["link"])
            if iid in seen_ids:
                continue

            seen_ids.add(iid)
            item["id"] = iid
            item["found_at"] = now.isoformat()
            new_items.append(item)

        time.sleep(1)  # be polite to Google News

    if new_items:
        data["seen_ids"] = list(seen_ids)
        data["articles"] = new_items + data.get("articles", [])
        data["last_run"] = now.isoformat()
        save_seen(data)
        notify(new_items)
        print(f"Found {len(new_items)} new article(s).")
    else:
        data["last_run"] = now.isoformat()
        save_seen(data)
        print("No new articles.")


if __name__ == "__main__":
    main()
