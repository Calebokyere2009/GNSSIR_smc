"""
GNSS-IR Soil Moisture Estimation System

Configuration File

This file contains:
- Project paths
- GNSS constants
- Signal processing parameters
- Quality control thresholds
- Validation settings
"""

import os


# ==========================================================
# PROJECT DIRECTORIES
# ==========================================================

# Root project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Data directories

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)


RINEX_DIR = os.path.join(
    DATA_DIR,
    "rinex"
)


SMAP_DIR = os.path.join(
    DATA_DIR,
    "smap"
)

CYGNSS_DIR = os.path.join(
    DATA_DIR,
    "cygnss"
)


METADATA_DIR = os.path.join(
    DATA_DIR,
    "metadata"
)

# We delete the unwanted files after using
TEMP_DIR = os.path.join(
    BASE_DIR,
    "temp"
)



# Results

RESULTS_DIR = os.path.join(
    BASE_DIR,
    "results"
)


INTERMEDIATE_RESULTS = os.path.join(
    RESULTS_DIR,
    "intermediate"
)


FINAL_RESULTS = os.path.join(
    RESULTS_DIR,
    "final"
)



# ==========================================================
# GNSS CONSTANTS
# ==========================================================

# GPS L1 frequency wavelength
# λ = c/f

L1_WAVELENGTH = 0.1902936728  # metres


# Speed of light

SPEED_OF_LIGHT = 299792458  # m/s



# ==========================================================
# GNSS-IR PROCESSING SETTINGS
# ==========================================================


# Elevation angle range used for reflected signals

MIN_ELEVATION = 5     # degrees

MAX_ELEVATION = 35    # degrees



# Reflector height search range

MIN_REFLECTOR_HEIGHT = 0.5   # metres

MAX_REFLECTOR_HEIGHT = 10.0  # metres



# Lomb-Scargle frequency resolution

LS_FREQUENCY_POINTS = 2000



# ==========================================================
# SNR PROCESSING
# ==========================================================


# Minimum acceptable signal strength

MIN_SNR = 20  # dB-Hz


# Minimum observations required
# before estimating moisture

MIN_OBSERVATIONS = 50



# ==========================================================
# QUALITY CONTROL PARAMETERS
# ==========================================================


# Minimum Lomb-Scargle peak strength

MIN_PEAK_RATIO = 3.0



# Reject unrealistic reflector heights

MAX_HEIGHT_ERROR = 0.5  # metres



# ==========================================================
# SOIL MOISTURE MODEL SETTINGS
# ==========================================================


# Default soil texture
# Can later be replaced by soil maps

DEFAULT_SAND_PERCENT = 40

DEFAULT_CLAY_PERCENT = 20



# Soil moisture physical limits

MIN_SOIL_MOISTURE = 0.0

MAX_SOIL_MOISTURE = 0.6
# volumetric fraction (m3/m3)



# ==========================================================
# SMAP VALIDATION SETTINGS
# ==========================================================


# Maximum time difference allowed

SMAP_TIME_WINDOW_HOURS = 3



# Spatial matching radius

SMAP_MATCH_RADIUS_KM = 5



# ==========================================================
# BATCH PROCESSING
# ==========================================================


# Number of parallel workers

MAX_WORKERS = 4



# ==========================================================
# LOGGING
# ==========================================================

LOG_FILE = os.path.join(
    BASE_DIR,
    "logs",
    "processing.log"
)

# ==========================================================
# RINEX DATA STRUCTURE
# ==========================================================

# data/rinex/
#     STATION/
#         YEAR/
#             MONTH/
#                 DAY/
#                     file.zip


SUPPORTED_RINEX_EXTENSIONS = [
    ".zip",
    ".obs",
    ".rnx",
    ".o",
    ".gz"
]


RINEX_YEAR_FORMAT = "%Y"

RINEX_MONTH_FORMAT = "%m"

RINEX_DAY_FORMAT = "%d"