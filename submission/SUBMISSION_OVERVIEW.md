# EWB Courses Assignment Submission Package 🎓
## Student Performance Analytics System — EduMetrics

**Candidate Name:** Rajkiran Mishra  
**Course / Track:** EWB Courses — Advanced Python & Data Analytics  
**Project Title:** EduMetrics — Academic Performance Analytics Platform  
**Target Deadline:** 26 October 2026  
**Repository:** [https://github.com/rajkiranmishra/private](https://github.com/rajkiranmishra/private)  
**Working Branch:** `fix/v1-hardening`  
**License:** MIT License  

---

## 📑 Deliverables Cross-Check Matrix (EWB Assignment Requirements)

| Mandatory Requirement | Implemented Solution | Verification Evidence |
| :--- | :--- | :--- |
| **1. Python Fundamentals** | Modular architecture, custom exceptions, dataclasses, pure functions | `core/grading.py`, `core/loader.py`, `core/validation.py` |
| **2. CSV File Ingestion** | Robust loader with encoding detection, leading-zero preservation, structural checks | `core/loader.py`, `tests/test_loader.py` |
| **3. Data Validation** | Missing value detection, non-finite rejection (`NaN`, `Inf`), duplicate ID checks | `core/validation.py`, `tests/test_validation.py` |
| **4. NumPy Calculations** | Class mean, median, standard deviation, extremes, unrounded arrays | `core/analytics.py`, `tests/test_analytics.py` |
| **5. Pandas Analytics** | Proportional score normalization, cohort grouping, student explorer filters | `core/grading.py`, `core/analytics.py` |
| **6. Academic Analytics** | Subject difficulty ranking, deterministic leaderboards, attention heuristics | `core/analytics.py`, `tests/test_analytics.py` |
| **7. Standalone Python CLI** | Pure headless execution via `main.py` with argument parsing and export | `main.py`, `tests/test_cli.py` |
| **8. Web Dashboard** | Interactive Streamlit presentation layer (`app.py`) with 8 dedicated tabs | `app.py`, `tests/test_sessions.py` |
| **9. Automated Testing** | Comprehensive test suite (134 automated unit, security, and session tests) | `tests/`, `docs/TEST_REPORT.md` |
| **10. Documentation** | Complete SRS, Architecture, Security, User Guide, and Project Documentation | `docs/` index |

---

## 1. Project Overview & Problem Statement

### Problem Statement
Educators routinely manage student marks using manual, error-prone spreadsheets:
1. **Heterogeneous Maximum Marks:** Combining courses with varying total marks (e.g. 100-mark theory vs. 50-mark lab) often results in skewed, unweighted averages.
2. **Rigid Institutional Grading:** Real institutions employ dual-layer pass/fail criteria (requiring students to pass *every* course in addition to an overall aggregate percentage) and customizable grade thresholds.
3. **Lack of Early Diagnostic Attention:** Teachers struggle to quickly distinguish engaged students who are struggling academically (high attendance, low score) from chronically absent students.
4. **Data Security & Formula Injection (CWE-1236):** Unsanitized CSV exports can trigger remote command execution in Microsoft Excel, Apple Numbers, and LibreOffice Calc.

### Proposed Solution
**EduMetrics** is an academic performance analytics platform designed specifically for schools, colleges, and universities. It provides:
- A **standalone Python CLI (`main.py`)** for zero-dependency headless evaluation.
- An **interactive Streamlit web dashboard (`app.py`)** for visual exploration.
- A **zero-storage ephemeral memory model** ensuring compliance with student privacy expectations.

---

## 2. System Architecture & Technology Stack

### Technology Stack
- **Language:** Python 3.9+
- **Numerical Processing:** NumPy
- **Data Manipulation:** Pandas
- **Presentation Layer:** Streamlit (UI layer only; zero imports in core engine)
- **Quality Assurance:** pytest (134 automated tests)
- **Security:** Pure Python CWE-1236 formula defusion and multi-layer ingestion bounds

### Component Topology
```
                     +---------------------------------------+
                     |         EduMetrics CLI (main.py)      |
                     +-------------------+-------------------+
                                         |
+------------------------------------+   |   +------------------------------------+
|   Streamlit Dashboard (app.py)     |   |   |        pytest Test Suite (134)     |
+-----------------+------------------+   |   +-----------------+------------------+
                  |                      |                     |
                  +-------------------+  |  +------------------+
                                      |  |  |
                                      v  v  v
+---------------------------------------------------------------------------------+
|                                 CORE ENGINE                                     |
|                                                                                 |
|  +--------------------+  +--------------------+  +---------------------------+  |
|  |   core/loader.py   |  | core/validation.py |  |     core/grading.py       |  |
|  | - Encoding detect  |  | - Unique IDs       |  | - Proportional norm       |  |
|  | - Leading zeros    |  | - Finite numbers   |  | - Custom grade brackets   |  |
|  | - Bounds checks    |  | - Absence markers  |  | - Dual-layer pass/fail    |  |
|  +--------------------+  +--------------------+  +---------------------------+  |
|                                                                                 |
|  +--------------------+  +--------------------+  +---------------------------+  |
|  | core/analytics.py  |  |  core/reports.py   |  |  core/session_state.py    |  |
|  | - NumPy statistics |  | - Formula defusion |  | - Session isolation      |  |
|  | - Difficulty rank  |  | - Sanitized CSV    |  | - Stale invalidation      |  |
|  | - Attention flags  |  | - ASCII reports    |  | - State reset             |  |
|  +--------------------+  +--------------------+  +---------------------------+  |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  |                      security/upload_checks.py                            |  |
|  |   - 2MB limit, 5000 rows max, 30 cols max, 512-char cells, Bidi rejection |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
```

---

## 3. Key Feature Breakdown

1. **Dual Operating Modes:** Execute directly in terminal via `main.py` or visually in browser via `app.py`.
2. **Proportional Normalization:** Correctly computes aggregate percentage across courses with mixed maximum marks:
   $$\text{Percentage} = \left( \frac{\sum \text{Marks Obtained}}{\sum \text{Maximum Marks}} \right) \times 100$$
3. **Institutional Metadata Context:** Configure institution name, academic level (School, College, University, Other), program, and academic term.
4. **Custom Grade Boundaries & Presets:** Supports 2 to 12 configurable grade tiers with validation and presets (`Default EduMetrics`, `Example School`, `Example College`).
5. **Dual-Layer Pass/Fail Rule:** Requires passing marks in *every* enrolled course (with per-subject cutoff overrides) as well as the aggregate passing threshold.
6. **Decoupled Attendance Policy:** Configurable attendance warning cutoff ($< 75\%$) with toggleable alerts that never cause academic failure.
7. **Transparent Academic Attention Indicators:** Rule-based heuristics classifying struggling students into actionable intervention categories.
8. **Deterministic Tie-Breaking Leaderboard:** Multi-key ranking: Percentage $\rightarrow$ Attendance $\rightarrow$ Student ID.
9. **CWE-1236 Formula Injection Defense:** Defuses formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`, `%`) on CSV export by prepending single quotes.
10. **Zero-Storage Privacy Architecture:** Processes data exclusively in transient session memory; zero permanent database persistence.

---

## 4. Benchmark Datasets

The submission package includes two representative academic datasets:

| Dataset | Records | Structure | Key Edge Cases Tested |
| :--- | :---: | :--- | :--- |
| **`sample_school.csv`** | 20 students | 5 uniform 100-mark subjects across 2 class sections | High performers, failing students, attendance warnings, single-subject failures |
| **`sample_college.csv`** | 25 students | 3 theory subjects (100 marks) + 3 lab/project courses (50 marks) | Leading-zero IDs (`"001"`), mixed maximum marks, departmental comparison (`CSE`, `IT`, `ECE`) |

---

## 5. Installation & Verification Instructions

### Step 1: Clone Repository
```bash
git clone https://github.com/rajkiranmishra/private.git edumetrics
cd edumetrics
```

### Step 2: Set Up Python Environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run Automated Test Suite
```bash
pytest -v
```
*Expected Result: 134 passed in ~3.5 seconds with 100% pass rate.*

### Step 4: Execute Standalone CLI
```bash
# School dataset evaluation
python main.py --file data/sample_school.csv

# College dataset evaluation with metadata and CSV export
python main.py --file data/sample_college.csv \
  --institution "Apex Engineering College" \
  --level "College" \
  --program "B.Tech Computer Science" \
  --term "Semester IV" \
  --top 5 \
  --export analyzed_college_report.csv
```

### Step 5: Launch Web Dashboard
```bash
streamlit run app.py
```
*Access via browser at: `http://localhost:8501`.*

---

## 6. Testing Evidence Summary

- **Total Automated Tests:** **134 passed** across 8 test suites:
  - `tests/test_analytics.py`: 7 tests
  - `tests/test_cli.py`: 6 tests
  - `tests/test_grading.py`: 46 tests
  - `tests/test_loader.py`: 13 tests
  - `tests/test_reports.py`: 2 tests
  - `tests/test_security.py`: 13 tests
  - `tests/test_sessions.py`: 32 tests
  - `tests/test_validation.py`: 15 tests
- **Continuous Integration:** Verified on GitHub Actions across Python 3.9, 3.10, and 3.11.

---

## 7. Security & Privacy Considerations

- **Zero Hardcoded Credentials:** Audited git history confirms zero API keys, secrets, or passwords.
- **CSV Formula Injection Sanitization:** Defends against CWE-1236 across exported spreadsheets.
- **Ingestion Guardrails:** 2 MB file limit, 5,000 maximum rows, 30 maximum columns, 512-character cell limits.
- **Privacy Notice:** Explicitly advises users that the platform is designed for fictional, synthetic, or de-identified datasets.

---

## 8. Index of Submission Documents

- `submission/DEMONSTRATION_SCRIPT.md`: Concise 3–5-minute presentation script and oral examination outline.
- `docs/USER_GUIDE.md`: Comprehensive educator operational manual.
- `docs/DEPLOYMENT.md`: Streamlit Community Cloud and self-hosted deployment procedures.
- `docs/USER_VALIDATION.md`: Educator field validation package, questionnaire, and sample dataset.
- `docs/RELEASE_CHECKLIST.md`: Release gates and verification evidence.
- `docs/RELEASE_NOTES.md`: Official V1.0.0 release notes.
- `docs/SRS.md`: Software Requirements Specification.
- `docs/ARCHITECTURE.md`: Architecture specification and component diagrams.
- `docs/SECURITY.md`: Threat model (STRIDE) and security analysis.
- `docs/TEST_REPORT.md`: Comprehensive test execution evidence and benchmarks.
- `docs/Project_Documentation.md`: EWB Courses assignment compliance document (10 headings).
