"""Console and file logging for pipeline runs."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_path: Path, run_id: str) -> logging.Logger:
    logger = logging.getLogger("dataforge")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.info("Logging started for run_id=%s", run_id)
    return logger
