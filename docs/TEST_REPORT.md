# Automated Test Execution & Quality Assurance Report
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 2.0.0 (Final Pre-Release)  
**Date of Execution:** 17 October 2026  
**Test Framework:** `pytest 8.4.2` / `Python 3.9.6` / `macOS Darwin ARM64`  
**Overall Status:** PASSED (134 of 134 tests passing, 100% success rate)  

---

## 1. Executive Summary

| Test Suite | File | Tests Run | Passed | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Loader & Ingestion** | `tests/test_loader.py` | 13 | 13 | 0 | 0.05s |
| **Academic Validation** | `tests/test_validation.py` | 15 | 15 | 0 | 0.08s |
| **Grading, Precision & Policy** | `tests/test_grading.py` | 46 | 46 | 0 | 0.16s |
| **Statistical Analytics** | `tests/test_analytics.py` | 7 | 7 | 0 | 0.03s |
| **Reporting & Formatting** | `tests/test_reports.py` | 2 | 2 | 0 | 0.02s |
| **Security, Sanitization & Limits** | `tests/test_security.py` | 13 | 13 | 0 | 0.06s |
| **Session Isolation & State** | `tests/test_sessions.py` | 32 | 32 | 0 | 1.82s |
| **Standalone CLI Operations** | `tests/test_cli.py` | 6 | 6 | 0 | 0.06s |
| **TOTAL** | | **134** | **134** | **0** | **3.48s** |

---

## 2. Test Execution Details by Suite

### 2.1 Ingestion & Loader (`tests/test_loader.py`)
- Verified standard sample datasets load cleanly (`sample_school.csv`, `sample_college.csv`).
- Leading zero preservation (`"001"` remains string rather than integer `1`).
- Rejection of duplicate headers, whitespace-only files, inconsistent row lengths, empty files, and header-only files.
- Robust encoding detection across UTF-8, UTF-8-BOM, and Latin-1.
- Ingestion error raised if raw cells exceed 512 characters or column headers exceed 64 characters.

### 2.2 Academic Validation (`tests/test_validation.py`)
- Verified mandatory column verification and row-level constraint checks.
- Unique student ID validation with case-insensitive collision detection.
- Non-empty student names accepting arbitrary international Unicode characters.
- Attendance validation within [0.0, 100.0] as finite numbers.
- Subject score validation rejecting out-of-range, NaN, and positive/negative infinity.
- Support for documented absence indicators (`ABS`, `ABSENT`) while rejecting unstandardized codes.
- Length validation on student IDs ($\le 64$), names ($\le 128$), and departments ($\le 64$).
- Rejection of dangerous Unicode bidirectional override sequences (`\u202e` etc.) and unprintable control characters.
- Enforcement of error capping at 500 errors to prevent denial of service.

### 2.3 Grading, Numerical Precision & Policy Configuration (`tests/test_grading.py`)
- **Default Grading Scale:** Verified 7-tier scale (`A+` down to `F`).
- **School Grading Scale:** Verified 6-tier custom school policy (`A+`, `A`, `B`, `C`, `D`, `F`).
- **College Grading Scale:** Verified 7-tier custom college policy (`O`, `E`, `A`, `B`, `C`, `P`, `F`).
- **Custom Grade Labels:** Validated acceptance of arbitrary alphanumeric grade labels (e.g., `Distinction`, `Merit`, `Pass`, `Fail`).
- **Policy Validation Invariants:**
  - Rejection of duplicate grade labels (case-insensitive) (`PolicyConfigurationError`).
  - Rejection of duplicate percentage thresholds (`PolicyConfigurationError`).
  - Rejection of non-monotonic or ascending boundary order (`PolicyConfigurationError`).
  - Rejection of missing 0.0% lowest baseline (`PolicyConfigurationError`).
  - Rejection of boundaries with fewer than 2 tiers (`PolicyConfigurationError`).
  - Rejection of non-finite or out-of-range percentages ($<0$ or $>100$).
- **Per-Subject Passing Thresholds:** Verified `subject_pass_overrides` enforce course-specific passing cutoffs.
- **Attendance Warning Policy:** Verified toggle (`enable_attendance_warning`) controls alert indicators without causing academic failure.
- **Exact Boundary Preservation:** Verified full precision `raw_percentage` prevents premature rounding at pass/fail and grade boundaries (`39.996%` $\rightarrow$ FAIL, `40.0%` $\rightarrow$ PASS, `79.999%` $\rightarrow$ B+).
- **Direct Invocation Fail-Safe Validation:** Strict validation inside `evaluate_students()` rejects corrupted data with `ValueError`.

### 2.4 Statistical Analytics (`tests/test_analytics.py`)
- Class averages, medians, standard deviations, extremes, and pass rates.
- Difficulty ranking (Rank 1 = most challenging).
- Deterministic multi-key tie-breaking leaderboard.
- Transparent academic attention indicators dynamically incorporating institutional passing and attendance thresholds.
- Departmental comparative analytics.

### 2.5 Security & Sanitization (`tests/test_security.py`)
- Formula injection (CWE-1236) neutralization across triggers: `=`, `+`, `-`, `@`, `\t`, `\r`, `%`.
- Leading whitespace formula injection bypass protection (`"   =1+1"`, `"\t@SUM(...)"`, `"  +cmd|..."`).
- Preservation of pre-escaped formula strings without redundant quote inflation.
- Filename sanitization against directory traversal (`../../etc/passwd`, `..\\windows\\system32\\cmd.exe`), null bytes, control characters, and HTML tags (`<script>`).
- Detection and rejection of Unicode bidirectional overrides (`\u202e`) and unprintable control characters.
- Maximum file size (2 MB) and dimensional bounds (5,000 rows, 30 columns) enforcement.
- Raw CSV cell length bounding ($\le 512$ characters) and header length bounding ($\le 64$ characters).
- Validation error collection limit (capped at 500 errors).

### 2.6 Concurrency & Session State Integrity (`tests/test_sessions.py`)
- Thread-safe isolation and zero cross-contamination across concurrent worker sessions.
- Deterministic SHA-256 dataset fingerprinting and state reset on dataset modification.
- Automated result invalidation (`is_analysis_stale`) on configuration mutation (grade boundaries, subject max marks, per-subject thresholds, attendance settings, institution metadata).
- One-click reset clears institutional metadata, datasets, and configuration widgets.
- Grade-boundary editor state retention: adding or removing a grade level preserves user-edited labels and percentage numbers without discarding previous entries.
- Added regression test `test_grade_boundary_editor_preserves_user_edits_on_remove_tier`.
- Added regression test `test_grade_boundary_editor_add_tier_at_low_percentage_avoids_duplicate`.
- Added regression test `test_student_search_special_characters_regex_safety`.

### 2.7 Standalone CLI Operations (`tests/test_cli.py`)
- Verified `main.py` subject configuration inference (labs/projects default to 50 max marks, theory to 100).
- Verified format table helper renders cleanly with zero external dependency.
- Verified end-to-end execution on `data/sample_school.csv`.
- Verified end-to-end execution on `data/sample_college.csv` with `--export` option producing sanitized CSV.
- Verified error handling and clean exit code 1 when input file is missing.
- Verified error handling and clean exit code 1 when grade boundaries are non-monotonic or malformed.

---

## 3. Discovered Anomalies & Applied Resolutions

1. **Student Explorer Regex Crash on Special Characters (Final Hardening):**
   - *Problem:* When searching by Student Name or ID with regex characters (`[`, `(`, `*`, `+`), Pandas `str.contains(query)` raised unhandled `re.error` (e.g. `unterminated character set`).
   - *Fix:* Configured `str.contains(query, regex=False, na=False)` in `app.py`, ensuring all queries are treated strictly as literal substrings.
   - *Regression Test:* `test_student_search_special_characters_regex_safety` (PASSED).

2. **Grade Boundary Editor Duplicate Thresholds on Low Tiers (Final Hardening):**
   - *Problem:* When adding a grade level where the second-to-last tier was $\le 20\%$ (e.g. 10%), the calculation `max(10.0, prev_pct - 10.0)` computed `10.0%`, causing duplicate percentage error (`PolicyConfigurationError`).
   - *Fix:* Updated calculation to divide in half (`round(prev_pct / 2.0, 1)`) when `prev_pct <= 20.0`, ensuring the new tier is strictly decreasing and never duplicates the lowest 0.0% boundary.
   - *Regression Test:* `test_grade_boundary_editor_add_tier_at_low_percentage_avoids_duplicate` (PASSED).

3. **Streamlit Execution from Arbitrary Working Directories (Final Hardening):**
   - *Problem:* If Streamlit was launched from a different working directory, relative references `open("data/sample_school.csv")` failed.
   - *Fix:* Anchored paths to `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` in `app.py` and added directory fallback in `main.py`.

4. **Grade Boundary Editor Data Loss on Add/Remove Tier (Fix 04):**
   - *Problem:* When an educator edited custom grade labels or percentage numbers in Tab 2 and then clicked "➕ Add Grade Level" or "➖ Remove Grade Level", previous edits were discarded.
   - *Fix:* Base tier addition and removal directly on `edited_boundaries` and synchronized `st.session_state.custom_boundaries = edited_boundaries`.

5. **CSV Formula Injection Leading Whitespace Bypass (Fix 04):**
   - *Problem:* Strings like `"   =1+1"` or `"\t@SUM(A1:A10)"` bypassed `.startswith(FORMULA_TRIGGERS)`.
   - *Fix:* Updated `defuse_formula_injection()` to inspect `value.lstrip(" \t\r\n")` for formula triggers and prepended a single quote (`'`).

6. **Oversized Individual CSV Cells DoS (Fix 04):**
   - *Problem:* An individual cell with $>500$ KB of characters caused memory spikes and UI rendering hangs.
   - *Fix:* Enforced `MAX_RAW_CELL_LENGTH = 512` in `core/loader.py`.

---

## 4. Performance & Resource Benchmarks

Real benchmarks conducted on **macOS Darwin ARM64** / **Python 3.9.6**:

### 4.1 Dataset Scaling Benchmarks

| Dataset Size | Records | Total Processing Time | Ingestion + Validation | Grading + Analytics | Peak RAM Delta |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Small Cohort** | 20 students | **13.61 ms** | 6.84 ms | 6.77 ms | 0.56 MB |
| **Standard Class** | 100 students | **13.84 ms** | 6.80 ms | 7.04 ms | 0.45 MB |
| **Large Department** | 1,000 students | **105.32 ms** | 55.43 ms | 49.89 ms | 2.79 MB |
| **Maximum Allowed** | 5,000 students | **514.83 ms** | 272.93 ms | 241.90 ms | 12.66 MB |

### 4.2 Multi-User Concurrency Benchmarks

| Simulated Users | Total Time | Avg Latency | Peak RAM | Data Isolation |
| :--- | :---: | :---: | :---: | :---: |
| **1 User** | 14.16 ms | 11.36 ms | 0.65 MB | Verified 100% Isolated |
| **5 Users** | 35.32 ms | 12.51 ms | 0.44 MB | Verified 100% Isolated |
| **10 Users** | 67.45 ms | 14.20 ms | 0.58 MB | Verified 100% Isolated |
| **20 Users** | 126.01 ms | 13.82 ms | 0.48 MB | Verified 100% Isolated |

---

## 5. Verification Sign-Off

- **Automated Unit & Integration Tests:** 134/134 PASSED (100%)
- **CLI Sample School Dataset:** Verified PASSED (0 errors, full report generated)
- **CLI Sample College Dataset:** Verified PASSED (0 errors, full report generated)
- **CLI Custom Policy & Overrides:** Verified PASSED (0 errors, metadata reflected)
- **GitHub Actions CI Matrix:** Python 3.9, 3.10, 3.11 with `permissions: contents: read` verified
- **Overall Quality Status:** **PRODUCTION READY**
