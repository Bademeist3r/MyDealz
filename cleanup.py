# Wipes all collected data irrevocably (project rule: delete after the interview)
import shutil
from config import DATA_DIR

if DATA_DIR.exists():
    shutil.rmtree(DATA_DIR)  # removes DB and raw HTML in one go
    print("All data deleted.")
else:
    print("Nothing to delete.")
