"""
discover.py

Responsible for discovering RINEX observation files
inside the GNSS_IR_smc data directory.

Expected structure:

rinex/
    station/
        year/
            month/
                day/
                    file.zip

Supports:
- RINEX 2.x
- RINEX 3.x naming
- compressed archives
"""


import os
from pathlib import Path
from datetime import datetime

from logger import get_logger
import config


logger = get_logger(__name__)


# Supported file formats
SUPPORTED_EXTENSIONS = [
    ".zip",
    ".rnx",
    ".obs",
    ".o",
    ".gz"
]


def is_rinex_file(filename):
    """
    Check whether file is a possible RINEX observation file.
    """

    filename = filename.lower()

    for ext in SUPPORTED_EXTENSIONS:
        if filename.endswith(ext):
            return True

    return False



def extract_station_from_path(path):
    """
    Extract station name from folder structure.

    Example:

    rinex/GEOM/2025/01/01/file.zip

    returns:

    GEOM
    """

    parts = Path(path).parts

    try:
        rinex_index = parts.index("rinex")
        station = parts[rinex_index + 1]

        return station.upper()

    except Exception:

        return "UNKNOWN"



def extract_date_from_path(path):
    """
    Extract date from folder structure.

    Expected:

    station/year/month/day/file

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

    except Exception:

        return None



def discover_rinex_files(root_folder=None):

    """
    Scan the RINEX directory recursively.

    Returns:

    [
        {
        station:
        date:
        path:
        }
    ]

    """

    if root_folder is None:
        root_folder = config.RINEX_ROOT


    logger.info(
        f"Searching RINEX directory: {root_folder}"
    )


    discovered = []


    for root, directories, files in os.walk(root_folder):

        for file in files:

            if is_rinex_file(file):

                full_path = os.path.join(
                    root,
                    file
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

                    "path": full_path

                }


                discovered.append(record)



                logger.info(
                    f"Found {station}: {file}"
                )



    logger.info(
        f"Total RINEX files discovered: {len(discovered)}"
    )


    return discovered



if __name__ == "__main__":


    files = discover_rinex_files()


    print("\nDISCOVERED FILES")
    print("----------------")


    for item in files[:10]:

        print(item)