# Automated Test Execution & Quality Assurance Report
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.4.0  
**Date of Execution:** 16 October 2026  
**Test Framework:** `pytest 8.4.2` / `Python 3.9.6` / `macOS Darwin ARM64`  
**Overall Status:** PASSED (116 of 116 tests passing, 100% success rate)  

---

## 1. Executive Summary

| Test Suite | File | Tests Run | Passed | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Loader & Ingestion** | `tests/test_loader.py` | 13 | 13 | 0 | 0.05s |
| **Academic Validation** | `tests/test_validation.py` | 15 | 15 | 0 | 0.08s |
| **Grading, Precision & Policy** | `tests/test_grading.py` | 46 | 46 | 0 | 0.16s |
| **Statistical Analytics** | `tests/test_analytics.py` | 7 | 7 | 0 | 0.03s |
| **Reporting & Formatting** | `tests/test_reports.py` | 2 | 2 | 0 | 0.02s |
| **Security & Sanitization**| `tests/test_security.py` | 5 | 5 | 0 | 0.02s |
| **Session Isolation & State** | `tests/test_sessions.py` | 28 | 28 | 0 | 1.42s |
| **TOTAL** | | **116** | **116** | **0** | **1.78s** |

---

## 2. Test Execution Details by Suite

### 2.1 Ingestion & Loader (`tests/test_loader.py`)
- Verified standard sample datasets load cleanly.
- Leading zero preservation (`"001"` remains string).
- Rejection of duplicate headers, whitespace-only files, inconsistent row lengths, empty files, and header-only files.
- Robust encoding detection across UTF-8, UTF-8-BOM, and Latin-1.

### 2.2 Academic Validation (`tests/test_validation.py`)
- Verified mandatory column verification and row-level constraint checks.
- Unique student ID validation with case-insensitive collision detection.
- Non-empty student names accepting arbitrary international Unicode characters.
- Attendance validation within [0.0, 100.0] as finite numbers.
- Subject score validation rejecting out-of-range, NaN, and positive/negative infinity.
- Support for documented absence indicators (`ABS`, `ABSENT`) while rejecting unstandardized codes.

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
- **Per-Subject Passing Thresholds:** Verified `subject_pass_overrides` enforce course-specific passing cutoffs (e.g., 45% in Math while other subjects require 40%).
- **Attendance Warning Policy:** Verified toggle (`enable_attendance_warning`) controls alert indicators without causing academic failure.
- **CLI String Parsing:** Verified `parse_grade_boundaries_string()` correctly constructs validated policies from CLI `--grade-boundaries` arguments.
- **Exact Boundary Preservation:** Verified full precision `raw_percentage` prevents premature rounding at pass/fail and grade boundaries (`39.996%` $\rightarrow$ FAIL, `40.0%` $\rightarrow$ PASS, `79.999%` $\rightarrow$ B+).
- **Direct Invocation Fail-Safe Validation:** Strict validation inside `evaluate_students()` rejects corrupted data with `ValueError`.

### 2.4 Statistical Analytics (`tests/test_analytics.py`)
- Class averages, medians, standard deviations, extremes, and pass rates.
- Difficulty ranking (Rank 1 = most challenging).
- Deterministic multi-key tie-breaking leaderboard.
- Transparent academic attention indicators.
- Departmental comparative analytics.

### 2.5 Security & Sanitization (`tests/test_security.py`)
- Formula injection (CWE-1236) neutralization on export.
- File size, dimension, and binary executable upload constraints.

### 2.6 Concurrency & Session State Integrity (`tests/test_sessions.py`)
- Thread-safe isolation and zero cross-contamination.
- Deterministic MD5 dataset fingerprinting and state reset on dataset modification.
- Automated result invalidation (`is_analysis_stale`) on configuration mutation (grade boundaries, subject max marks, per-subject thresholds, attendance settings).
- One-click reset clears institutional metadata, datasets, and configuration widgets.

---

## 3. Discovered Anomalies & Applied Resolutions

1. **Premature Rounding Before Pass/Fail & Grade Evaluation (Fix 02.1):**
   - *Problem:* `round(raw_percentage, 2)` before grade lookup and pass threshold checking caused near-boundary scores to round up.
   - *Fix:* Separated `raw_percentage` (unrounded float) used for all grade assignment, pass evaluation, rankings, and attention checks, reserving `percentage` strictly for display. Implemented `is_greater_or_close(val, threshold, tol=1e-12)`.
2. **Silent Zero-Coercion in Direct Evaluation (Fix 02.1):**
   - *Problem:* Calling `evaluate_students()` without prior `validate_dataset()` silently converted unparseable strings, missing values, NaNs, and Infs to 0.0.
   - *Fix:* Added strict fail-safe validation directly inside `evaluate_students()`, raising clear `ValueError` exceptions on corrupted data.
3. **Rigid Predefined Grade Scale in UI (Fix 03):**
   - *Problem:* Streamlit UI had hardcoded grade boundaries, preventing non-K-12 institutions (like universities using O, E, A, B, C, P, F) from using the platform.
   - *Fix:* Implemented dynamic grade boundary configuration, presets (`Default EduMetrics`, `Example School`, `Example College`), add/remove tier controls, and live policy preview in Tab 2.
4. **Attendance Warning Conflation with Academic Failure (Fix 03):**
   - *Problem:* Potential ambiguity between attendance warnings and academic pass/fail status.
   - *Fix:* Strictly decoupled attendance warnings as administrative/pastoral indicators that never cause academic failure unless explicitly mandated by academic pass thresholds.

---

## 4. Performance Benchmarks

- **CLI Execution Time (25 records, 6 subjects):** ~0.04 seconds.
- **Full Test Suite Execution Time (116 tests):** 1.78 seconds.
- **Memory Footprint:** Less than 45 MB peak RAM during full evaluation.
