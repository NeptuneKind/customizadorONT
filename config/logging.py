# ===================================================================
# Imports
# ===================================================================
import logging
import sys
from pathlib import Path
from typing import Optional

# ===================================================================
# Métodos para logging
# ===================================================================
def setup_logging(*, debug: bool, logs_dir: Path) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=level,
        # format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
        format="[%(levelname)s][%(name)s] %(message)s",
        handlers=handlers,
    )


def get_logger(tag: str) -> logging.Logger:
    # tag should be like "SELENIUM", "CUSTOM", "PING", "UI"
    return logging.getLogger(tag)