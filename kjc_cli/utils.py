import json
from pathlib import Path
from kjc_cli import config

def save_json(dest: Path, obj):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
