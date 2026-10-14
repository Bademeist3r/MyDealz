# Writes parsed deals into SQLite: one row per deal, one snapshot per scrape
def save_deals(conn, deals: list[dict], scraped_at: str) -> None:
    for d in deals:
        # Upsert keeps first_seen; posted_at keeps the earliest value because bumps move it forward
        conn.execute(
            """
            INSERT INTO deals (deal_id, title, category, merchant, posted_at, bumped_at,
                               ends_at, is_apple, status, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(deal_id) DO UPDATE SET
                title     = excluded.title,
                category  = COALESCE(excluded.category, deals.category),
                merchant  = COALESCE(excluded.merchant, deals.merchant),
                posted_at = COALESCE(MIN(deals.posted_at, excluded.posted_at),
                                     deals.posted_at, excluded.posted_at),
                bumped_at = COALESCE(excluded.bumped_at, deals.bumped_at),
                ends_at   = COALESCE(excluded.ends_at, deals.ends_at),
                is_apple  = excluded.is_apple,
                status    = excluded.status,
                last_seen = excluded.last_seen
            """,
            (d["deal_id"], d["title"], d["category"], d["merchant"], d["posted_at"],
             d["bumped_at"], d["ends_at"], d["is_apple"], d["status"], scraped_at, scraped_at),
        )
        # Every run adds a snapshot, this is the time series for price history
        conn.execute(
            """
            INSERT INTO deal_snapshots (deal_id, scraped_at, price, list_price,
                                        shipping_price, temperature, comment_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (d["deal_id"], scraped_at, d["price"], d["list_price"],
             d["shipping_price"], d["temperature"], d["comment_count"]),
        )
