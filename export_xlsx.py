# Exports the SQLite data to one Excel file for Power BI.
# Excel keeps column types, so there are no decimal-separator problems like with CSV.
import sqlite3

import pandas as pd

from config import DB_PATH, DATA_DIR

OUT = DATA_DIR / "mydealz_export.xlsx"


def to_dt(series: pd.Series) -> pd.Series:
    # ISO strings (UTC) to naive datetimes, Excel cannot store time zones
    return pd.to_datetime(series, utc=True).dt.tz_localize(None)


def apple_group(title: str, is_apple: int) -> str:
    # Product group for Apple deals; same keywords as the is_apple heuristic
    if not is_apple:
        return "Andere Deals"
    t = title.lower()
    if "iphone" in t:
        return "iPhone"
    if "ipad" in t:
        return "iPad"
    if "airpods" in t:
        return "AirPods"
    if any(k in t for k in ("macbook", "imac", "mac mini")):
        return "Mac"
    if "apple tv" in t:
        return "Apple TV"
    if "apple watch" in t:
        return "Apple Watch"
    return "Sonstige Apple-Deals"


def price_band(p) -> str:
    # Bands let Power BI hide outliers like cars with one click
    if pd.isna(p):
        return "Ohne Preis"
    if p == 0:
        return "Gratis"
    if p < 25:
        return "unter 25 EUR"
    if p < 100:
        return "25-100 EUR"
    if p < 500:
        return "100-500 EUR"
    return "ab 500 EUR"


conn = sqlite3.connect(DB_PATH)
deals = pd.read_sql("SELECT * FROM deals", conn)
snaps = pd.read_sql("SELECT * FROM deal_snapshots", conn)

for col in ("posted_at", "bumped_at", "ends_at", "first_seen", "last_seen"):
    deals[col] = to_dt(deals[col])
snaps["scraped_at"] = to_dt(snaps["scraped_at"])

# One row per deal with the values of its newest snapshot
latest = snaps.sort_values("scraped_at").groupby("deal_id").tail(1).drop(columns=["snapshot_id"])
dl = deals.merge(latest, on="deal_id")
dl["category"] = dl["category"].fillna("Ohne Kategorie")

# Derived columns that save DAX work in Power BI
dl["apple_group"] = [apple_group(t, a) for t, a in zip(dl["title"], dl["is_apple"])]
dl["price_band"] = dl["price"].map(price_band)
has_list = (dl["list_price"] > 0) & dl["price"].notna()
dl["discount_pct"] = ((1 - dl["price"] / dl["list_price"]) * 100).where(has_list).round(1)
dl["posted_date"] = dl["posted_at"].dt.normalize()
dl["posted_hour"] = dl["posted_at"].dt.hour
dl["posted_weekday"] = dl["posted_at"].dt.day_name()
dl["age_hours"] = ((dl["scraped_at"] - dl["posted_at"]).dt.total_seconds() / 3600).round(1)
dl["age_bucket"] = pd.cut(
    dl["age_hours"], bins=[-1, 6, 24, 168, float("inf")],
    labels=["1: under 6h", "2: 6-24h", "3: 1-7 days", "4: over 7 days"],
).astype("string")

# Snapshot history with the labels needed for charts
hist = snaps.merge(deals[["deal_id", "title", "category", "merchant"]], on="deal_id")
hist["category"] = hist["category"].fillna("Ohne Kategorie")

# Deals whose price really changed between snapshots
priced = snaps.dropna(subset=["price"]).sort_values("scraped_at")
g = priced.groupby("deal_id")["price"]
chg = pd.DataFrame({
    "n_snapshots": g.size(), "n_distinct_prices": g.nunique(),
    "first_price": g.first(), "last_price": g.last(),
    "min_price": g.min(), "max_price": g.max(),
}).reset_index()
chg = chg[chg["n_distinct_prices"] > 1].copy()
chg["change_pct"] = ((chg["last_price"] / chg["first_price"] - 1) * 100).round(1)
chg = chg.merge(deals[["deal_id", "title", "merchant", "category"]], on="deal_id")

with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
    dl.to_excel(xl, sheet_name="deals_latest", index=False)
    hist.to_excel(xl, sheet_name="snapshots", index=False)
    chg.to_excel(xl, sheet_name="price_changes", index=False)

print(f"{OUT}: {len(dl)} deals, {len(hist)} snapshots, {len(chg)} deals with price changes")
