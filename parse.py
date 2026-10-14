# Turns a mydealz listing page into plain dicts (no usernames, texts or images kept).
# The server sends two page variants, so there are two readers:
#   1) embedded JSON (data-vue3) in the plain page that browsers get
#   2) rendered HTML cards in the prerendered page that bots get
import json
import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

# Brand keywords that hint at Apple products
APPLE_RE = re.compile(r"\b(apple|iphone|ipad|macbook|imac|mac mini|airpods|airtag|homepod)\b", re.I)

# Words that usually mean third-party accessories or gift cards
NOT_APPLE_RE = re.compile(
    r"(hülle|case|schutzfolie|panzerglas|kompatibel|halterung|ständer|kabel|guthaben"
    r"|gift ?card|geschenkkarte|für\s+(?:das\s+|den\s+|die\s+)?(?:apple|iphone|ipad|macbook|airpods))",
    re.I,
)


def is_apple(title: str) -> bool:
    # Heuristic only: brand keyword present and no accessory/gift-card wording
    return bool(APPLE_RE.search(title)) and not NOT_APPLE_RE.search(title)


def parse_price(text: str):
    # German format: "22.475€", "66.365,41€", "Kostenlos"; None if no number
    t = text.strip()
    if t.lower() == "kostenlos":
        return 0.0
    m = re.search(r"\d[\d.]*(?:,\d+)?", t)
    if not m:
        return None
    return float(m.group().replace(".", "").replace(",", "."))


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _iso_from_unix(ts) -> str | None:
    # Unix seconds to ISO 8601 UTC; 0 and None mean "not set"
    if not ts:
        return None
    return _iso(datetime.fromtimestamp(ts, tz=timezone.utc))


def parse_posted_at(chip_text: str, now: datetime):
    # Only "Gepostet vor ..." tells us the age; "Aktualisiert vor ..." does not
    m = re.search(r"Gepostet vor\s+(\d+)\s*([A-Za-zäöü]+)", chip_text)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("min"):
        delta = timedelta(minutes=n)
    elif unit.startswith("std"):
        delta = timedelta(hours=n)
    elif unit.startswith("tg"):
        delta = timedelta(days=n)
    elif unit.startswith("wo"):
        delta = timedelta(weeks=n)
    elif unit.startswith("mo"):
        delta = timedelta(days=30 * n)
    elif unit.startswith("j"):
        delta = timedelta(days=365 * n)
    else:
        return None
    # Relative ages are coarse, so the timestamp is an approximation (rounded to the minute)
    return _iso(now.replace(second=0, microsecond=0) - delta)


def parse_ends_at(chip_text: str, now: datetime):
    # "Läuft ab in 12h 48m 2s" -> approximate end time
    m = re.search(r"Läuft ab\s+in\s+(.*)", chip_text)
    if not m:
        return None
    rest = m.group(1)
    parts = {u: int(re.search(rf"(\d+)\s*{u}", rest).group(1)) if re.search(rf"(\d+)\s*{u}", rest) else 0
             for u in ("Tg", "h", "m", "s")}
    delta = timedelta(days=parts["Tg"], hours=parts["h"], minutes=parts["m"], seconds=parts["s"])
    return _iso(now + delta) if delta else None


# ---------- Reader 1: embedded JSON ----------

def _clean_price(price, list_price) -> float | None:
    # The site uses 0 for both "free" and "no price"; the list price tells them apart
    if price and price > 0:
        return float(price)
    if price == 0 and list_price and list_price > 0:
        return 0.0
    return None


def _shipping_json(ship: dict | None) -> float | None:
    # isFree: 1 = free, 0 = paid, null = unknown
    if not ship:
        return None
    if ship.get("isFree") == 1:
        return 0.0
    if ship.get("isFree") == 0:
        return float(ship.get("price") or 0)
    return None


def _from_json(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    deals = []
    for el in soup.select('div[data-handler="vue3"]'):
        raw = el.get("data-vue3")
        if not raw or '"ThreadMainListItemNormalizer"' not in raw:
            continue
        try:
            t = json.loads(raw).get("props", {}).get("thread")
        except json.JSONDecodeError:
            continue
        # Only real deals: vouchers and discussions have other types
        if not t or t.get("type") != "Deal":
            continue
        list_price = t.get("nextBestPrice")
        temp = t.get("temperature")
        title = t.get("title", "")
        # Only whitelisted fields are copied, the user object is never touched
        deals.append({
            "deal_id": str(t["threadId"]),
            "title": title,
            "category": (t.get("mainGroup") or {}).get("threadGroupUrlName"),
            "merchant": (t.get("merchant") or {}).get("merchantName") or t.get("linkHost"),
            "posted_at": _iso_from_unix(t.get("publishedAt")),
            "bumped_at": _iso_from_unix(t.get("bumpedAt")),
            "ends_at": _iso_from_unix((t.get("endDate") or {}).get("timestamp")),
            "is_apple": int(is_apple(title)),
            "status": "expired" if t.get("isExpired") else "active",
            "price": _clean_price(t.get("price"), list_price),
            "list_price": float(list_price) if list_price else None,
            "shipping_price": _shipping_json(t.get("shipping")),
            "temperature": round(temp, 1) if temp is not None else None,
            "comment_count": t.get("commentCount"),
        })
    return deals


# ---------- Reader 2: rendered cards ----------

def _merchant(art) -> str | None:
    link = art.select_one('a[data-t="merchantLink"]')
    if link:
        return link.get_text(strip=True)
    # Some deals show the merchant as plain text without a link
    node = art.find(string=re.compile(r"(Verfügbar|Einlösen) bei"))
    if node is None:
        return None
    # Use the direct parent only, a wider span would also contain the author name
    txt = node.parent.get_text(" ", strip=True)
    return re.sub(r"^(Verfügbar|Einlösen) bei\s*", "", txt) or None


def _first_int(el) -> int | None:
    m = re.search(r"-?\d+", el.get_text()) if el else None
    return int(m.group()) if m else None


def _from_cards(html: str, now: datetime, category: str | None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    deals = []
    # Only real deals: vouchers and discussions use other article classes
    for art in soup.select("article.cept-thread-item.thread--deal"):
        title_el = art.select_one("strong.thread-title a")
        if title_el is None:
            continue
        title = title_el.get("title") or title_el.get_text(strip=True)

        # Free deals lack the thread-price class, the wrapper span covers both cases
        price_el = art.select_one("span.vAlign--all-tt") or art.select_one(".thread-price")
        old_el = art.select_one(".text--lineThrough")
        truck = art.select_one("svg.icon--truck")

        chips = " ".join(c.get_text(" ", strip=True) for c in art.select("span.chip"))
        temp_el = art.select_one(".cept-vote-temp")

        deals.append({
            "deal_id": art["id"].removeprefix("thread_"),
            "title": title,
            "category": category,
            "merchant": _merchant(art),
            "posted_at": parse_posted_at(chips, now),
            "bumped_at": None,
            "ends_at": parse_ends_at(chips, now),
            "is_apple": int(is_apple(title)),
            "status": "expired" if "Abgelaufen" in chips else "active",
            "price": parse_price(price_el.get_text()) if price_el else None,
            "list_price": parse_price(old_el.get_text()) if old_el else None,
            "shipping_price": parse_price(truck.parent.get_text(" ", strip=True)) if truck else None,
            "temperature": float(_first_int(temp_el)) if _first_int(temp_el) is not None else None,
            "comment_count": _first_int(art.select_one('a[data-t="commentsLink"]')),
        })
    return deals


def parse_listing(html: str, now: datetime, category: str | None = None) -> list[dict]:
    # Prefer the exact JSON data, fall back to the rendered cards
    deals = _from_json(html)
    return deals if deals else _from_cards(html, now, category)
