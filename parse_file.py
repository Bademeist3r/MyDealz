# Re-runs the parser on a saved raw page, no new request needed.
# Usage: python parse_file.py [path/to/file.html]
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from parse import parse_listing

# Default: newest file in data/raw
path = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(Path("data/raw").glob("*.html"))[-1]

# Relative ages ("vor 5 Min.") must be read against the fetch time stored in the file name
m = re.match(r"(\d{8}T\d{6})Z", path.name)
now = (datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
       if m else datetime.now(timezone.utc))

deals = parse_listing(path.read_text(encoding="utf-8"), now)
print(f"{path}: {len(deals)} deals (reference time {now.isoformat(timespec='seconds')})")
for d in deals[:5]:
    print(d)
