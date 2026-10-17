"""Safe, resilient CSV loader for academic datasets.

Guarantees:
1. Zero Streamlit coupling.
2. Character encoding resilience (UTF-8, UTF-8-BOM, Latin-1 fallback).
3. Preservation of string formatting (e.g. leading zeros in student IDs).
4. Whitespace trimming and header normalization.
5. Detection of duplicate column headers (including duplicates after whitespace trimming).
6. Detection of empty or whitespace-only column headers.
7. Support for multiline quoted fields and rejection of malformed quoted fields or inconsistent row lengths.
8. Enforces computational bounds via security checks and cell-size constraints.
"""

import io
import csv
from typing import Tuple, List, Optional
import pandas as pd

from security.upload_checks import (
    check_file_size,
    is_safe_csv_content,
    check_csv_bounds,
    sanitize_filename,
    has_prohibited_characters,
    MAX_HEADER_LENGTH,
    MAX_RAW_CELL_LENGTH,
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
    clean_filename = sanitize_filename(filename)

    # 1. Byte-level size check
    size_ok, size_msg = check_file_size(file_bytes)
    if not size_ok:
        raise IngestionError(f"File '{clean_filename}' rejected: {size_msg}")

    # 2. Content safety check (reject binaries/null bytes)
    safe_ok, safe_msg = is_safe_csv_content(file_bytes)
    if not safe_ok:
        raise IngestionError(f"File '{clean_filename}' rejected: {safe_msg}")

    # 3. Detect encoding
    encoding = detect_encoding(file_bytes)

    # 4. Decode content and inspect structure via csv.reader
    try:
        sample_text = file_bytes.decode(encoding, errors="replace")
    except Exception as exc:
        raise IngestionError(f"Failed to decode CSV '{clean_filename}' using {encoding}: {str(exc)}") from exc

    if not sample_text.strip():
        raise IngestionError(f"File '{clean_filename}' contains no readable content or is empty.")

    try:
        csv_reader = csv.reader(io.StringIO(sample_text))
        first_row = next(csv_reader, None)
    except csv.Error as exc:
        raise IngestionError(f"Malformed CSV structure in '{clean_filename}': {str(exc)}") from exc

    if first_row is None or len(first_row) == 0 or all(not str(c).strip() for c in first_row):
        raise IngestionError(f"Uploaded CSV file '{clean_filename}' has no header row.")

    # Check for empty headers (e.g. "student_id,name,,Math")
    empty_header_positions = [i + 1 for i, c in enumerate(first_row) if not str(c).strip()]
    if empty_header_positions:
        raise IngestionError(
            f"Dataset contains empty or whitespace-only column header at column position(s) {empty_header_positions}. "
            f"All column headers must be non-empty strings."
        )

    # Check header length and prohibited characters
    for idx, raw_h in enumerate(first_row, start=1):
        h_str = str(raw_h).strip()
        if len(h_str) > MAX_HEADER_LENGTH:
            raise IngestionError(
                f"Column header at position {idx} exceeds maximum allowed length of "
                f"{MAX_HEADER_LENGTH} characters ({len(h_str)} characters detected)."
            )
        if has_prohibited_characters(h_str):
            raise IngestionError(
                f"Column header '{h_str[:20]}...' contains unprintable control characters or prohibited Unicode sequences."
            )

    # Check for duplicate headers after whitespace normalization
    norm_headers = [str(c).strip() for c in first_row]
    seen_headers = set()
    dup_headers = []
    for h in norm_headers:
        if h in seen_headers and h not in dup_headers:
            dup_headers.append(h)
        seen_headers.add(h)

    if dup_headers:
        raise IngestionError(
            f"Dataset contains duplicate column headers (after whitespace normalization): {dup_headers}. "
            f"All column headers must be distinct."
        )

    # Validate row length consistency and cell length bounds across all data rows
    expected_cols = len(first_row)
    try:
        for row_idx, row in enumerate(csv_reader, start=2):
            if not row or all(not str(c).strip() for c in row):
                continue
            if len(row) != expected_cols:
                raise IngestionError(
                    f"Inconsistent row length in '{clean_filename}' at row {row_idx}: "
                    f"expected {expected_cols} columns, found {len(row)}."
                )
            for col_idx, cell in enumerate(row, start=1):
                if len(str(cell)) > MAX_RAW_CELL_LENGTH:
                    raise IngestionError(
                        f"Oversized CSV cell in '{clean_filename}' at row {row_idx}, column {col_idx}: "
                        f"field length ({len(str(cell))}) exceeds the limit of {MAX_RAW_CELL_LENGTH} characters."
                    )
    except IngestionError:
        raise
    except csv.Error as exc:
        raise IngestionError(f"Malformed CSV data in '{clean_filename}': {str(exc)}") from exc

    # 5. Parse CSV via Pandas
    try:
        # Read with dtype=str to preserve exact values (e.g., "0042" stays "0042")
        df_raw = pd.read_csv(
            io.BytesIO(file_bytes),
            encoding=encoding,
            dtype=str,
            index_col=False,
            skipinitialspace=True,
            on_bad_lines="error",
        )
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"Failed to parse CSV '{clean_filename}': {str(exc)}") from exc

    # Strip column names
    df_raw.columns = [str(c).strip() for c in df_raw.columns]

    # 6. Check row and column bounds
    row_count, col_count = df_raw.shape
    bounds_ok, bounds_msg = check_csv_bounds(row_count, col_count)
    if not bounds_ok:
        raise IngestionError(f"Dataset bounds violation in '{clean_filename}': {bounds_msg}")

    return df_raw, list(df_raw.columns)


def load_csv_from_path(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """Load and parse a CSV file directly from a filesystem path."""
    clean_path = sanitize_filename(file_path)
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
    except OSError as err:
        raise IngestionError(f"Could not open file at '{clean_path}': {err.strerror}") from err

    return load_csv_from_bytes(raw_bytes, filename=clean_path)
