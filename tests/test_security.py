"""Unit tests for security/upload_checks.py and export sanitization."""

import pytest
import pandas as pd
from security.upload_checks import (
    check_file_size,
    is_safe_csv_content,
    check_csv_bounds,
    defuse_formula_injection,
    MAX_FILE_SIZE_BYTES,
)
from core.reports import generate_sanitized_csv


def test_defuse_formula_injection_triggers():
    """Verify formula injection characters are defused by prepending a single quote."""
    assert defuse_formula_injection("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert defuse_formula_injection("+12345") == "'+12345"
    assert defuse_formula_injection("-5+10") == "'-5+10"
    assert defuse_formula_injection("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert defuse_formula_injection("\tcmd") == "'\tcmd"
    assert defuse_formula_injection("\rcmd") == "'\rcmd"
    # Normal text should remain untouched
    assert defuse_formula_injection("Aarav Sharma") == "Aarav Sharma"
    assert defuse_formula_injection(95.5) == 95.5


def test_generate_sanitized_csv_protects_exported_cells():
    """Verify exported CSV defuses injected strings in DataFrame columns."""
    df_malicious = pd.DataFrame({
        "student_id": ["=1+1", "002"],
        "student_name": ["@SUM(B1:B10)", "Valid Name"],
        "percentage": [80.0, 90.0],
    })
    csv_bytes = generate_sanitized_csv(df_malicious)
    csv_text = csv_bytes.decode("utf-8")

    assert "'=1+1" in csv_text
    assert "'@SUM(B1:B10)" in csv_text
    assert "Valid Name" in csv_text


def test_file_size_limits():
    """Verify 2 MB upload threshold enforcement."""
    # 1 byte over max limit
    oversized = b"a" * (MAX_FILE_SIZE_BYTES + 1)
    ok, msg = check_file_size(oversized)
    assert ok is False
    assert "exceeds" in msg

    # Normal 100 KB payload
    valid_size = b"a" * (100 * 1024)
    ok, msg = check_file_size(valid_size)
    assert ok is True


def test_binary_and_executable_rejection():
    """Verify files with null bytes or executable headers are rejected."""
    # Null byte payload
    binary_payload = b"student_id,name\nS01,\x00\x01\x02\n"
    ok, msg = is_safe_csv_content(binary_payload)
    assert ok is False
    assert "Binary" in msg

    # ZIP / Office header
    zip_payload = b"PK\x03\x04somezipdata"
    ok, msg = is_safe_csv_content(zip_payload)
    assert ok is False
    assert "ZIP" in msg


def test_csv_dimension_bounds():
    """Verify maximum row and column limits."""
    # Row limit (max 5000)
    ok, msg = check_csv_bounds(row_count=5001, col_count=10)
    assert ok is False
    assert "exceeds maximum allowed rows" in msg

    # Column limit (max 30)
    ok, msg = check_csv_bounds(row_count=100, col_count=31)
    assert ok is False
    assert "exceeds maximum allowed columns" in msg

    # Valid dimensions
    ok, _ = check_csv_bounds(row_count=2000, col_count=15)
    assert ok is True
