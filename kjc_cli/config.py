import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()  # read .env

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# Load YAML config
CFG_FILE = BASE_DIR / "config.yaml"
if CFG_FILE.exists():
    with open(CFG_FILE, "r") as fh:
        _cfg = yaml.safe_load(fh)
else:
    _cfg = {}

# Env-aware paths
BACKGROUND_DIR = Path(os.getenv("BACKGROUND_DIR", str(DATA_DIR / "backgrounds")))
HOOKS_DIR = Path(os.getenv("HOOKS_DIR", str(DATA_DIR / "hooks")))
COMPOSED_DIR = Path(os.getenv("COMPOSED_DIR", str(DATA_DIR / "composed")))
PRODUCTS_DIR = Path(os.getenv("PRODUCTS_DIR", str(DATA_DIR / "products")))

# Ensure directories exist
for p in (BACKGROUND_DIR, HOOKS_DIR, COMPOSED_DIR, PRODUCTS_DIR, DATA_DIR / "reports"):
    p.mkdir(parents=True, exist_ok=True)

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# Scheduler
SCHEDULE_CRON = os.getenv("SCHEDULE_CRON", "0 * * * *")  # hourly by default
POSTS_PER_DAY = int(os.getenv("DEFAULT_POSTS_PER_DAY", _cfg.get("posts", {}).get("posts_per_day", 10)))

# image compose defaults
IMAGE_CFG = _cfg.get("image", {})
FONT_PATH = IMAGE_CFG.get("default_font", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_SIZE = IMAGE_CFG.get("font_size", 48)
COMPOSED_WIDTH = IMAGE_CFG.get("composed_width", 1200)
COMPOSED_HEIGHT = IMAGE_CFG.get("composed_height", 1200)
