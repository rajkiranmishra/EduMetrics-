# EduMetrics 🎓
### Academic Performance Analytics Platform

[![EduMetrics CI](https://github.com/rajkiranmishra/edumetrics/actions/workflows/ci.yml/badge.svg)](https://github.com/rajkiranmishra/edumetrics/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests: 31 Passed](https://img.shields.io/badge/Tests-31%20Passed-success.svg)](docs/TEST_REPORT.md)

**EduMetrics** is a production-minded academic analytics platform that empowers teachers, professors, and academic coordinators to validate student performance datasets, configure institutional grading policies, compute statistical cohort distributions, and export sanitized reports without requiring spreadsheet programming.

Built with **Python, NumPy, Pandas, and Streamlit**, EduMetrics satisfies all requirements of the **EWB Courses "Student Performance Analytics System"** assignment while establishing a security-conscious, modular foundation.

---

## 📑 Table of Contents
- [Problem Statement](#-problem-statement)
- [Key Features](#-key-features)
- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Sample Datasets](#-sample-datasets)
- [Installation & Local Setup](#-installation--local-setup)
- [Usage: Standalone CLI](#-usage-standalone-cli)
- [Usage: Web Dashboard](#-usage-web-dashboard)
- [Academic Grading Methodology](#-academic-grading-methodology)
- [Security & Privacy Controls](#-security--privacy-controls)
- [Automated Testing](#-automated-testing)
- [Project Documentation Index](#-project-documentation-index)
- [Limitations & Future Roadmap](#-limitations--future-roadmap)
- [License](#-license)

---

## 🎯 Problem Statement

Educators frequently compile student marks across disparate spreadsheets with manual, error-prone calculations:
1. **Unequal Maximum Marks:** Calculating totals across mixed courses (e.g., 100-mark theory vs. 50-mark lab) often leads to skewed unweighted averages.
2. **Rigid Policies:** Off-the-shelf software rarely handles dual-layer passing rules (e.g., requiring a passing mark in *every* course in addition to an overall aggregate percentage).
3. **Lack of Instant Diagnostics:** Instructors struggle to quickly surface students who need help (e.g., students with high attendance but low scores, or students failing exactly one subject).
4. **Data Privacy & Ingestion Fragility:** Heavy enterprise software requires complex procurement and passwords, while ad-hoc spreadsheets risk spreadsheet formula execution exploits (CWE-1236).

EduMetrics resolves these challenges through a **zero-login, session-ephemeral web dashboard** and a **headless standalone CLI** sharing a pure functional analytics engine.

---

## ✨ Key Features

- **Dual Operating Modes:** Run headlessly via terminal CLI (`main.py`) or interactively in a web browser (`app.py`).
- **Flexible Column Mapping:** Resiliently maps custom column names for Student ID, Name, Department, Attendance, and dynamic subject lists.
- **Heterogeneous Score Normalization:** Proportional normalization across subjects with different maximum possible marks.
- **Dual-Layer Institutional Pass/Fail Rules:** Independent subject-level and aggregate-level thresholds with detailed failure diagnostics.
- **Deterministic Ranking:** Multi-key tie-breaking (Percentage $\rightarrow$ Attendance $\rightarrow$ Student ID).
- **Rule-Based Academic Attention Flags:** Transparent heuristics identifying students needing tutoring, chronic absenteeism intervention, or single-course remediation.
- **CSV Formula Injection Defusion (CWE-1236):** Neutralizes formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) on export.
- **Privacy by Design:** Zero permanent database storage in V1; records exist only in transient session memory.

---

## 🏗️ Architecture Overview

EduMetrics uses a **Headless Modular Monolith** architecture. The core computational engine has **zero imports of Streamlit**, ensuring it can be tested and executed headlessly.

```
edumetrics/
├── .github/workflows/ci.yml       # Automated GitHub Actions CI
├── .streamlit/config.toml          # Streamlit theme & upload constraints
├── core/
│   ├── loader.py                  # Encoding detection, safe CSV ingestion
│   ├── validation.py              # Schema, score bounds, duplicate checks
│   ├── grading.py                 # Normalization, grade brackets, pass/fail
│   ├── analytics.py               # NumPy/Pandas statistics, ranking, attention
│   └── reports.py                 # Sanitized CSV and text summary generation
├── security/
│   └── upload_checks.py           # 2MB file limits, row/col caps, formula defusion
├── data/
│   ├── sample_school.csv          # Fictional K-12 dataset (20 students)
│   └── sample_college.csv         # Fictional College dataset (25 students, mixed max marks)
├── docs/
│   ├── SRS.md                     # Software Requirements Specification
│   ├── ARCHITECTURE.md            # Component diagrams & future DB design
│   ├── SECURITY.md                # Threat model (STRIDE) & disclosure policy
│   ├── TEST_REPORT.md             # Test results, benchmarks, and bug fixes
│   └── Project_Documentation.md   # EWB Courses assignment compliance document
├── tests/                         # 31 automated pytest unit & security tests
├── app.py                         # Streamlit Web Application (UI layer only)
├── main.py                        # Standalone CLI Entrypoint
├── requirements.txt               # Pinned dependencies
├── README.md                      # Project documentation
└── LICENSE                        # MIT License
```

---

## 🛠️ Tech Stack

- **Python 3.9+** — Core programming language.
- **NumPy** — Fast numerical calculations (mean, median, standard deviation, extremes).
- **Pandas** — DataFrames, schema validation, grouping, and CSV export.
- **Streamlit** — Interactive presentation layer with session-ephemeral state.
- **pytest** — Automated test suite with 100% pass rate across 31 tests.

---

## 📊 Sample Datasets

EduMetrics includes two fictional datasets in `data/`:

| Dataset | Cohort | Description | Structure |
| :--- | :--- | :--- | :--- |
| **`data/sample_school.csv`** | 20 students | K-12 School model across 2 sections (`Section A`, `Section B`). | 5 subjects with uniform 100 max marks (`English`, `Mathematics`, `Science`, `Social_Studies`, `Second_Language`). |
| **`data/sample_college.csv`** | 25 students | University engineering model across 3 departments (`CSE`, `IT`, `ECE`). | Leading zero IDs (`"001"`), 3 theory courses (Max: 100), and 3 lab/project courses (Max: 50). Total: 450 marks. |

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/rajkiranmishra/edumetrics.git
cd edumetrics
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Usage: Standalone CLI

Run the analytics engine directly from your terminal:

```bash
# Run on the School dataset (default)
python main.py --file data/sample_school.csv

# Run on the College dataset with custom top performers and CSV export
python main.py --file data/sample_college.csv --top 5 --export analyzed_report.csv
```

### CLI Command Options
- `--file`, `-f`: Path to the CSV dataset (default: `data/sample_school.csv`).
- `--id-col`: Column header for Student ID (default: `student_id`).
- `--name-col`: Column header for Student Name (default: `student_name`).
- `--attendance-col`: Column header for Attendance % (default: `attendance`).
- `--dept-col`: Column header for Department (default: `department`).
- `--subject-pass`: Minimum % required to pass individual subjects (default: `40.0`).
- `--aggregate-pass`: Minimum overall aggregate % required to pass (default: `40.0`).
- `--attendance-warning`: Attendance % threshold for warning (default: `75.0`).
- `--top`: Number of top performers to display (default: `5`).
- `--export`, `-e`: Optional path to save evaluated and formula-defused CSV.

---

## 🌐 Usage: Web Dashboard

Launch the Streamlit interactive dashboard locally:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

### Web Workflow:
1. **Overview & Samples:** Read the privacy notice and download sample CSV templates.
2. **Upload & Configure:** Upload your CSV (or load a sample with 1 click), map columns, configure maximum marks, and set grading policies.
3. **Performance Dashboard:** View class averages, pass rates, grade distribution charts, and leaderboards.
4. **Subject Analysis:** Inspect pass rates and difficulty rankings per subject.
5. **Student Explorer:** Search, filter, and sort student-level performance records.
6. **Academic Attention:** Review students flagged for conceptual tutoring, chronic absenteeism, or subject remediation.
7. **Reports & Export:** Download sanitized CSV reports (with formula defusion) and text summaries.
8. **Reset Session:** Click "Start New Analysis / Reset" to clear all session memory.

---

## 📐 Academic Grading Methodology

### 1. Proportional Score Normalization
$$\text{Normalized Percentage} = \left( \frac{\sum_{i=1}^M \text{Marks Obtained}_i}{\sum_{i=1}^M \text{Maximum Possible Marks}_i} \right) \times 100$$

### 2. Default Institutional Grade Scale
- **A+:** $\ge 90.0\%$
- **A:** $80.0\% - 89.99\%$
- **B+:** $70.0\% - 79.99\%$
- **B:** $60.0\% - 69.99\%$
- **C:** $50.0\% - 59.99\%$
- **D:** $40.0\% - 49.99\%$
- **F:** $< 40.0\%$

### 3. Dual-Layer Pass/Fail Rule
A student passes if and only if:
1. Every subject score meets or exceeds the subject pass threshold (default: 40%).
2. Overall normalized percentage meets or exceeds the aggregate pass threshold (default: 40%).

### 4. Transparent Academic Attention Indicators
- **Conceptual Support Needed:** Attendance $\ge 85\%$ and Score $< 50\%$.
- **Critical Intervention:** Attendance $< 75\%$ and Score $< 50\%$.
- **Subject-Specific Remediation:** Failed exactly 1 subject, while remaining subjects average $\ge 65\%$.
- **Borderline / At-Risk:** Passing within 5 percentage points of failure ($40\% \le \text{Score} < 45\%$).

---

## 🔒 Security & Privacy Controls

- **CWE-1236 Formula Injection Defense:** All exported text cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are neutralized by prepending a single quote (`'`), protecting educators opening files in Microsoft Excel or Apple Numbers.
- **Resource Limits:** Hard caps of 2 MB file size, 5,000 rows, and 30 columns prevent memory exhaustion DoS attacks.
- **Binary Rejection:** Null bytes and binary executable magic headers are rejected before parsing.
- **Zero Disk Retention:** Uploaded student data lives strictly within volatile session memory.

---

## 🧪 Automated Testing

EduMetrics includes a comprehensive test suite of **31 automated tests** covering all modules:

```bash
pytest -v
```

```
============================== test session starts ==============================
collected 31 items

tests/test_analytics.py ...................................... [ 16%]
tests/test_grading.py ........................................ [ 35%]
tests/test_loader.py ......................................... [ 54%]
tests/test_reports.py ........................................ [ 61%]
tests/test_security.py ....................................... [ 77%]
tests/test_sessions.py ....................................... [ 80%]
tests/test_validation.py ..................................... [100%]

============================== 31 passed in 0.06s ==============================
```

---

## 📚 Project Documentation Index

- [SRS.md](docs/SRS.md) — Comprehensive Software Requirements Specification.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Component diagrams, data flow, and future relational DB schema.
- [SECURITY.md](docs/SECURITY.md) — Threat model (STRIDE), trust boundaries, and vulnerability reporting.
- [TEST_REPORT.md](docs/TEST_REPORT.md) — Test execution evidence, bug fixes, and performance benchmarks.
- [Project_Documentation.md](docs/Project_Documentation.md) — EWB Courses assignment compliance document (10 headings).

---

## 🔮 Limitations & Future Roadmap

### Tested Scope (V1)
- Tested with cohort sizes of 20 to 5,000 records.
- Zero login / anonymous session-ephemeral mode.
- High-fidelity formula-defused CSV exports.

### Planned for V2 (Post-Submission)
- Multi-tenant institutional accounts with role-based access control (Admin, Coordinator, Teacher).
- Persistent storage using PostgreSQL (see [schema design in ARCHITECTURE.md](docs/ARCHITECTURE.md#4-future-relational-database-architecture-v2-roadmap)).
- Longitudinal student performance tracking across academic terms.
- Server-side PDF export generation.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
