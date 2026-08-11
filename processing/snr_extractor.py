"""
snr_extractor.py
================

SNR extraction and organization for the GNSS-IR Soil Moisture
Estimation System.

Responsibilities
----------------
1. Identify SNR observables available in a RINEX dataset.
2. Identify GNSS constellation and signal/frequency where possible.
3. Select an appropriate SNR observable for GNSS-IR processing.
4. Preserve observation time and satellite identifiers.
5. Return a standardized SNR dataset for later quality control.

This module does NOT:
    - detrend SNR
    - estimate reflector height
    - estimate soil moisture
    - compare against SMAP
    - compare against CYGNSS

Those operations belong to later modules.

Scientific principle
--------------------
Raw SNR should be preserved during extraction. No filtering,
interpolation, smoothing, detrending, or normalization is
performed here.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from logger import get_logger


logger = get_logger(__name__)


# ============================================================
# GNSS CONSTELLATION IDENTIFICATION
# ============================================================

CONSTELLATION_NAMES = {
    "G": "GPS",
    "R": "GLONASS",
    "E": "Galileo",
    "C": "BeiDou",
    "J": "QZSS",
    "I": "IRNSS",
    "S": "SBAS",
}


def identify_constellation(satellite):
    """
    Identify the GNSS constellation from a satellite identifier.

    Examples
    --------
    G05 -> GPS
    R12 -> GLONASS
    E19 -> Galileo
    C07 -> BeiDou
    """

    satellite = str(satellite).strip().upper()

    if not satellite:
        return "UNKNOWN"

    prefix = satellite[0]

    return CONSTELLATION_NAMES.get(
        prefix,
        "UNKNOWN"
    )


# ============================================================
# FREQUENCY IDENTIFICATION
# ============================================================

def identify_frequency(observable):
    """
    Identify the GNSS frequency band from an RINEX observation
    code.

    Examples
    --------
    S1C -> L1
    S1 -> L1
    S2W -> L2
    S5Q -> L5

    The function intentionally does not infer a physical
    frequency from an unsupported or ambiguous observation code.
    """

    observable = str(
        observable
    ).upper().strip()

    if not observable.startswith("S"):
        return None

    if len(observable) < 2:
        return None

    frequency_number = observable[1]

    frequency_map = {
        "1": "L1",
        "2": "L2",
        "5": "L5",
        "6": "L6",
        "7": "L7",
        "8": "L8",
    }

    return frequency_map.get(
        frequency_number
    )


# ============================================================
# OBSERVABLE INFORMATION
# ============================================================

def describe_observable(observable):
    """
    Return metadata describing an SNR observable.
    """

    observable = str(
        observable
    ).upper().strip()

    return {
        "observable": observable,
        "frequency": identify_frequency(
            observable
        ),
    }


# ============================================================
# AVAILABLE SNR VARIABLES
# ============================================================

def find_snr_variables(dataset):
    """
    Find SNR observables in an xarray Dataset.

    RINEX 3 observables may look like:

        S1C
        S1W
        S2W
        S5Q

    RINEX 2 observables may appear as:

        S1
        S2
        S5

    The function searches the actual variables present in
    the dataset instead of assuming a fixed naming scheme.
    """

    snr_variables = []

    for variable in dataset.data_vars:

        name = str(
            variable
        ).upper().strip()

        if name.startswith("S"):

            snr_variables.append(
                str(variable)
            )

    return sorted(
        snr_variables
    )


# ============================================================
# PRIORITY RULES
# ============================================================

def rank_snr_observable(observable):
    """
    Rank SNR observables for GNSS-IR processing.

    Lower score = higher priority.

    L1 is preferred because the initial GNSS-IR implementation
    is based on the GPS L1 wavelength.

    This ranking is a selection preference, NOT a statement that
    other frequencies are scientifically invalid.
    """

    name = str(
        observable
    ).upper().strip()

    frequency = identify_frequency(
        name
    )

    # Prefer L1.
    if frequency == "L1":
        return 1

    # Then L2.
    if frequency == "L2":
        return 2

    # Then L5.
    if frequency == "L5":
        return 3

    # Other frequencies.
    return 99


def select_preferred_snr_variable(
    dataset,
    preferred_frequency="L1"
):
    """
    Select the preferred SNR observable.

    Parameters
    ----------
    dataset : xarray.Dataset
        RINEX dataset.

    preferred_frequency : str
        Preferred frequency, normally L1 for the first
        GNSS-IR implementation.

    Returns
    -------
    str or None
        Name of selected SNR observable.
    """

    variables = find_snr_variables(
        dataset
    )

    if not variables:
        return None

    preferred_frequency = (
        preferred_frequency.upper()
    )

    preferred = [
        variable
        for variable in variables
        if identify_frequency(
            variable
        ) == preferred_frequency
    ]

    if preferred:

        preferred.sort(
            key=rank_snr_observable
        )

        return preferred[0]

    # Fall back to the highest-ranked
    # available SNR observable.
    variables.sort(
        key=rank_snr_observable
    )

    return variables[0]


# ============================================================
# EXTRACT ONE SNR OBSERVABLE
# ============================================================

def extract_observable(
    dataset,
    observable
):
    """
    Extract one SNR observable from an xarray Dataset.

    The returned dataset retains the original time and satellite
    dimensions.
    """

    if observable not in dataset.data_vars:

        raise KeyError(
            f"SNR observable '{observable}' "
            f"not found in dataset."
        )

    return dataset[
        [observable]
    ]


# ============================================================
# CONVERT TO TABULAR FORM
# ============================================================

def snr_to_dataframe(
    dataset,
    observable
):
    """
    Convert a selected SNR observable into a pandas DataFrame.

    Output columns:

        time
        satellite
        snr
        constellation
        frequency

    Missing/invalid SNR values are retained initially so that
    later quality-control procedures can decide how to treat them.
    """

    if observable not in dataset.data_vars:

        raise KeyError(
            f"Observable '{observable}' "
            f"not found."
        )

    data_array = dataset[
        observable
    ]

    dataframe = (
        data_array
        .to_dataframe(
            name="snr"
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Standardize satellite column.
    # --------------------------------------------------------

    if "sv" in dataframe.columns:

        dataframe.rename(
            columns={
                "sv": "satellite"
            },
            inplace=True
        )

    elif "satellite" not in dataframe.columns:

        dataframe["satellite"] = (
            "UNKNOWN"
        )

    # --------------------------------------------------------
    # Standardize time column.
    # --------------------------------------------------------

    if "time" not in dataframe.columns:

        dataframe["time"] = pd.NaT

    # --------------------------------------------------------
    # Add constellation.
    # --------------------------------------------------------

    dataframe[
        "constellation"
    ] = dataframe[
        "satellite"
    ].apply(
        identify_constellation
    )

    # --------------------------------------------------------
    # Add frequency.
    # --------------------------------------------------------

    dataframe[
        "frequency"
    ] = identify_frequency(
        observable
    )

    # --------------------------------------------------------
    # Record observable.
    # --------------------------------------------------------

    dataframe[
        "observable"
    ] = observable

    # --------------------------------------------------------
    # Ensure SNR is numeric.
    # --------------------------------------------------------

    dataframe[
        "snr"
    ] = pd.to_numeric(
        dataframe["snr"],
        errors="coerce"
    )

    return dataframe


# ============================================================
# BASIC SNR INFORMATION
# ============================================================

def summarize_snr_dataframe(
    dataframe
):
    """
    Produce descriptive statistics for extracted SNR data.

    This function is diagnostic only.

    It does not perform quality control.
    """

    if dataframe is None:
        return {}

    if dataframe.empty:
        return {
            "records": 0
        }

    snr = dataframe[
        "snr"
    ].dropna()

    summary = {
        "records": int(
            len(dataframe)
        ),
        "valid_snr": int(
            len(snr)
        ),
        "missing_snr": int(
            len(dataframe) - len(snr)
        ),
    }

    if len(snr) > 0:

        summary.update({
            "minimum": float(
                snr.min()
            ),
            "maximum": float(
                snr.max()
            ),
            "mean": float(
                snr.mean()
            ),
            "median": float(
                snr.median()
            ),
            "std": float(
                snr.std()
            ),
        })

    return summary


# ============================================================
# COMPLETE EXTRACTION
# ============================================================

def extract_snr(
    dataset,
    preferred_frequency="L1"
):
    """
    Main SNR extraction interface.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset returned by rinex_reader.py.

    preferred_frequency : str
        Preferred GNSS frequency.

    Returns
    -------
    dict
        Structured extraction result.
    """

    logger.info(
        "Starting SNR extraction."
    )

    available = find_snr_variables(
        dataset
    )

    logger.info(
        f"Available SNR observables: "
        f"{available}"
    )

    if not available:

        logger.warning(
            "No SNR observables available."
        )

        return {
            "selected_observable": None,
            "frequency": None,
            "dataframe": pd.DataFrame(),
            "summary": {
                "records": 0
            },
            "available_observables": [],
        }

    selected = (
        select_preferred_snr_variable(
            dataset,
            preferred_frequency
        )
    )

    logger.info(
        f"Selected SNR observable: "
        f"{selected}"
    )

    dataframe = snr_to_dataframe(
        dataset,
        selected
    )

    summary = summarize_snr_dataframe(
        dataframe
    )

    logger.info(
        "SNR extraction completed | "
        f"Observable: {selected} | "
        f"Records: {summary.get('records', 0)}"
    )

    return {
        "selected_observable": selected,
        "frequency": identify_frequency(
            selected
        ),
        "dataframe": dataframe,
        "summary": summary,
        "available_observables": available,
    }


# ============================================================
# SAVE RAW EXTRACTED SNR
# ============================================================

def save_snr_csv(
    dataframe,
    output_path
):
    """
    Save extracted SNR observations to CSV.

    This is an intermediate product and should not be confused
    with the final soil-moisture result.
    """

    if dataframe is None:

        raise ValueError(
            "No SNR dataframe supplied."
        )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    dataframe.to_csv(
        output_path,
        index=False
    )

    logger.info(
        f"SNR data saved: {output_path}"
    )


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("SNR EXTRACTOR TEST")
    print("=" * 60)

    print(
        "\nSNR extractor module loaded successfully."
    )

    print(
        "\nNo RINEX dataset is currently available."
    )

    print(
        "The module will be tested with actual RINEX "
        "observations when the data are supplied."
    )

    print("=" * 60)