import logging
from logging.handlers import RotatingFileHandler
from kjc_cli import config

LOG_FILE = config.DATA_DIR / "reports" / "kjc.log"

def get_logger(name="kjc"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, config._cfg.get("logging", {}).get("level", "INFO")))
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger
