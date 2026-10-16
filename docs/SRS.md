# Software Requirements Specification (SRS)
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.3.0  
**Target Release:** EduMetrics V1 (Fix 03 Hardening)  
**Date:** October 2026  
**Status:** Approved Baseline  

---

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements for **EduMetrics V1**, a lightweight, security-conscious academic performance analytics platform. EduMetrics enables educators to upload student performance datasets, validate academic integrity constraints, configure custom grading policies, compute statistical performance distributions, and export sanitized reports.

### 1.2 Scope
EduMetrics V1 provides:
- A standalone, zero-dependency Python command-line interface (`main.py`) satisfying core course requirements.
- An interactive, session-ephemeral web dashboard (`app.py`) built with Streamlit.
- In-memory data validation, normalization, and statistical computation.
- Flexible institutional metadata, dynamic subject configuration, customizable grade boundaries, and grading presets.
- Protection against Denial of Service (file/row limits) and spreadsheet formula injection (CWE-1236).

*Out-of-Scope for V1:* User authentication, persistent relational databases, multi-tenant cloud storage, and predictive machine learning models.

---

## 2. Stakeholders & User Personas

| Role | Description | Primary Needs |
| :--- | :--- | :--- |
| **School Teacher** | Primary/Secondary educator managing class section marks. | Quick upload, automatic total and percentage calculations, grade assignment, identification of failing students, custom school grading scale. |
| **College Professor** | Higher education faculty handling courses with theory (100 marks) and labs (50 marks). | Heterogeneous mark normalization, college grading presets (O, E, A, B, C, P, F), departmental comparisons, identifying single-subject outliers for remedial classes. |
| **Academic Coordinator** | Department head or dean monitoring cohort-wide outcomes. | Pass rate distribution, subject difficulty rankings, attendance correlation, downloadable audit summaries with institutional metadata. |

---

## 3. Functional Requirements (FR)

### FR-1: Data Ingestion & Schema Support
- **FR-1.1:** The system shall ingest academic records from CSV format, supporting standard and multiline quoted fields.
- **FR-1.2:** The system shall read student identifiers as strings, preserving leading zeros (e.g., `"0042"`).
- **FR-1.3:** The system shall support flexible column mapping for Student ID, Name, Department (optional), Attendance %, and dynamic subject count ($N \ge 1$).
- **FR-1.4:** The system shall detect and decode UTF-8, UTF-8-BOM, and Latin-1 character encodings.
- **FR-1.5:** The system shall reject empty CSV files, empty/whitespace-only column headers, and duplicate headers (including duplicates after whitespace normalization).
- **FR-1.6:** The system shall enforce consistent row lengths and reject malformed quoted records without silently discarding data.

### FR-2: Data Validation & Integrity
- **FR-2.1:** The system shall verify the presence of all mapped mandatory columns (including mapped subject columns) before initiating row validation.
- **FR-2.2:** The system shall enforce non-empty, unique Student Identifiers using case-insensitive collision detection while preserving original string casing.
- **FR-2.3:** The system shall enforce non-empty Student Names, permitting legitimate international Unicode names, accents, hyphens, and apostrophes.
- **FR-2.4:** The system shall enforce finite numerical score boundaries $0.0 \le \text{mark} \le \text{SubjectMaxMark}$ where $\text{SubjectMaxMark} > 0$.
- **FR-2.5:** The system shall enforce finite numerical attendance boundaries $0.0 \le \text{attendance} \le 100.0$.
- **FR-2.6:** The system shall strictly reject non-finite numerical representations (`NaN`, `Inf`, `-Inf`, `Infinity`) in marks, attendance, max marks, and grading thresholds.
- **FR-2.7:** The system shall distinguish empty mark cells (flagged as missing score validation errors) from explicit institutional absence markers (`ABS`, `ABSENT`), which are evaluated as 0.0 marks and tracked separately in diagnostic audit fields (`absent_subjects`, `absent_subject_count`).
- **FR-2.8:** The system shall provide structured error messages citing specific row numbers and column names.

### FR-3: Academic Normalization & Grading Engine
- **FR-3.1:** The system shall compute total obtained marks and total possible marks.
- **FR-3.2:** The system shall calculate normalized overall percentage:
  $$\text{Percentage} = \left( \frac{\sum \text{Marks Obtained}}{\sum \text{Maximum Possible Marks}} \right) \times 100$$
- **FR-3.3:** The system shall support configurable grade brackets (e.g., A+, A, B+, B, C, D, F) and enforce monotonic ordering.
- **FR-3.4:** The system shall evaluate subject-level pass/fail independently against a configurable subject cutoff (default: 40%).
- **FR-3.5:** The system shall evaluate aggregate pass/fail independently against a configurable aggregate cutoff (default: 40%).
- **FR-3.6:** The system shall flag students who fail with detailed failure diagnostics (e.g., `"Failed in: Mathematics"`).

### FR-4: Statistical & Cohort Analytics
- **FR-4.1:** The system shall compute class average, median, standard deviation, minimum score, and maximum score.
- **FR-4.2:** The system shall calculate overall class pass percentage and grade distribution counts.
- **FR-4.3:** The system shall compute subject-wise metrics: average score, median, min, max, pass rate, and difficulty ranking (Rank 1 = hardest).
- **FR-4.4:** The system shall rank top performers deterministically with multi-key tie-breaking: Percentage $\rightarrow$ Attendance $\rightarrow$ Student ID.
- **FR-4.5:** The system shall compute departmental comparisons (average score, pass rate, attendance) when department data is provided.

### FR-5: Academic Attention Indicators
- **FR-5.1:** The system shall surface students meeting transparent, rule-based attention criteria:
  - *Conceptual Support:* Attendance $\ge 85\%$ and Score $< 50\%$.
  - *Critical Intervention:* Attendance $< 75\%$ and Score $< 50\%$.
  - *Subject Outlier:* Single failed subject with remaining subject average $\ge 65\%$.
  - *Borderline Pass:* $40.0\% \le \text{Score} < 45.0\%$ with PASS status.

### FR-6: Security & Export Protections
- **FR-6.1:** The system shall reject files exceeding 2 MB, 5,000 rows, or 30 columns.
- **FR-6.2:** The system shall reject non-text/binary files containing null bytes.
- **FR-6.3:** The system shall neutralize formula injection triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) on all exported CSV cells by prepending a single quote (`'`).

### FR-7: Institutional Metadata Configuration
- **FR-7.1:** The system shall accept optional institutional metadata fields:
  - Institution Name (e.g., "Springfield Academy")
  - Academic Level (`School`, `College`, `University`, `Other`)
  - Class, Program, or Course Name (e.g., "Grade 10-A", "B.Tech CSE")
  - Academic Term or Semester (e.g., "Semester 1", "Fall 2026")
- **FR-7.2:** Configured institutional metadata shall be included in generated text summaries and export audit headers.
- **FR-7.3:** Metadata shall reside strictly within transient session state and must never be persisted to disk or databases in V1.
- **FR-7.4:** Resetting the session or starting a new analysis shall purge all configured institutional metadata.

### FR-8: Custom Grade Boundaries & Presets
- **FR-8.1:** The system shall support custom letter grade labels and associated percentage cutoffs.
- **FR-8.2:** The system shall permit adding and removing grade tiers within a reasonable bound (2 to 12 levels).
- **FR-8.3:** The system shall strictly validate grading policies:
  - Reject duplicate grade labels (case-insensitive).
  - Reject non-finite, NaN, or infinite thresholds.
  - Require thresholds to lie strictly within $[0.0, 100.0]$.
  - Require strict descending monotonic order.
  - Require the lowest grade tier to begin strictly at $0.0\%$.
- **FR-8.4:** The system shall assign letter grades based on unrounded percentages (`raw_percentage`), ensuring exact boundary compliance.
- **FR-8.5:** The system shall provide selectable, editable institutional presets (`Default EduMetrics`, `Example School`, `Example College`).
- **FR-8.6:** The system shall render a live policy preview displaying all active grade tiers and passing rules.

### FR-9: Heterogeneous Subjects & Per-Subject Passing Overrides
- **FR-9.1:** The system shall detect subject columns dynamically from the uploaded CSV dataset.
- **FR-9.2:** The system shall support custom maximum possible marks per subject and compute normalized percentages via maximum-marks-weighted proportional normalization.
- **FR-9.3:** The system shall support optional per-subject passing thresholds (`subject_pass_overrides`), falling back to the default subject passing cutoff when an override is not specified.

### FR-10: Attendance Policy & Decoupled Warnings
- **FR-10.1:** The system shall provide a configurable attendance warning percentage cutoff (default: $75.0\%$).
- **FR-10.2:** The system shall provide an enable/disable toggle for attendance warning indicators.
- **FR-10.3:** The system shall strictly decouple attendance warnings from academic grading: low attendance flags are pastoral/administrative warnings and must never trigger academic failure unless explicitly required by an academic policy.

---

## 4. Non-Functional Requirements (NFR)

- **NFR-1 (Portability):** The application shall run locally on macOS, Linux, and Windows without binary OS dependencies.
- **NFR-2 (Stateless Core):** The core calculation engine shall have zero imports of Streamlit or web frameworks, enabling headless CLI execution and testing.
- **NFR-3 (Privacy):** No uploaded student data shall be persisted to disk or databases. All records shall reside strictly in transient session memory.
- **NFR-4 (Performance):** A dataset of 1,000 student records shall be validated, evaluated, and analyzed in under 2.0 seconds on standard consumer hardware.
- **NFR-5 (Testability):** All analytical and validation rules shall achieve 100% automated test coverage under `pytest`.
- **NFR-6 (Usability):** The web dashboard shall provide clear empty states, error diagnostics in plain English, and one-click session resets.
- **NFR-7 (Configuration Integrity):** Any mutation of institutional metadata, subject parameters, or grading policies shall automatically invalidate previously computed analysis results (`is_analysis_stale`).

---

## 5. Acceptance Criteria

1. Standalone CLI `main.py` executes successfully on `data/sample_school.csv` and `data/sample_college.csv` with support for all new configuration flags (`--institution`, `--level`, `--program`, `--term`, `--preset`, `--grade-boundaries`, `--subject-pass-overrides`, `--disable-attendance-warning`).
2. All 116 automated tests in `tests/` pass with zero failures.
3. Student IDs with leading zeros (`"001"`) retain exact formatting in all views and exports.
4. Exported CSV files with malicious formulas are defused per CWE-1236.
5. Streamlit web application organizes configuration into 7 distinct sections with live preview, preset switching, and real-time validation.
6. Changing grade boundaries, subject parameters, or attendance thresholds invalidates previous analysis results.
7. Reset purges all session state, uploaded data, and institutional configurations.
