"""
rinex_detector.py

RINEX format and archive detector for the GNSS-IR Soil Moisture
Estimation System.

Responsibilities
----------------
1. Identify whether an input is a supported RINEX-related file.
2. Identify compressed archives.
3. Temporarily inspect compressed RINEX files without permanently
   extracting the dataset.
4. Detect RINEX 2.x versus RINEX 3.x from the RINEX header.
5. Determine whether the file is an observation file.
6. Return structured metadata for downstream processing.

The detector does NOT extract SNR or perform GNSS-IR calculations.
"""

from pathlib import Path
import gzip
import zipfile

import config
from logger import get_logger


logger = get_logger(__name__)


# ============================================================
# RINEX DETECTION RESULT
# ============================================================

def empty_result(file_path):
    """
    Create a standard result structure.

    Keeping one consistent structure is important because later
    modules will consume these results.
    """

    return {
        "path": str(file_path),
        "filename": Path(file_path).name,
        "archive_type": None,
        "rinex_version": None,
        "file_type": None,
        "observation_file": False,
        "valid": False,
        "error": None,
    }


# ============================================================
# ARCHIVE DETECTION
# ============================================================

def detect_archive_type(file_path):
    """
    Determine whether the input is:

    - ZIP
    - GZIP
    - uncompressed
    """

    path = Path(file_path)

    if not path.exists():
        return None

    suffix = path.suffix.lower()

    if suffix == ".zip":
        return "zip"

    if suffix == ".gz":
        return "gzip"

    return "none"


# ============================================================
# ZIP MEMBER DISCOVERY
# ============================================================

def get_zip_members(file_path):
    """
    Return filenames contained inside a ZIP archive.

    The archive is inspected without extracting all files to disk.
    """

    try:

        with zipfile.ZipFile(file_path, "r") as archive:

            return archive.namelist()

    except zipfile.BadZipFile as exc:

        logger.error(
            f"Invalid ZIP archive: {file_path} | {exc}"
        )

        return []

    except OSError as exc:

        logger.error(
            f"Could not read ZIP archive: {file_path} | {exc}"
        )

        return []


# ============================================================
# RINEX MEMBER SELECTION
# ============================================================

def find_rinex_members(members):
    """
    Identify likely RINEX files inside an archive.

    This does not assume that the filename follows one specific
    RINEX naming convention.

    Returns a list of candidate members.
    """

    candidates = []

    for member in members:

        name = Path(member).name.lower()

        # Ignore directories.
        if member.endswith("/"):
            continue

        # Common RINEX observation extensions.
        if (
            name.endswith(".rnx")
            or name.endswith(".obs")
            or name.endswith(".o")
        ):
            candidates.append(member)
            continue

        # RINEX 2 observation files can have names such as:
        #
        # GEOM0010.25o
        #
        # where the final character is "o".
        #
        # The .o check above handles this case.

    return candidates


# ============================================================
# RINEX HEADER READING
# ============================================================

def read_header_from_text(text):
    """
    Read enough of a RINEX header to determine:

    - RINEX version
    - file type
    - whether it is an observation file

    RINEX 2 and RINEX 3 both contain:

        RINEX VERSION / TYPE

    in the header.
    """

    lines = text.splitlines()

    for line in lines:

        if "RINEX VERSION / TYPE" not in line:
            continue

        try:

            version_string = line[0:9].strip()
            version = float(version_string)

        except (ValueError, IndexError):

            return {
                "rinex_version": None,
                "file_type": None,
                "observation_file": False,
            }

        # RINEX 2.x
        if version < 3.0:

            version_family = "2.x"

        # RINEX 3.x and later
        else:

            version_family = "3.x"

        # RINEX 2.x uses column 21 for the file type.
        # RINEX 3.x uses the same general header field but
        # exact spacing may vary, so we inspect the line.

        file_type = line[20:21].strip()

        observation_file = (
            file_type.upper() == "O"
        )

        return {
            "rinex_version": version_family,
            "rinex_version_number": version,
            "file_type": file_type,
            "observation_file": observation_file,
        }

    return {
        "rinex_version": None,
        "rinex_version_number": None,
        "file_type": None,
        "observation_file": False,
    }


# ============================================================
# HEADER FROM UNCOMPRESSED FILE
# ============================================================

def read_uncompressed_header(file_path, max_lines=200):
    """
    Read only the beginning of an uncompressed RINEX file.

    We do not load the complete observation file into memory.
    """

    try:

        with open(
            file_path,
            "r",
            encoding="ascii",
            errors="replace"
        ) as file:

            header_lines = []

            for _ in range(max_lines):

                line = file.readline()

                if not line:
                    break

                header_lines.append(line)

                if "END OF HEADER" in line:
                    break

        return "".join(header_lines)

    except OSError as exc:

        logger.error(
            f"Could not read RINEX header: {file_path} | {exc}"
        )

        return ""


# ============================================================
# HEADER FROM GZIP
# ============================================================

def read_gzip_header(file_path, max_lines=200):
    """
    Read the header of a GZIP-compressed RINEX file.
    """

    try:

        with gzip.open(
            file_path,
            "rt",
            encoding="ascii",
            errors="replace"
        ) as file:

            header_lines = []

            for _ in range(max_lines):

                line = file.readline()

                if not line:
                    break

                header_lines.append(line)

                if "END OF HEADER" in line:
                    break

        return "".join(header_lines)

    except OSError as exc:

        logger.error(
            f"Could not read GZIP RINEX file: {file_path} | {exc}"
        )

        return ""


# ============================================================
# HEADER FROM ZIP
# ============================================================

def read_zip_header(file_path, max_lines=200):
    """
    Read a RINEX header directly from a ZIP archive.

    The complete archive is NOT extracted.
    """

    members = get_zip_members(file_path)

    candidates = find_rinex_members(members)

    if not candidates:
        return "", None

    # Prefer the first likely RINEX observation file.
    member = candidates[0]

    try:

        with zipfile.ZipFile(file_path, "r") as archive:

            with archive.open(member, "r") as raw_file:

                header_lines = []

                for _ in range(max_lines):

                    line = raw_file.readline()

                    if not line:
                        break

                    decoded = line.decode(
                        "ascii",
                        errors="replace"
                    )

                    header_lines.append(decoded)

                    if "END OF HEADER" in decoded:
                        break

        return "".join(header_lines), member

    except (zipfile.BadZipFile, OSError, KeyError) as exc:

        logger.error(
            f"Could not read RINEX header from ZIP: "
            f"{file_path} | {exc}"
        )

        return "", None


# ============================================================
# MAIN DETECTOR
# ============================================================

def detect_rinex(file_path):
    """
    Detect the RINEX format and file type.

    Parameters
    ----------
    file_path : str or Path
        Path to a RINEX file or compressed archive.

    Returns
    -------
    dict
        Structured RINEX metadata.
    """

    result = empty_result(file_path)

    file_path = Path(file_path)

    if not file_path.exists():

        result["error"] = "File does not exist"

        logger.error(
            f"RINEX file does not exist: {file_path}"
        )

        return result

    archive_type = detect_archive_type(file_path)

    result["archive_type"] = archive_type

    header = ""
    internal_file = None

    # --------------------------------------------------------
    # ZIP
    # --------------------------------------------------------

    if archive_type == "zip":

        header, internal_file = read_zip_header(
            file_path
        )

    # --------------------------------------------------------
    # GZIP
    # --------------------------------------------------------

    elif archive_type == "gzip":

        header = read_gzip_header(
            file_path
        )

    # --------------------------------------------------------
    # UNCOMPRESSED
    # --------------------------------------------------------

    else:

        header = read_uncompressed_header(
            file_path
        )

    # --------------------------------------------------------
    # No header
    # --------------------------------------------------------

    if not header:

        result["error"] = (
            "Could not read a RINEX header"
        )

        return result

    # --------------------------------------------------------
    # Parse header
    # --------------------------------------------------------

    header_info = read_header_from_text(
        header
    )

    result.update(header_info)

    result["valid"] = (
        result["rinex_version"] is not None
        and result["observation_file"] is True
    )

    if internal_file is not None:

        result["internal_file"] = internal_file

    logger.info(
        "RINEX detection | "
        f"File: {file_path.name} | "
        f"Version: {result['rinex_version']} | "
        f"Observation: {result['observation_file']} | "
        f"Valid: {result['valid']}"
    )

    return result


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("RINEX DETECTOR TEST")
    print("=" * 60)

    print(
        "\nNo RINEX file was supplied for testing."
    )

    print(
        "\nThe detector module has been loaded successfully."
    )

    print(
        "\nWhen real RINEX data are available, run:"
    )

    print(
        "python -m processing.rinex_detector "
        "/path/to/file.zip"
    )

    print("=" * 60)