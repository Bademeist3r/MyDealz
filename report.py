# Quick sanity report on the collected data (no sqlite3 CLI needed)
import sqlite3

from config import DB_PATH

conn = sqlite3.connect(DB_PATH)


def show(title: str, sql: str) -> None:
    print(f"\n{title}")
    for row in conn.execute(sql):
        print("  ", row)


show("Deals / snapshots",
     "SELECT (SELECT COUNT(*) FROM deals), (SELECT COUNT(*) FROM deal_snapshots)")
show("Deals per category",
     "SELECT COALESCE(category, '(none)'), COUNT(*) FROM deals GROUP BY 1 ORDER BY 2 DESC")
show("Snapshots with NULL price / temperature / comments / shipping, total",
     "SELECT SUM(price IS NULL), SUM(temperature IS NULL), SUM(comment_count IS NULL), "
     "SUM(shipping_price IS NULL), COUNT(*) FROM deal_snapshots")
show("Top 5 by temperature",
     "SELECT SUBSTR(d.title, 1, 55), s.temperature, s.comment_count FROM deals d "
     "JOIN deal_snapshots s USING (deal_id) WHERE s.temperature IS NOT NULL "
     "ORDER BY s.temperature DESC LIMIT 5")
show("Top 5 by comments",
     "SELECT SUBSTR(d.title, 1, 55), s.comment_count, s.temperature FROM deals d "
     "JOIN deal_snapshots s USING (deal_id) WHERE s.comment_count IS NOT NULL "
     "ORDER BY s.comment_count DESC LIMIT 5")
show("Apple deals (heuristic)", "SELECT COUNT(*) FROM deals WHERE is_apple = 1")
