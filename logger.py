"""
logger.py
---------
Centralized logging for the GNSS-IR Soil Moisture Estimation System.

Responsibilities (per project roadmap, Phase 1):
    - Record processing status (info/debug level events)
    - Record errors (with traceback where relevant)
    - Track failed stations
    - Track failed dates
    - Support large batch processing (60 stations x 365 days ~ 21,900 files)
      via per-run log files and lightweight failure registries that batch.py
      can consume to build retry lists / summary reports.

Usage:
    from logger import get_logger, log_failed_station, log_failed_date, get_failure_summary

    logger = get_logger(__name__)
    logger.info("Starting processing for station GEOM")

    try:
        ...
    except Exception as e:
        log_failed_station("GEOM", reason=str(e))
        logger.error(f"Failed to process station GEOM: {e}", exc_info=True)
"""

import logging
import logging.handlers
import os
import sys
import json
import threading
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------
# config.py is expected to define LOG_FILE and (optionally) BASE_DIR / LOG_DIR.
# We fall back to sensible defaults if config.py isn't importable yet, so this
# module can be developed and tested independently (per project philosophy).
try:
    import config
    LOG_FILE = getattr(config, "LOG_FILE", None)
    LOG_DIR = os.path.dirname(LOG_FILE) if LOG_FILE else getattr(config, "BASE_DIR", ".")
except ImportError:
    LOG_DIR = os.path.join(os.getcwd(), "logs")
    LOG_FILE = os.path.join(LOG_DIR, "gnss_ir_smc.log")

os.makedirs(LOG_DIR if LOG_DIR else ".", exist_ok=True)
if not LOG_FILE:
    LOG_FILE = os.path.join(LOG_DIR, "gnss_ir_smc.log")

FAILED_STATIONS_LOG = os.path.join(LOG_DIR, "failed_stations.jsonl")
FAILED_DATES_LOG = os.path.join(LOG_DIR, "failed_dates.jsonl")

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_lock = threading.Lock()
_configured = False


# ---------------------------------------------------------------------------
# Core setup
# ---------------------------------------------------------------------------
def _configure_root_logger(level=logging.INFO, max_bytes=10_000_000, backup_count=5):
    """Configure the root logger once: rotating file handler + console handler."""
    global _configured
    if _configured:
        return

    root = logging.getLogger("GNSS_IR_SMC")
    root.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configured = True


def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """Return a module-level logger, e.g. logger = get_logger(__name__)."""
    _configure_root_logger(level=level)
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Failure tracking (for batch processing across stations/dates)
# ---------------------------------------------------------------------------
def _append_jsonl(path: str, record: dict):
    """Thread-safe append of one JSON record per line."""
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


def log_failed_station(station: str, reason: str = "", date: str = None):
    """Register a station-level processing failure for later retry/reporting."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "station": station,
        "date": date,
        "reason": reason,
    }
    _append_jsonl(FAILED_STATIONS_LOG, record)
    get_logger("failures").warning(f"Station failure recorded: {station} ({reason})")


def log_failed_date(date: str, station: str = None, reason: str = ""):
    """Register a date-level processing failure for later retry/reporting."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": date,
        "station": station,
        "reason": reason,
    }
    _append_jsonl(FAILED_DATES_LOG, record)
    get_logger("failures").warning(f"Date failure recorded: {date} ({reason})")


def _read_jsonl(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_failure_summary() -> dict:
    """Return all recorded failures, for batch.py to build retry lists / reports."""
    return {
        "failed_stations": _read_jsonl(FAILED_STATIONS_LOG),
        "failed_dates": _read_jsonl(FAILED_DATES_LOG),
    }


def clear_failure_logs():
    """Clear failure registries at the start of a fresh batch run."""
    for path in (FAILED_STATIONS_LOG, FAILED_DATES_LOG):
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("Logger self-test: informational message")
    logger.warning("Logger self-test: warning message")
    logger.error("Logger self-test: error message")

    log_failed_station("TEST01", reason="Simulated RINEX read failure", date="2025-01-01")
    log_failed_date("2025-01-02", station="TEST01", reason="Simulated missing file")

    summary = get_failure_summary()
    logger.info(f"Failure summary: {summary}")
    print(f"\nLog file written to: {LOG_FILE}")
    print(f"Failed stations log: {FAILED_STATIONS_LOG}")
    print(f"Failed dates log: {FAILED_DATES_LOG}")