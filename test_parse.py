# Minimal checks for parse.py and store.py, run with: python test_parse.py
import html as htmllib
import json
import sqlite3
from datetime import datetime, timezone

from db import SCHEMA
from parse import parse_listing, is_apple
from store import save_deals

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


# ---------- Reader 1: embedded JSON ----------

def card(thread: dict, escaped: bool = True) -> str:
    # Same wrapper the real page uses: JSON inside a data-vue3 attribute
    payload = json.dumps({"name": "ThreadMainListItemNormalizer", "props": {"thread": thread}})
    if escaped:
        return f'<article><div class="js-vue3" data-handler="vue3" data-vue3="{htmllib.escape(payload)}"></div></article>'
    # The real page leaves "&" unescaped inside a single-quoted attribute
    return f"<article><div class=\"js-vue3\" data-handler=\"vue3\" data-vue3='{payload}'></div></article>"


BASE = {"isExpired": False, "bumpedAt": 0, "endDate": None, "shipping": {"isFree": None, "price": 0},
        "user": {"username": "SECRET_USER"}, "mainGroup": {"threadGroupUrlName": "gaming"}}

normal = {**BASE, "threadId": "1", "type": "Deal", "title": "Mortal Kombat & Co | Switch", "commentCount": 2,
          "temperature": 78.74, "price": 11.99, "nextBestPrice": 39.99, "publishedAt": 1791704625,
          "endDate": {"timestamp": 1793055540}, "shipping": {"isFree": 1, "price": 0},
          "merchant": {"merchantName": "Nintendo eShop"}}
free = {**BASE, "threadId": "2", "type": "Deal", "title": "PDF Reader PRO", "commentCount": 137,
        "temperature": 4183.9, "price": 0, "nextBestPrice": 9.99, "publishedAt": 1791693886,
        "bumpedAt": 1791693886, "merchant": {"merchantName": "Google Play"}}
noprice = {**BASE, "threadId": "3", "type": "Deal", "title": "Ernsting's 30% auf alles", "commentCount": 0,
           "temperature": 83.24, "price": 0, "nextBestPrice": 0, "publishedAt": 1791696204,
           "merchant": {"merchantName": "Ernsting's family"}}
nomerchant = {**BASE, "threadId": "4", "type": "Deal", "title": "Gratis Parken", "commentCount": 124,
              "temperature": 2960.93, "price": 0, "nextBestPrice": 0, "publishedAt": 1791619563,
              "merchant": None, "linkHost": "parkfuchs.app", "shipping": {"isFree": 0, "price": 3.99}}
voucher = {**BASE, "threadId": "5", "type": "Voucher", "title": "IKEA 20%"}
discussion = {**BASE, "threadId": "6", "type": "Discussion", "title": "Question of the Week"}

html = "".join([card(normal), card(free, escaped=False), card(noprice), card(nomerchant),
                card(voucher), card(discussion), "<article>no data here</article>"])
deals = {d["deal_id"]: d for d in parse_listing(html, NOW)}

# Only deals survive, vouchers and discussions are skipped
assert set(deals) == {"1", "2", "3", "4"}

d = deals["1"]
assert d["title"] == "Mortal Kombat & Co | Switch" and d["category"] == "gaming"
assert d["price"] == 11.99 and d["list_price"] == 39.99 and d["shipping_price"] == 0.0
assert d["temperature"] == 78.7 and d["comment_count"] == 2
# Unix 1791704625 is the 11 Oct 2026, 07:43:45 UTC
assert d["posted_at"] == "2026-10-11T07:43:45+00:00"
assert d["ends_at"] is not None and d["bumped_at"] is None and d["merchant"] == "Nintendo eShop"

# Price 0 means free only when a list price exists, otherwise there is no price
assert deals["2"]["price"] == 0.0 and deals["2"]["bumped_at"] is not None
assert deals["3"]["price"] is None and deals["3"]["merchant"] == "Ernsting's family"

# Missing merchant falls back to the link host, paid shipping is kept
assert deals["4"]["merchant"] == "parkfuchs.app" and deals["4"]["shipping_price"] == 3.99

# No personal data leaks into the output
assert "SECRET_USER" not in json.dumps(list(deals.values()))


# ---------- Reader 2: rendered cards (what bots receive) ----------

CARDS = """
<article id="thread_10" class="thread cept-thread-item thread--deal"><div>
 <button class="cept-vote-temp vote-temp"><span>64°</span></button>
 <span class="chip chip--type-default"><span>Gepostet vor 1 Std.</span></span>
 <strong class="thread-title"><a title="Mortal Kombat &amp; Co | Switch">x</a></strong>
 <span class="overflow--wrap-off"><span class="vAlign--all-tt"><span class="text--b thread-price">24,49€</span></span>
  <span class="text--lineThrough">48,99€</span></span>
 <span><span>inkl.</span><svg class="icon icon--truck"></svg><span>3,99€</span></span>
 <span>Verfügbar bei <a data-t="merchantLink">Nintendo eShop</a></span>
 <span>Veröffentlicht von SECRET_USER</span>
 <a data-t="commentsLink"><svg></svg> 12</a></div></article>
<article id="thread_11" class="thread cept-thread-item thread--deal"><div>
 <button class="cept-vote-temp"><span>4140°</span></button>
 <span class="chip"><span>Aktualisiert vor 4 Std.</span></span>
 <strong class="thread-title"><a title="PDF Reader PRO">x</a></strong>
 <span class="vAlign--all-tt"><span class="text--b color--text-StatusPositive">Kostenlos</span></span>
 <span class="text--lineThrough">9,99€</span>
 <a data-t="commentsLink"> 137</a></div></article>
<article id="thread_12" class="thread cept-thread-item thread--deal"><div>
 <button class="cept-vote-temp"><span>2898°</span></button>
 <span class="chip chip--type-warning"><span>Läuft ab in 12h 48m 2s</span></span>
 <strong class="thread-title"><a title="Gratis Parken">x</a></strong>
 <span class="flex"><span>Verfügbar bei <span>parkfuchs.app</span></span><span>Veröffentlicht von SECRET_USER</span></span>
 <a data-t="commentsLink"> 137</a></div></article>
<article id="thread_13" class="thread cept-thread-item thread--deal"><div>
 <strong class="thread-title"><a title="Ernsting 30%">x</a></strong>
 <span class="chip"><span>Gepostet vor 2 Wo.</span></span></div></article>
<article id="thread_14" class="thread cept-thread-item thread--voucher"><strong class="thread-title"><span title="IKEA">x</span></strong></article>
<article id="thread_15" class="thread cept-thread-item thread--discussion"><strong class="thread-title"><a title="QotW">x</a></strong></article>
"""
rd = {d["deal_id"]: d for d in parse_listing(CARDS, NOW, "gaming")}
assert set(rd) == {"10", "11", "12", "13"}

a = rd["10"]
assert a["title"] == "Mortal Kombat & Co | Switch" and a["category"] == "gaming"
assert a["price"] == 24.49 and a["list_price"] == 48.99 and a["shipping_price"] == 3.99
assert a["temperature"] == 64.0 and a["comment_count"] == 12 and a["merchant"] == "Nintendo eShop"
assert a["posted_at"] == "2026-10-11T11:00:00+00:00"

# Free deal: no thread-price class, wrapper span still delivers the text
assert rd["11"]["price"] == 0.0 and rd["11"]["list_price"] == 9.99 and rd["11"]["posted_at"] is None

# Expiring chip becomes an end time, plain-text merchant must not swallow the author
assert rd["12"]["ends_at"] == "2026-10-12T00:48:02+00:00"
assert rd["12"]["merchant"] == "parkfuchs.app"

# Card without price or votes stays valid with empty fields
assert rd["13"]["price"] is None and rd["13"]["temperature"] is None
assert rd["13"]["posted_at"] == "2026-09-27T12:00:00+00:00"
assert "SECRET_USER" not in json.dumps(list(rd.values()))


# ---------- Apple heuristic and store ----------

assert is_apple("Apple AirPods Pro 3 für 199€")
assert not is_apple("Hülle für iPhone 16") and not is_apple("Apple Guthaben kaufen")

# Second run adds a snapshot and keeps the earliest posted_at
conn = sqlite3.connect(":memory:")
conn.executescript(SCHEMA)
save_deals(conn, list(deals.values()), "2026-10-11T12:00:00+00:00")
later = dict(deals["2"], posted_at="2026-10-12T00:00:00+00:00", temperature=4200.0)
save_deals(conn, [later], "2026-10-11T18:00:00+00:00")
assert conn.execute("select count(*) from deals").fetchone()[0] == 4
assert conn.execute("select count(*) from deal_snapshots").fetchone()[0] == 5
assert conn.execute("select posted_at from deals where deal_id='2'").fetchone()[0] == deals["2"]["posted_at"]
print("all tests passed")
