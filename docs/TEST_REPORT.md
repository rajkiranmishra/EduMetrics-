# Automated Test Execution & Quality Assurance Report
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.0.0  
**Date of Execution:** 14 October 2026  
**Test Framework:** `pytest 8.4.2` / `Python 3.9.6` / `macOS Darwin ARM64`  
**Overall Status:** PASSED (31 of 31 tests passing, 100% success rate)  

---

## 1. Executive Summary

| Test Suite | File | Tests Run | Passed | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Loader & Ingestion** | `tests/test_loader.py` | 6 | 6 | 0 | 0.01s |
| **Academic Validation** | `tests/test_validation.py` | 6 | 6 | 0 | 0.01s |
| **Grading & Policy** | `tests/test_grading.py` | 6 | 6 | 0 | 0.01s |
| **Statistical Analytics** | `tests/test_analytics.py` | 5 | 5 | 0 | 0.01s |
| **Reporting & Formatting** | `tests/test_reports.py` | 2 | 2 | 0 | 0.01s |
| **Security & Sanitization**| `tests/test_security.py` | 5 | 5 | 0 | 0.01s |
| **Session Isolation** | `tests/test_sessions.py` | 1 | 1 | 0 | 0.01s |
| **TOTAL** | | **31** | **31** | **0** | **0.06s** |

---

## 2. Test Execution Details by Suite

### 2.1 Ingestion & Loader (`tests/test_loader.py`)
- `test_sample_datasets_load_successfully`: Verified `data/sample_school.csv` (20 rows) and `data/sample_college.csv` (25 rows) load with correct column structures.
- `test_leading_zero_preservation`: Verified student ID `"001"` remains string length 3 and is not converted to integer `1`.
- `test_duplicate_column_headers_rejected`: Verified raw CSV duplicate headers raise `IngestionError`.
- `test_empty_file_rejected`: Verified 0-byte upload raises `IngestionError`.
- `test_encoding_detection`: Verified UTF-8, UTF-8-BOM, and Latin-1 accented characters ("Renée") decode cleanly.
- `test_missing_file_raises_ingestion_error`: Verified clean error handling when a non-existent path is provided.

### 2.2 Academic Validation (`tests/test_validation.py`)
- `test_valid_dataset_passes_validation`: Verified well-formed data passes with zero errors.
- `test_missing_required_column`: Verified missing mandatory columns (e.g. Student ID) are caught.
- `test_duplicate_student_id_rejected`: Verified duplicate ID rows are flagged with line references.
- `test_out_of_range_attendance`: Verified values `< 0`, `> 100`, or strings are rejected.
- `test_out_of_range_subject_score`: Verified scores exceeding subject maximum (e.g., 55/50 in lab) are flagged.
- `test_absent_mark_allowed_without_error`: Verified `"ABS"` strings are accepted as excused/absent (0 score).

### 2.3 Grading & Normalization (`tests/test_grading.py`)
- `test_monotonic_grade_boundaries_validation`: Verified disordered grade brackets (e.g., B higher than A) raise `PolicyConfigurationError`.
- `test_lowest_grade_must_start_at_zero`: Verified omission of 0% baseline raises `PolicyConfigurationError`.
- `test_assign_grade_to_percentage`: Verified boundary thresholds map to exact letter grades (A+, A, B, etc.).
- `test_proportional_normalization_heterogeneous_marks`: Verified mixed 100-mark theory and 50-mark lab courses compute correct proportional percentages.
- `test_subject_level_fail_with_high_aggregate`: Verified student with 60% aggregate who fails one subject (<40%) receives overall `FAIL` status.
- `test_attendance_warning_flag`: Verified attendance below 75% triggers `attendance_warning = True`.

### 2.4 Statistical Analytics (`tests/test_analytics.py`)
- `test_class_summary_metrics`: Verified class averages, medians, standard deviations, extremes, and pass rates.
- `test_subject_analytics_and_difficulty_ranking`: Verified subject metrics and difficulty ranking (Rank 1 = hardest).
- `test_deterministic_top_performers_tie_breaking`: Verified multi-key sorting (Percentage $\rightarrow$ Attendance $\rightarrow$ Student ID).
- `test_academic_attention_indicators`: Verified all 4 transparent heuristics (Conceptual Support, Critical Intervention, Subject Outlier, Borderline Pass) flag matching students.
- `test_department_summary`: Verified group aggregation by department.

### 2.5 Security & Sanitization (`tests/test_security.py`)
- `test_defuse_formula_injection_triggers`: Verified `=`, `+`, `-`, `@`, `\t`, `\r` prefixes are neutralized with prepended `'`.
- `test_generate_sanitized_csv_protects_exported_cells`: Verified full DataFrame export sanitization.
- `test_file_size_limits`: Verified rejection of files exceeding 2 MB.
- `test_binary_and_executable_rejection`: Verified rejection of null bytes and executable headers.
- `test_csv_dimension_bounds`: Verified enforcement of 5,000 row and 30 column limits.

### 2.6 Concurrency & Session Isolation (`tests/test_sessions.py`)
- `test_concurrent_session_isolation`: Executed 10 interleaved threads across 2 different datasets and policies simultaneously. Verified 0% data cross-contamination.

---

## 3. Discovered Anomalies & Applied Resolutions

During test execution, 3 specific edge cases were caught and resolved:

1. **Pandas Header Mangling on Duplicate Columns:**
   - *Problem:* Pandas `pd.read_csv` silently renames duplicate headers from `['Math', 'Math']` to `['Math', 'Math.1']`.
   - *Fix:* Added raw byte inspection using Python's `csv.reader` on the initial line before passing to Pandas, guaranteeing clean rejection of duplicate column headers.
2. **Numpy Boolean Identity Comparison:**
   - *Problem:* Comparing `np.bool_(False) is False` evaluates to `False` in Python due to object identity mismatch.
   - *Fix:* Replaced identity `is` with standard boolean comparison `assert not val` and cast internal boolean flags with `bool()`.
3. **Attention Rule Precedence Collision:**
   - *Problem:* Student with attendance 88% and score 43% satisfied both Rule 1 (Attendance $\ge$ 85% + Score $<$ 50%) and Rule 4 (Borderline Pass 40-44%).
   - *Fix:* Clarified rule definitions and calibrated test fixtures so each test student uniquely validates their targeted attention category.

---

## 4. Performance Benchmarks

- **CLI Execution Time (25 records, 6 subjects):** ~0.04 seconds.
- **Full Test Suite Execution Time (31 tests):** 0.06 seconds.
- **Memory Footprint:** Less than 45 MB peak RAM during full evaluation.
