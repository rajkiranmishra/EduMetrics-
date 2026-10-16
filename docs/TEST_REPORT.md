# Automated Test Execution & Quality Assurance Report
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.5.0  
**Date of Execution:** 16 October 2026  
**Test Framework:** `pytest 8.4.2` / `Python 3.9.6` / `macOS Darwin ARM64`  
**Overall Status:** PASSED (125 of 125 tests passing, 100% success rate)  

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
| **Session Isolation & State** | `tests/test_sessions.py` | 29 | 29 | 0 | 1.48s |
| **TOTAL** | | **125** | **125** | **0** | **2.71s** |

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
- Deterministic MD5 dataset fingerprinting and state reset on dataset modification.
- Automated result invalidation (`is_analysis_stale`) on configuration mutation (grade boundaries, subject max marks, per-subject thresholds, attendance settings, institution metadata).
- One-click reset clears institutional metadata, datasets, and configuration widgets.
- Grade-boundary editor state retention: adding or removing a grade level preserves user-edited labels and percentage numbers without discarding previous entries.

---

## 3. Discovered Anomalies & Applied Resolutions

1. **Grade Boundary Editor Data Loss on Add/Remove Tier (Fix 04):**
   - *Problem:* When an educator edited custom grade labels or percentage numbers in Tab 2 and then clicked "➕ Add Grade Level" or "➖ Remove Grade Level", the editor reconstructed the boundary list from `active_bounds` (the prior version's unedited list), discarding all in-progress edits.
   - *Fix:* Base tier addition and removal directly on `edited_boundaries`, and synchronize `st.session_state.custom_boundaries = edited_boundaries` in session state.

2. **CSV Formula Injection Leading Whitespace Bypass (Fix 04):**
   - *Problem:* Strings like `"   =1+1"` or `"\t@SUM(A1:A10)"` bypassed `.startswith(FORMULA_TRIGGERS)`. When opened in certain versions of Excel or Calc, leading spaces are stripped by the spreadsheet parser, triggering formula execution.
   - *Fix:* Updated `defuse_formula_injection()` to inspect `value.lstrip(" \t\r\n")` for formula triggers and prepended a single quote (`'`), while preventing double-escaping on already escaped strings.

3. **Oversized Individual CSV Cells DoS (Fix 04):**
   - *Problem:* A CSV file under the 2 MB limit could contain an individual cell with $>500$ KB of characters, causing severe UI rendering hangs and unbounded memory spikes during Pandas DataFrame construction.
   - *Fix:* Enforced `MAX_RAW_CELL_LENGTH = 512` during initial CSV reader row inspection in `core/loader.py`, rejecting oversized cells with an `IngestionError` before DataFrame instantiation.

4. **Adversarial Upload Filenames & Path Traversal (Fix 04):**
   - *Problem:* Uploaded filenames or CLI arguments containing path traversal sequences (e.g., `../../etc/passwd`) or HTML tags (`<script>`) were reflected in UI text and reports.
   - *Fix:* Implemented `sanitize_filename()` in `security/upload_checks.py` to extract base names, remove directory traversal separators, strip HTML/script characters, remove null bytes/control chars, and enforce a 128-character limit.

5. **Validation Error DOM & Memory Exhaustion (Fix 04):**
   - *Problem:* An uploaded file with thousands of invalid cells generated an unbounded list of `ValidationError` objects, which severely degraded Streamlit UI rendering and consumed server memory.
   - *Fix:* Enforced `MAX_VALIDATION_ERRORS = 500`. Validation halts adding individual error records after 500 errors and appends an explicit notification notice.

6. **Hardcoded Academic Attention Heuristics (Fix 04):**
   - *Problem:* `identify_academic_attention_cases()` used hardcoded 40% aggregate pass and 75% attendance cutoffs regardless of the educator's configured grading policy.
   - *Fix:* Parametrized `identify_academic_attention_cases()` with `aggregate_pass_threshold` and `attendance_warning_threshold`, wired directly to the active `GradingPolicy` in `app.py` and `main.py`.

---

## 4. Performance & Resource Benchmarks

Real benchmarks conducted on **macOS Darwin ARM64** / **Python 3.9.6**:

### 4.1 Dataset Scaling Benchmarks

| Dataset Size | Records | Total Processing Time | Ingestion + Validation | Grading + Analytics | Peak RAM Delta |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Small Cohort** | 20 students | **13.61 ms** | 6.84 ms | 6.77 ms | 0.56 MB |
| **Standard Class** | 100 students | **13.84 ms** | 6.80 ms | 7.04 ms | 0.45 MB |
| **Large Department** | 1,000 students | **105.32 ms** | 55.43 ms | 49.89 ms | 2.79 MB |
| **Maximum Allowed** | 5,000 students | **514.83 ms** | 272.93 ms | 241.90 ms | 12.66 MB |

### 4.2 Multi-User Concurrency Benchmarks

| Simulated Users | Total Time | Avg Latency | Peak RAM | Data Isolation |
| :---: | :---: | :---: | :---: | :---: |
| **1 User** | 14.16 ms | 11.36 ms | 0.65 MB | Verified 100% Isolated |
| **5 Users** | 35.32 ms | 12.51 ms | 0.44 MB | Verified 100% Isolated |
| **10 Users** | 67.45 ms | 14.20 ms | 0.58 MB | Verified 100% Isolated |
| **20 Users** | 126.01 ms | 13.82 ms | 0.48 MB | Verified 100% Isolated |

---

## 5. Verification Sign-Off

- **Automated Unit & Integration Tests:** 125/125 PASSED (100%)
- **CLI Sample School Dataset:** Verified PASSED (0 errors, full report generated)
- **CLI Sample College Dataset:** Verified PASSED (0 errors, full report generated)
- **GitHub Actions Least Privilege:** `permissions: contents: read` verified
- **Fix 04 Overall Status:** PASS
