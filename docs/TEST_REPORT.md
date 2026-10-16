# Automated Test Execution & Quality Assurance Report
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.3.0  
**Date of Execution:** 16 October 2026  
**Test Framework:** `pytest 8.4.2` / `Python 3.9.6` / `macOS Darwin ARM64`  
**Overall Status:** PASSED (101 of 101 tests passing, 100% success rate)  

---

## 1. Executive Summary

| Test Suite | File | Tests Run | Passed | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Loader & Ingestion** | `tests/test_loader.py` | 13 | 13 | 0 | 0.05s |
| **Academic Validation** | `tests/test_validation.py` | 15 | 15 | 0 | 0.08s |
| **Grading, Precision & Policy** | `tests/test_grading.py` | 33 | 33 | 0 | 0.12s |
| **Statistical Analytics** | `tests/test_analytics.py` | 7 | 7 | 0 | 0.03s |
| **Reporting & Formatting** | `tests/test_reports.py` | 2 | 2 | 0 | 0.02s |
| **Security & Sanitization**| `tests/test_security.py` | 5 | 5 | 0 | 0.02s |
| **Session Isolation & State** | `tests/test_sessions.py` | 26 | 26 | 0 | 1.30s |
| **TOTAL** | | **101** | **101** | **0** | **1.62s** |

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

### 2.3 Grading, Numerical Precision & Direct Evaluation (`tests/test_grading.py`)
- Monotonic grade boundaries and 0% baseline validation.
- Proportional normalization across heterogeneous course weights (100-mark theory vs 50-mark lab).
- Exact boundary preservation without premature rounding:
  - `39.996%` vs `40.0%` pass threshold $\rightarrow$ Strictly `FAIL`.
  - Exactly `40.0%` pass threshold $\rightarrow$ `PASS`.
  - Slightly above `40.0%` (`40.001%`) $\rightarrow$ `PASS`.
  - `79.999%` vs `80.0%` Grade A boundary $\rightarrow$ Strictly `B+` (not prematurely promoted to A).
  - Exactly `80.0%` $\rightarrow$ Grade `A`.
  - Subject-level threshold: `19.999/50.0` ($39.998\%$) $\rightarrow$ failed subject; `20.0/50.0` ($40.0\%$) $\rightarrow$ passed subject.
- Direct invocation fail-safe validation:
  - Rejection of non-numeric marks (`ValueError`).
  - Rejection of missing marks, `""`, `None`, and `NaN` (`ValueError`).
  - Rejection of `NaN`, `Inf`, and `-Inf` (`ValueError`).
  - Rejection of negative scores and scores exceeding subject maximum (`ValueError`).
  - Rejection of missing, non-numeric, or out-of-range attendance (`ValueError`).
  - Rejection of missing mandatory student IDs and names (`ValueError`).
  - Rejection of empty/invalid subject configurations and missing columns (`PolicyConfigurationError`).
  - Guarantee that input DataFrames are completely immutable and never modified in-place.
  - Deterministic ranking of top performers using unrounded `raw_percentage` precision to break ties.

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
- Invalidation of downstream results on parameter/mapping alterations.

---

## 3. Discovered Anomalies & Applied Resolutions

1. **Premature Rounding Before Pass/Fail & Grade Evaluation:**
   - *Problem:* `round(raw_percentage, 2)` before grade lookup and pass threshold checking caused near-boundary scores (e.g. 39.996% and 79.999%) to round up to 40.00% and 80.00%, falsely passing or promoting students.
   - *Fix:* Separated `raw_percentage` (unrounded float) used for all grade assignment, pass evaluation, rankings, and attention checks, reserving `percentage` strictly for display. Implemented `is_greater_or_close(val, threshold, tol=1e-12)` to defend against IEEE 754 machine representation artifacts without allowing genuinely sub-threshold values to pass.
2. **Silent Zero-Coercion in Direct Evaluation:**
   - *Problem:* Calling `evaluate_students()` without prior `validate_dataset()` silently converted unparseable strings, missing values, NaNs, and Infs to 0.0.
   - *Fix:* Added strict fail-safe validation directly inside `evaluate_students()`, raising clear `ValueError` exceptions on corrupted data.
3. **Absence Marker Separation:**
   - *Problem:* Risk of treating any missing or arbitrary text as an absence.
   - *Fix:* Strictly constrained supported absence markers to documented set `{"ABS", "ABSENT"}` and raised errors on unstandardized codes.

---

## 4. Performance Benchmarks

- **CLI Execution Time (25 records, 6 subjects):** ~0.04 seconds.
- **Full Test Suite Execution Time (101 tests):** 1.62 seconds.
- **Memory Footprint:** Less than 45 MB peak RAM during full evaluation.
