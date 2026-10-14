# Central settings for the Mydealz demo project
from pathlib import Path

BASE_URL = "https://www.mydealz.de"

# Be honest about who we are; put a real contact address here
USER_AGENT = "ErikDemoBot/0.1 (private demo project, contact: YOUR@MAIL.DE)"

# Polite crawling: random pause between requests (seconds)
MIN_DELAY, MAX_DELAY = 5, 10

# Hard cap per run, keeps every snapshot small
MAX_REQUESTS_PER_RUN = 12

# Listing pages to fetch: (path, category label or None, number of pages)
# Deal cards do not show a category, so group pages give it to us
GROUPS = ["elektronik", "gaming", "home-living", "fashion-accessoires", "sport", "food"]
TARGETS = [
    ("/", None, 2),      # "Beliebt"
    ("/new", None, 3),   # "Alles", newest first
] + [(f"/gruppe/{g}", g, 1) for g in GROUPS]

# Local storage paths
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "mydealz.db"
