# One snapshot run: fetch listing pages, parse, store. Schedule this 2-3 times a day.
from datetime import datetime, timezone

from config import BASE_URL, TARGETS, MAX_REQUESTS_PER_RUN
from db import get_conn, init_db
from fetch import polite_get, save_raw
from parse import parse_listing
from store import save_deals


def page_url(path: str, page: int) -> str:
    # Plain ?page=N is allowed by robots.txt, the site's own ajax variant is not
    url = BASE_URL + path
    return url if page == 1 else f"{url}?page={page}"


def main() -> None:
    init_db()
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Dedupe within a run so a deal seen on several pages gets one snapshot
    seen: dict[str, dict] = {}
    requests_done = 0
    for path, category, pages in TARGETS:
        for page in range(1, pages + 1):
            if requests_done >= MAX_REQUESTS_PER_RUN:
                break
            html = polite_get(page_url(path, page))
            requests_done += 1
            if html is None:
                break  # blocked by robots.txt
            # Relative ages like "vor 5 Min." refer to the moment of this response
            page_now = datetime.now(timezone.utc)
            save_raw(html, f"{path.strip('/').replace('/', '_') or 'home'}_p{page}")
            deals = parse_listing(html, page_now, category)
            print(f"{path} page {page}: {len(deals)} deals")
            # Zero deals usually means a layout change or a block page
            if not deals:
                print("[warn] nothing parsed, skipping the rest of this target")
                break
            for d in deals:
                prev = seen.get(d["deal_id"])
                # Keep the copy that knows its category
                if prev is None or (prev["category"] is None and d["category"]):
                    seen[d["deal_id"]] = d

    with get_conn() as conn:
        save_deals(conn, list(seen.values()), scraped_at)
    print(f"Saved {len(seen)} deals at {scraped_at}")


if __name__ == "__main__":
    main()
