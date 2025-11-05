from datetime import datetime
from kjc_cli.logger import get_logger
from kjc_cli import config
from pathlib import Path

logger = get_logger("monitor")
LOGFILE = config.DATA_DIR / "reports" / "events.log"

def log_event(msg, status="INFO"):
    entry = f"{datetime.utcnow().isoformat()}Z\t{status}\t{msg}\n"
    Path(LOGFILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(entry)
    logger.info(f"MONITOR: {status} - {msg}")
