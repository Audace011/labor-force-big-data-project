"""
Shared logging configuration. Every script imports get_logger()
instead of using print() (assignment requirement 4.1).
"""
import logging
import os
from src.config import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        # avoid adding duplicate handlers if called multiple times
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (one shared pipeline.log, easy to include in your report)
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
