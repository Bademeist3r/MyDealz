# Polite fetching: robots.txt check, honest user agent, delays, raw HTML kept locally
import random
import time
from datetime import datetime, timezone

import requests
from protego import Protego

from config import BASE_URL, USER_AGENT, MIN_DELAY, MAX_DELAY, RAW_DIR

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_robots = None  # cached robots.txt parser


def _load_robots():
    # Fetch and parse robots.txt once per run
    global _robots
    if _robots is None:
        r = _session.get(f"{BASE_URL}/robots.txt", timeout=15)
        r.raise_for_status()
        _robots = Protego.parse(r.text)
    return _robots


def polite_get(url: str) -> str | None:
    """Return the HTML, or None if robots.txt disallows the path."""
    # Respect robots.txt before every single request
    if not _load_robots().can_fetch(url, USER_AGENT):
        print(f"[robots] disallowed, skipped: {url}")
        return None

    # Random pause so we never hammer the server
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    r = _session.get(url, timeout=20)

    # If the operator pushes back, stop immediately instead of working around it
    if r.status_code in (403, 429):
        raise SystemExit(f"HTTP {r.status_code}: server is blocking us. Stopping, no workarounds.")
    r.raise_for_status()
    return r.text


def save_raw(html: str, name: str) -> None:
    # Keep the raw HTML so parsing can be re-run without new requests
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (RAW_DIR / f"{stamp}_{name}.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    # First test: fetch exactly ONE page and store it for inspection
    html = polite_get(f"{BASE_URL}/")
    if html:
        save_raw(html, "startpage")
        print(f"OK, {len(html)} characters saved to {RAW_DIR}")
