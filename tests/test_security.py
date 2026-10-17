"""Unit tests for security/upload_checks.py and export sanitization."""

import pytest
import pandas as pd
from security.upload_checks import (
    check_file_size,
    is_safe_csv_content,
    check_csv_bounds,
    defuse_formula_injection,
    sanitize_filename,
    has_prohibited_characters,
    MAX_FILE_SIZE_BYTES,
    MAX_STUDENT_ID_LENGTH,
    MAX_STUDENT_NAME_LENGTH,
    MAX_DEPARTMENT_LENGTH,
    MAX_HEADER_LENGTH,
    MAX_RAW_CELL_LENGTH,
    MAX_VALIDATION_ERRORS,
)
from core.loader import load_csv_from_bytes, IngestionError
from core.validation import validate_dataset
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


def test_defuse_formula_injection_leading_whitespace_and_percent():
    """Verify formula injection triggers preceded by spaces, tabs, carriage returns, or percent are defused."""
    assert defuse_formula_injection("   =1+1") == "'   =1+1"
    assert defuse_formula_injection("\t=SUM(A1:A10)") == "'\t=SUM(A1:A10)"
    assert defuse_formula_injection("  +cmd|' /C calc'!A0") == "'  +cmd|' /C calc'!A0"
    assert defuse_formula_injection("\r-10") == "'\r-10"
    assert defuse_formula_injection("   @admin") == "'   @admin"
    assert defuse_formula_injection("%0A") == "'%0A"
    assert defuse_formula_injection("  %TOTAL") == "'  %TOTAL"

    # Already quoted formula should not receive redundant second quote
    assert defuse_formula_injection("'=1+1") == "'=1+1"
    assert defuse_formula_injection("''=1+1") == "''=1+1"

    # Mid-string formula characters should NOT trigger escaping
    assert defuse_formula_injection("Grade A+") == "Grade A+"
    assert defuse_formula_injection("student@school.edu") == "student@school.edu"
    assert defuse_formula_injection("Math - Advanced") == "Math - Advanced"


def test_sanitize_filename_prevents_traversal_and_malicious_names():
    """Verify sanitize_filename eliminates directory traversal, control chars, and HTML tags."""
    # Directory traversal
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.exe") == "calc.exe"

    # Null bytes and control characters
    assert sanitize_filename("grades\x00_test.csv") == "grades_test.csv"
    assert sanitize_filename("test\x07file.csv") == "testfile.csv"

    # HTML tags / script injection
    assert sanitize_filename("<script>alert(1)</script>.csv") == "script.csv"
    assert sanitize_filename("<alert>.csv") == "alert.csv"

    # Fallback on empty or dot-only
    assert sanitize_filename("") == "uploaded_dataset.csv"
    assert sanitize_filename(".") == "uploaded_dataset.csv"
    assert sanitize_filename("...") == "uploaded_dataset.csv"

    # Excessive length bounding
    long_name = ("a" * 200) + ".csv"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) <= 128
    assert sanitized.endswith(".csv")


def test_has_prohibited_characters_identifies_bidi_and_control():
    """Verify detection of dangerous bidi overrides and ASCII/Latin-1 control characters."""
    # Bidi overrides
    assert has_prohibited_characters("User\u202ename") is True   # Right-to-Left Override
    assert has_prohibited_characters("Test\u202e") is True
    assert has_prohibited_characters("Student\u200fName") is True  # RLM

    # Control characters
    assert has_prohibited_characters("Student\x00Name") is True
    assert has_prohibited_characters("Line\x1bName") is True  # ESC char

    # Safe legitimate characters
    assert has_prohibited_characters("John Doe") is False
    assert has_prohibited_characters("Aarav Sharma") is False
    assert has_prohibited_characters("Müller-Özdemir") is False
    assert has_prohibited_characters("Renée O'Connor") is False
    assert has_prohibited_characters("李小龙") is False


def test_loader_rejects_oversized_cells():
    """Verify CSV containing any cell larger than MAX_RAW_CELL_LENGTH (512 chars) is rejected."""
    huge_cell = "A" * 600
    csv_bytes = f"student_id,student_name,attendance,Math\nS01,{huge_cell},90.0,85.0\n".encode("utf-8")

    with pytest.raises(IngestionError) as exc_info:
        load_csv_from_bytes(csv_bytes, "test.csv")
    assert "exceeds the limit of 512 characters" in str(exc_info.value)


def test_loader_rejects_oversized_headers_and_control_chars():
    """Verify CSV containing headers exceeding 64 characters or with control characters is rejected."""
    # Header > 64 chars
    huge_header = "H" * 70
    csv_bytes = f"student_id,student_name,attendance,{huge_header}\nS01,Alice,90.0,85.0\n".encode("utf-8")
    with pytest.raises(IngestionError) as exc_info:
        load_csv_from_bytes(csv_bytes, "test.csv")
    assert "exceeds maximum allowed length" in str(exc_info.value)

    # Header with control characters
    bad_header_bytes = b"student_id,student_name,attendance,Math\x07_Lab\nS01,Alice,90.0,85.0\n"
    with pytest.raises(IngestionError) as exc_info:
        load_csv_from_bytes(bad_header_bytes, "test.csv")
    assert "contains unprintable control characters" in str(exc_info.value)


def test_validation_rejects_oversized_identifiers_and_names():
    """Verify validation flags student IDs > 64 chars, names > 128 chars, and departments > 64 chars."""
    df_oversized = pd.DataFrame({
        "student_id": ["ID_" + ("x" * 70)],
        "student_name": ["Name_" + ("y" * 150)],
        "attendance": [90.0],
        "Math": [85.0],
        "department": ["Dept_" + ("z" * 70)],
    })

    res = validate_dataset(
        df=df_oversized,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
        department_col="department",
    )
    assert res.is_valid is False
    assert any("Student ID exceeds maximum allowed length" in str(e) for e in res.errors)
    assert any("Student Name exceeds maximum allowed length" in str(e) for e in res.errors)
    assert any("Department name exceeds maximum allowed length" in str(e) for e in res.errors)


def test_validation_rejects_bidi_override_in_student_name():
    """Verify validation rejects names disguising identities with bidirectional overrides."""
    df_bidi = pd.DataFrame({
        "student_id": ["S01"],
        "student_name": ["Admin\u202etxt.fdp"],
        "attendance": [90.0],
        "Math": [85.0],
    })

    res = validate_dataset(
        df=df_bidi,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    assert any("prohibited Unicode sequences" in str(e) for e in res.errors)


def test_validation_error_capping():
    """Verify dataset producing over MAX_VALIDATION_ERRORS (500) errors is safely capped."""
    # Generate 600 invalid records
    df_bad = pd.DataFrame({
        "student_id": [""] * 600,
        "student_name": [""] * 600,
        "attendance": [-10.0] * 600,
        "Math": [150.0] * 600,
    })

    res = validate_dataset(
        df=df_bad,
        student_id_col="student_id",
        name_col="student_name",
        attendance_col="attendance",
        subject_configs={"Math": 100.0},
    )
    assert res.is_valid is False
    # Error count should be capped at 501 (500 errors + 1 capping notice)
    assert len(res.errors) == MAX_VALIDATION_ERRORS + 1
    assert "Validation error limit reached" in str(res.errors[-1])

