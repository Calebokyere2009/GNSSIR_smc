
"""
discover.py

Responsible for discovering RINEX observation files
inside the GNSS_IR_smc data directory.

Expected structure:

data/rinex/
    station/
        year/
            month/
                day/
                    observation_file

Example:

data/rinex/GEOM/2025/01/01/GEOM0010.25o.zip

Supports:
- RINEX 2.x
- RINEX 3.x
- ZIP archives
- RINEX observation files
- GZIP-compressed files
"""

import os
from pathlib import Path
from datetime import datetime

import config
from logger import get_logger


logger = get_logger(__name__)


# ============================================================
# SUPPORTED FILE FORMATS
# ============================================================

SUPPORTED_EXTENSIONS = (
    ".zip",
    ".rnx",
    ".obs",
    ".o",
    ".gz",
)


# ============================================================
# FILE IDENTIFICATION
# ============================================================

def is_rinex_file(filename):
    """
    Determine whether a filename has a supported RINEX-related
    extension.
    """

    filename = filename.lower()

    return filename.endswith(SUPPORTED_EXTENSIONS)


# ============================================================
# STATION IDENTIFICATION
# ============================================================

def extract_station_from_path(path):
    """
    Extract the station name from the expected directory structure.

    Expected:

    data/rinex/GEOM/2025/01/01/file.zip

    Returns:

    GEOM
    """

    parts = Path(path).parts

    try:
        rinex_index = parts.index("rinex")

        station_index = rinex_index + 1

        station = parts[station_index]

        return station.upper()

    except (ValueError, IndexError):

        logger.warning(
            f"Could not determine station from path: {path}"
        )

        return "UNKNOWN"


# ============================================================
# DATE IDENTIFICATION
# ============================================================

def extract_date_from_path(path):
    """
    Extract the observation date from the directory structure.

    Expected:

    data/rinex/STATION/YEAR/MONTH/DAY/file.zip

    Example:

    data/rinex/GEOM/2025/01/01/GEOM0010.25o.zip

    Returns:

    datetime(2025, 1, 1)

    If the date cannot be determined, returns None.
    """

    parts = Path(path).parts

    try:
        rinex_index = parts.index("rinex")

        year = int(parts[rinex_index + 2])
        month = int(parts[rinex_index + 3])
        day = int(parts[rinex_index + 4])

        return datetime(
            year,
            month,
            day
        )

    except (ValueError, IndexError):

        logger.warning(
            f"Could not determine date from path: {path}"
        )

        return None


# ============================================================
# RINEX DISCOVERY
# ============================================================

def discover_rinex_files(root_folder=None):
    """
    Recursively search the RINEX directory.

    Parameters
    ----------
    root_folder : str or None
        Root directory containing the station folders.

        If None, RINEX_ROOT from config.py is used.

    Returns
    -------
    list of dict

        Each discovered file is represented as:

        {
            "station": "GEOM",
            "date": datetime(2025, 1, 1),
            "path": "/full/path/to/file.zip"
        }
    """

    if root_folder is None:
        root_folder = config.RINEX_DIR

    root_folder = os.path.abspath(root_folder)

    logger.info(
        f"Searching RINEX directory: {root_folder}"
    )

    if not os.path.exists(root_folder):

        logger.error(
            f"RINEX directory does not exist: {root_folder}"
        )

        return []

    discovered = []

    for root, directories, files in os.walk(root_folder):

        for filename in files:

            if not is_rinex_file(filename):
                continue

            full_path = os.path.join(
                root,
                filename
            )

            station = extract_station_from_path(
                full_path
            )

            date = extract_date_from_path(
                full_path
            )

            record = {
                "station": station,
                "date": date,
                "path": full_path,
            }

            discovered.append(record)

            logger.info(
                f"Found RINEX file | "
                f"Station: {station} | "
                f"Date: {date} | "
                f"File: {filename}"
            )

    logger.info(
        f"Total RINEX files discovered: {len(discovered)}"
    )

    return discovered


# ============================================================
# SUMMARY
# ============================================================

def summarize_discovery(files):
    """
    Produce a simple summary of discovered RINEX files.

    Returns
    -------
    dict

        {
            "total_files": ...,
            "stations": [...],
            "station_count": ...,
            "valid_dates": ...
        }
    """

    stations = sorted(
        {
            item["station"]
            for item in files
            if item["station"] != "UNKNOWN"
        }
    )

    valid_dates = [
        item["date"]
        for item in files
        if item["date"] is not None
    ]

    return {
        "total_files": len(files),
        "stations": stations,
        "station_count": len(stations),
        "valid_dates": len(valid_dates),
    }


# ============================================================
# TEST / COMMAND-LINE EXECUTION
# ============================================================

if __name__ == "__main__":

    files = discover_rinex_files()

    summary = summarize_discovery(files)

    print("\n")
    print("=" * 60)
    print("RINEX DISCOVERY RESULTS")
    print("=" * 60)

    print(
        f"Total files discovered: "
        f"{summary['total_files']}"
    )

    print(
        f"Number of stations: "
        f"{summary['station_count']}"
    )

    print(
        f"Files with valid dates: "
        f"{summary['valid_dates']}"
    )

    print("\nStations:")

    for station in summary["stations"]:
        print(f"  - {station}")

    print("\nFirst 10 discovered files:")
    print("-" * 60)

    for item in files[:10]:

        print(
            f"Station: {item['station']} | "
            f"Date: {item['date']} | "
            f"File: {item['path']}"
        )

    print("=" * 60)