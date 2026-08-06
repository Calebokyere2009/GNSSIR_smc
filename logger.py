"""
logger.py

Central logging system for the GNSS-IR Soil Moisture Project.

All modules should import this logger instead of using print().
"""

import logging
import os

from config import LOG_FILE


# Create log directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def get_logger(name: str):
    """
    Returns a configured logger.

    Parameters
    ----------
    name : str
        Usually __name__

    Returns
    -------
    logging.Logger
    """

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File output
    file_handler = logging.FileHandler(LOG_FILE)

    file_handler.setFormatter(formatter)

    # Terminal output
    console_handler = logging.StreamHandler()

    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    logger.addHandler(console_handler)

    return logger