# SQLite schema and connection helpers
import sqlite3
from config import DB_PATH, DATA_DIR

SCHEMA = """
-- Static deal attributes, one row per deal
CREATE TABLE IF NOT EXISTS deals (
    deal_id     TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    category    TEXT,              -- main group url name, e.g. 'gaming'
    merchant    TEXT,
    posted_at   TEXT,              -- earliest publish time seen, ISO 8601 UTC
    bumped_at   TEXT,              -- set when the site re-surfaced an old deal
    ends_at     TEXT,              -- planned end of the offer, NULL if open
    is_apple    INTEGER DEFAULT 0, -- result of keyword detection
    status      TEXT DEFAULT 'active',
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);

-- Time series: one row per deal per scrape (needed for price history)
CREATE TABLE IF NOT EXISTS deal_snapshots (
    snapshot_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id        TEXT NOT NULL REFERENCES deals(deal_id),
    scraped_at     TEXT NOT NULL,  -- ISO 8601 UTC
    price          REAL,           -- NULL if the deal has no price, 0 if free
    list_price     REAL,           -- price comparison value shown by the site
    shipping_price REAL,           -- NULL if unknown, 0 if free shipping
    temperature    REAL,           -- "hotness"
    comment_count  INTEGER
);

-- Speeds up per-deal history lookups
CREATE INDEX IF NOT EXISTS ix_snap_deal_time ON deal_snapshots(deal_id, scraped_at);

-- Small, manually observed sample. No raw page, comment text, or usernames.
CREATE TABLE IF NOT EXISTS manual_observations (
    observation_id    TEXT PRIMARY KEY,
    deal_ref          TEXT NOT NULL,
    product_key       TEXT NOT NULL,
    product_label     TEXT NOT NULL,
    observed_at       TEXT NOT NULL,
    category          TEXT NOT NULL,
    merchant          TEXT NOT NULL,
    price_eur         REAL,
    shipping_eur      REAL,
    reference_price_eur REAL,
    temperature       REAL,
    comment_count     INTEGER,
    availability      TEXT NOT NULL CHECK (availability IN ('active', 'expired', 'unknown')),
    is_apple_product  INTEGER CHECK (is_apple_product IN (0, 1) OR is_apple_product IS NULL),
    source_url        TEXT,
    imported_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_manual_product_time
    ON manual_observations(product_key, observed_at);
CREATE INDEX IF NOT EXISTS ix_manual_category_time
    ON manual_observations(category, observed_at);

-- Deliberately NOT stored: usernames, comment texts, descriptions, images
"""

def get_conn():
    # Make sure the data folder exists, then open the DB with FK checks on
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    # Idempotent: safe to run on every start
    with get_conn() as conn:
        conn.executescript(SCHEMA)

if __name__ == "__main__":
    init_db()
    print(f"DB ready: {DB_PATH}")
