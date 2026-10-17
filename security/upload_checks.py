"""Upload security validations, filename sanitization, and CSV formula injection defusion.

Implements lightweight, security-first defenses against:
1. Denial of Service via oversized files, row bombs, column bombs, or oversized cells.
2. Binary / executable file uploads masquerading as CSV.
3. CSV Formula Injection (CWE-1236) across exported spreadsheet data, including leading whitespace bypasses.
4. Adversarial filenames, directory traversal, and unprintable control character injection.
"""

import os
import re
from typing import Tuple, Any

MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB limit
MAX_ROW_COUNT: int = 5000                   # 5,000 rows limit
MAX_COLUMN_COUNT: int = 30                  # 30 columns limit

# Field length limits to prevent UI layout DoS and unbounded string buffering
MAX_STUDENT_ID_LENGTH: int = 64
MAX_STUDENT_NAME_LENGTH: int = 128
MAX_DEPARTMENT_LENGTH: int = 64
MAX_HEADER_LENGTH: int = 64
MAX_RAW_CELL_LENGTH: int = 512
MAX_FILENAME_LENGTH: int = 128
MAX_VALIDATION_ERRORS: int = 500

# Formula triggers per CWE-1236: =, +, -, @, Tab (0x09), Carriage Return (0x0D), %
FORMULA_TRIGGERS: Tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r", "%")

# Dangerous Unicode bidirectional formatting override characters that can visually spoof strings
BIDI_OVERRIDE_CHARS = {
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",  # LRE, RLE, PDF, LRO, RLO
    "\u200e", "\u200f",                                  # LRM, RLM
    "\u2066", "\u2067", "\u2068", "\u2069",            # LRI, RLI, FSI, PDI
}


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

    Protects against formula injection triggers even when preceded by leading whitespace
    (e.g., '   =1+1', '\\t@SUM(...)', '  +cmd|...').
    If a text field begins with =, +, -, @, %, or control characters, prepend a single quote (')
    to instruct spreadsheet engines (Excel, Calc, Sheets) to treat it strictly as literal text.
    """
    if isinstance(value, str):
        # Do not double-escape if already protected by single quote
        if value.startswith("'"):
            return value

        stripped = value.lstrip(" \t\r\n")
        if stripped and (stripped.startswith(FORMULA_TRIGGERS) or value.startswith(FORMULA_TRIGGERS)):
            return f"'{value}"
        elif value.startswith(FORMULA_TRIGGERS):
            return f"'{value}"
    return value


def sanitize_filename(filename: str, max_len: int = MAX_FILENAME_LENGTH) -> str:
    """Sanitize uploaded or CLI file names to prevent path traversal and unprintable characters."""
    if not filename:
        return "uploaded_dataset.csv"

    # Extract base filename to strip any path traversal sequences
    clean = os.path.basename(filename.replace("\\", "/"))

    # Remove null bytes, control characters, and dangerous HTML characters
    clean = "".join(
        c for c in clean
        if ord(c) >= 32 and ord(c) != 127 and c not in ("<", ">", '"', "'", ";", "|", "`")
    ).strip()

    # If filename is empty or dot-only after sanitization, assign safe default
    if not clean or clean in (".", "..") or set(clean) == {"."}:
        clean = "uploaded_dataset.csv"

    # Ensure max length bound
    if len(clean) > max_len:
        base, ext = os.path.splitext(clean)
        clean = base[: max_len - len(ext)] + ext

    return clean


def has_prohibited_characters(text: str) -> bool:
    """Check if a string contains unprintable control characters or bidi override sequences."""
    for ch in text:
        code = ord(ch)
        # Check ASCII / Latin-1 control characters except standard whitespace
        if (code < 32 and ch not in ("\t", "\n", "\r")) or (127 <= code <= 159):
            return True
        if ch in BIDI_OVERRIDE_CHARS:
            return True
    return False
