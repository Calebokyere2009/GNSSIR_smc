"""
rinex_reader.py
===============

RINEX observation reader for the GNSS-IR Soil Moisture
Estimation System.

Responsibilities
----------------
1. Open RINEX 2.x and RINEX 3.x observation files.
2. Read the RINEX header.
3. Identify available observation types.
4. Identify satellites and epochs.
5. Extract SNR-related observables.
6. Return a standardized structure for downstream processing.

This module does NOT:
    - estimate reflector height
    - estimate soil moisture
    - perform SMAP validation
    - perform CYGNSS validation

Those operations belong to later modules.

Scientific principle
--------------------
The reader must preserve the original observation information.
It should not modify, interpolate, detrend, smooth, or otherwise
alter the SNR data. Those operations belong to the later
GNSS-IR processing and quality-control stages.
"""

from pathlib import Path
import tempfile
import zipfile
import gzip
import shutil

import numpy as np

from logger import get_logger

try:
    import georinex as gr
except ImportError:
    gr = None


logger = get_logger(__name__)


# ============================================================
# DEPENDENCY CHECK
# ============================================================

def check_georinex():
    """
    Confirm that GeoRinex is available.

    Returns
    -------
    bool
        True if GeoRinex is installed.
    """

    if gr is None:

        logger.error(
            "GeoRinex is not installed. "
            "Install it with: pip install georinex"
        )

        return False

    return True


# ============================================================
# ARCHIVE EXTRACTION
# ============================================================

def extract_zip_temporarily(zip_path):
    """
    Extract a ZIP archive into a temporary directory.

    The temporary directory is automatically removed by the
    caller after processing.

    This prevents permanent extraction of thousands of RINEX
    files and therefore reduces storage requirements.
    """

    temp_dir = tempfile.mkdtemp(
        prefix="gnss_ir_rinex_"
    )

    try:

        with zipfile.ZipFile(zip_path, "r") as archive:

            archive.extractall(temp_dir)

    except Exception:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise

    return Path(temp_dir)


# ============================================================
# FIND OBSERVATION FILE
# ============================================================

def find_observation_file(directory):
    """
    Find a RINEX observation file inside an extracted archive.

    Supports common RINEX observation extensions.
    """

    candidates = []

    for path in Path(directory).rglob("*"):

        if not path.is_file():
            continue

        name = path.name.lower()

        if (
            name.endswith(".rnx")
            or name.endswith(".obs")
            or name.endswith(".o")
        ):
            candidates.append(path)

    if not candidates:
        return None

    # Prefer .rnx and .obs where available.
    candidates.sort(
        key=lambda p: (
            0 if p.suffix.lower() == ".rnx" else
            1 if p.suffix.lower() == ".obs" else
            2,
            str(p)
        )
    )

    return candidates[0]


# ============================================================
# OBSERVATION FILE RESOLUTION
# ============================================================

def resolve_observation_file(file_path):
    """
    Resolve an input path into an actual RINEX observation file.

    Supported:
        .rnx
        .obs
        .o
        .zip
        .gz

    Returns
    -------
    tuple
        (observation_path, temporary_directory)
    """

    file_path = Path(file_path)

    if not file_path.exists():

        raise FileNotFoundError(
            f"RINEX file does not exist: {file_path}"
        )

    suffix = file_path.suffix.lower()

    # --------------------------------------------------------
    # Uncompressed RINEX
    # --------------------------------------------------------

    if suffix in [".rnx", ".obs", ".o"]:

        return file_path, None

    # --------------------------------------------------------
    # ZIP archive
    # --------------------------------------------------------

    if suffix == ".zip":

        temp_dir = extract_zip_temporarily(
            file_path
        )

        observation_file = find_observation_file(
            temp_dir
        )

        if observation_file is None:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            raise ValueError(
                f"No RINEX observation file found "
                f"inside {file_path}"
            )

        return observation_file, temp_dir

    # --------------------------------------------------------
    # GZIP
    # --------------------------------------------------------

    if suffix == ".gz":

        temp_dir = Path(
            tempfile.mkdtemp(
                prefix="gnss_ir_rinex_"
            )
        )

        output_name = file_path.name[:-3]

        output_path = (
            temp_dir / output_name
        )

        try:

            with gzip.open(
                file_path,
                "rb"
            ) as source:

                with open(
                    output_path,
                    "wb"
                ) as destination:

                    shutil.copyfileobj(
                        source,
                        destination
                    )

        except Exception:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            raise

        return output_path, temp_dir

    raise ValueError(
        f"Unsupported RINEX file format: {file_path}"
    )


# ============================================================
# READ RINEX
# ============================================================

def read_rinex(file_path):
    """
    Read a RINEX observation file using GeoRinex.

    Parameters
    ----------
    file_path : str or Path
        Path to RINEX file or compressed archive.

    Returns
    -------
    xarray.Dataset

    Notes
    -----
    The returned dataset is preserved in its original
    observation form. No SNR filtering or GNSS-IR processing
    is performed here.
    """

    if not check_georinex():

        raise ImportError(
            "GeoRinex is required to read RINEX files."
        )

    observation_path = None
    temp_dir = None

    try:

        observation_path, temp_dir = (
            resolve_observation_file(
                file_path
            )
        )

        logger.info(
            f"Reading RINEX observation file: "
            f"{observation_path}"
        )

        dataset = gr.load(
            str(observation_path)
        )

        logger.info(
            f"Successfully loaded RINEX: "
            f"{observation_path.name}"
        )

        return dataset

    finally:

        # Remove temporary extraction directory.
        if temp_dir is not None:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )


# ============================================================
# HEADER / METADATA SUMMARY
# ============================================================

def get_rinex_summary(dataset):
    """
    Extract a compact metadata summary from a GeoRinex dataset.
    """

    summary = {
        "dimensions": {},
        "variables": [],
        "satellites": [],
        "epochs": 0,
    }

    # Dimensions
    for name, size in dataset.sizes.items():

        summary["dimensions"][name] = int(size)

    # Variables
    summary["variables"] = list(
        dataset.data_vars
    )

    # Satellites
    if "sv" in dataset.coords:

        summary["satellites"] = [
            str(satellite)
            for satellite in dataset.coords["sv"].values
        ]

    # Epochs
    if "time" in dataset.coords:

        summary["epochs"] = int(
            dataset.coords["time"].size
        )

    return summary


# ============================================================
# SNR OBSERVATION IDENTIFICATION
# ============================================================

def identify_snr_observables(dataset):
    """
    Identify SNR-related observables available in the RINEX file.

    RINEX observation naming differs between RINEX versions and
    constellations.

    Examples include:

        S1
        S2
        S5

    and constellation-specific forms such as:

        S1C
        S2W
        S5Q

    The function does not assume that a particular signal exists.
    """

    snr_variables = []

    for variable in dataset.data_vars:

        name = str(variable).upper()

        if name.startswith("S"):

            snr_variables.append(
                str(variable)
            )

    return sorted(
        snr_variables
    )


# ============================================================
# EXTRACT SNR DATASET
# ============================================================

def extract_snr(dataset):
    """
    Extract all available SNR observables.

    Returns
    -------
    xarray.Dataset
        Dataset containing only SNR-related variables.
    """

    snr_variables = (
        identify_snr_observables(
            dataset
        )
    )

    if not snr_variables:

        logger.warning(
            "No SNR observables were found "
            "in the RINEX dataset."
        )

        return None

    logger.info(
        f"SNR observables found: "
        f"{', '.join(snr_variables)}"
    )

    return dataset[
        snr_variables
    ]


# ============================================================
# BASIC DATA QUALITY SUMMARY
# ============================================================

def summarize_snr(snr_dataset):
    """
    Generate basic descriptive information about SNR data.

    This is NOT the final quality-control stage.

    It only helps us inspect what has been read.
    """

    if snr_dataset is None:

        return {}

    summary = {}

    for variable in snr_dataset.data_vars:

        data = (
            snr_dataset[variable]
            .values
        )

        finite = data[
            np.isfinite(data)
        ]

        if finite.size == 0:

            summary[str(variable)] = {
                "valid_count": 0,
                "minimum": None,
                "maximum": None,
                "mean": None,
                "std": None,
            }

            continue

        summary[str(variable)] = {
            "valid_count": int(
                finite.size
            ),
            "minimum": float(
                np.min(finite)
            ),
            "maximum": float(
                np.max(finite)
            ),
            "mean": float(
                np.mean(finite)
            ),
            "std": float(
                np.std(finite)
            ),
        }

    return summary


# ============================================================
# COMPLETE READING PIPELINE
# ============================================================

def inspect_rinex(file_path):
    """
    Read and inspect a RINEX observation file.

    This function provides the interface that future modules
    can use.

    Returns
    -------
    dict
        Contains the dataset, summary and SNR information.
    """

    logger.info(
        f"Beginning RINEX inspection: {file_path}"
    )

    dataset = read_rinex(
        file_path
    )

    summary = get_rinex_summary(
        dataset
    )

    snr_dataset = extract_snr(
        dataset
    )

    snr_summary = summarize_snr(
        snr_dataset
    )

    result = {
        "dataset": dataset,
        "summary": summary,
        "snr_dataset": snr_dataset,
        "snr_summary": snr_summary,
    }

    logger.info(
        f"RINEX inspection complete: "
        f"{file_path}"
    )

    return result


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("RINEX READER TEST")
    print("=" * 60)

    if gr is None:

        print(
            "\nGeoRinex is not installed."
        )

        print(
            "Install it using:"
        )

        print(
            "pip install georinex"
        )

    else:

        print(
            "\nGeoRinex is installed successfully."
        )

        print(
            "RINEX reader module loaded successfully."
        )

    print("=" * 60)