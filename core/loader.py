"""Safe, resilient CSV loader for academic datasets.

Guarantees:
1. Zero Streamlit coupling.
2. Character encoding resilience (UTF-8, UTF-8-BOM, Latin-1 fallback).
3. Preservation of string formatting (e.g. leading zeros in student IDs).
4. Whitespace trimming and header normalization.
5. Duplicate column header detection.
6. Enforces computational bounds via security checks.
"""

import io
from typing import Tuple, List, Optional
import pandas as pd

from security.upload_checks import (
    check_file_size,
    is_safe_csv_content,
    check_csv_bounds,
)


class IngestionError(Exception):
    """Raised when an uploaded or specified CSV fails ingestion security or parsing."""
    pass


def detect_encoding(raw_bytes: bytes) -> str:
    """Detect text encoding with safe fallbacks."""
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        # Fallback to Latin-1 which decodes arbitrary single-byte values safely
        return "latin-1"


def load_csv_from_bytes(
    file_bytes: bytes,
    filename: str = "dataset.csv",
) -> Tuple[pd.DataFrame, List[str]]:
    """Parse CSV bytes safely into a DataFrame with preserved raw types.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Original name of the file for error reporting.

    Returns:
        Tuple of (DataFrame, list of sanitized column names).

    Raises:
        IngestionError: If file violates size, safety, structure, or parsing constraints.
    """
    # 1. Byte-level size check
    size_ok, size_msg = check_file_size(file_bytes)
    if not size_ok:
        raise IngestionError(f"File '{filename}' rejected: {size_msg}")

    # 2. Content safety check (reject binaries/null bytes)
    safe_ok, safe_msg = is_safe_csv_content(file_bytes)
    if not safe_ok:
        raise IngestionError(f"File '{filename}' rejected: {safe_msg}")

    # 3. Detect encoding
    encoding = detect_encoding(file_bytes)

    # 4. Check raw header line for duplicate column headers before pandas mangles them
    try:
        sample_text = file_bytes.decode(encoding, errors="replace")
        header_line = sample_text.splitlines()[0] if sample_text.splitlines() else ""
        import csv
        header_reader = csv.reader([header_line])
        raw_headers = [c.strip() for c in next(header_reader, []) if c.strip()]
        if len(raw_headers) != len(set(raw_headers)):
            duplicates = [c for c in raw_headers if raw_headers.count(c) > 1]
            raise IngestionError(
                f"Dataset contains duplicate column headers: {list(set(duplicates))}. "
                f"All column headers must be distinct."
            )
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"Failed to inspect headers in CSV '{filename}': {str(exc)}") from exc

    # 5. Parse CSV via Pandas
    try:
        # Read with dtype=str to preserve exact values (e.g., "0042" stays "0042")
        df_raw = pd.read_csv(
            io.BytesIO(file_bytes),
            encoding=encoding,
            dtype=str,
            skipinitialspace=True,
            on_bad_lines="error",
        )
    except Exception as exc:
        raise IngestionError(f"Failed to parse CSV '{filename}': {str(exc)}") from exc

    # Strip column names
    df_raw.columns = [str(c).strip() for c in df_raw.columns]

    # 6. Check row and column bounds
    row_count, col_count = df_raw.shape
    bounds_ok, bounds_msg = check_csv_bounds(row_count, col_count)
    if not bounds_ok:
        raise IngestionError(f"Dataset bounds violation in '{filename}': {bounds_msg}")

    return df_raw, list(df_raw.columns)


def load_csv_from_path(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """Load and parse a CSV file directly from a filesystem path."""
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
    except OSError as err:
        raise IngestionError(f"Could not open file at '{file_path}': {err.strerror}") from err

    return load_csv_from_bytes(raw_bytes, filename=file_path)
