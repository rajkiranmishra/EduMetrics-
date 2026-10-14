"""Upload security validations and CSV formula injection defusion.

Implements lightweight, security-first defenses against:
1. Denial of Service via oversized files, row bombs, or column bombs.
2. Binary / executable file uploads masquerading as CSV.
3. CSV Formula Injection (CWE-1236) in exported data.
"""

from typing import Tuple, Any

MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB limit
MAX_ROW_COUNT: int = 5000                   # 5,000 rows limit
MAX_COLUMN_COUNT: int = 30                  # 30 columns limit

# Formula triggers per CWE-1236: =, +, -, @, Tab (0x09), Carriage Return (0x0D)
FORMULA_TRIGGERS: Tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def check_file_size(file_bytes: bytes, max_bytes: int = MAX_FILE_SIZE_BYTES) -> Tuple[bool, str]:
    """Verify that uploaded file size does not exceed the allowed threshold."""
    if not file_bytes:
        return False, "Uploaded file is empty (0 bytes)."
    size = len(file_bytes)
    if size > max_bytes:
        return False, (
            f"File size exceeds the {max_bytes // (1024 * 1024)} MB limit "
            f"({size / (1024 * 1024):.2f} MB detected)."
        )
    return True, "File size within acceptable limits."


def is_safe_csv_content(file_bytes: bytes) -> Tuple[bool, str]:
    """Inspect byte-level content to ensure the file is plain text, not a binary or executable."""
    if not file_bytes:
        return False, "File is empty."

    # Reject null bytes which indicate binary files (ELF, PE, Mach-O, ZIP, etc.)
    if b"\x00" in file_bytes[:8192]:
        return False, "Binary or executable content detected; only text CSV files are permitted."

    # Check for known binary magic bytes
    known_signatures = [
        (b"PK\x03\x04", "ZIP / Office archive"),
        (b"\x7fELF", "Linux ELF executable"),
        (b"MZ", "Windows PE executable"),
        (b"\xfe\xed\xfa", "Mach-O binary"),
        (b"\xcf\xfa\xed\xfe", "Mach-O binary (64-bit)"),
        (b"%PDF", "PDF document"),
    ]
    for signature, name in known_signatures:
        if file_bytes.startswith(signature):
            return False, f"Prohibited binary file format detected ({name}). Please upload a valid CSV."

    return True, "Content appears to be plain text."


def check_csv_bounds(
    row_count: int,
    col_count: int,
    max_rows: int = MAX_ROW_COUNT,
    max_cols: int = MAX_COLUMN_COUNT,
) -> Tuple[bool, str]:
    """Enforce computational and memory bounds on row and column counts."""
    if row_count == 0:
        return False, "Dataset contains 0 data rows."
    if row_count > max_rows:
        return False, f"Dataset exceeds maximum allowed rows ({row_count} > {max_rows})."
    if col_count > max_cols:
        return False, f"Dataset exceeds maximum allowed columns ({col_count} > {max_cols})."
    return True, "Dataset dimensions within acceptable limits."


def defuse_formula_injection(value: Any) -> Any:
    """Neutralize potential CSV formula injection (CWE-1236) in exported spreadsheet cells.

    If a text field begins with =, +, -, @, or control characters, prepend a single quote (')
    to instruct spreadsheet engines (Excel, Calc, Sheets) to treat it strictly as literal text.
    """
    if isinstance(value, str):
        if value.startswith(FORMULA_TRIGGERS):
            return f"'{value}"
    return value
