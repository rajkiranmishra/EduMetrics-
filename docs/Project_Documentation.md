# Student Performance Analytics System
## Project Documentation (EWB Courses Assignment)

---

### 1. Project Title
**EduMetrics — Student Performance Analytics System**

---

### 2. Objective
The objective of this project is to develop a reliable, maintainable, institutional-flexible, and security-conscious academic performance analytics platform. The system empowers educators to:
- Ingest student performance datasets in CSV format with resilient schema mapping.
- Configure institutional context (institution name, academic level, program/class name, academic term).
- Define custom grade boundaries and select from institutional presets (`Default EduMetrics`, `Example School`, `Example College`).
- Automatically validate data types, score boundaries, attendance ranges, and identifier uniqueness.
- Compute totals, averages, and normalized percentages when subjects have varying maximum marks.
- Configure per-subject passing thresholds and decoupled attendance warning policies.
- Assign institutional letter grades and determine dual-layer pass/fail statuses based on configurable rules.
- Identify class averages, extremes, subject-wise bottlenecks, and students needing academic attention.
- Provide both a headless, zero-dependency command-line interface (CLI) and an interactive web dashboard with zero server-side storage of confidential records.

---

### 3. Technologies Used
- **Programming Language:** Python 3 (3.9+)
- **Core Numerical Calculations:** NumPy (for statistical operations: mean, median, standard deviation, extremes)
- **Data Ingestion & Transformation:** Pandas (for DataFrame processing, filtering, grouping, and CSV export)
- **Web Dashboard:** Streamlit (for interactive web presentation, 7 configuration sections, session-ephemeral controls, and charts)
- **Automated Testing:** pytest (unit testing, validation testing, security checks, and concurrency testing)
- **Version Control & CI:** Git, GitHub, and GitHub Actions

---

### 4. Dataset Description
EduMetrics includes two deterministic, fictional datasets representing different tiers of academic institutions:

#### A. School Dataset (`data/sample_school.csv`)
- **Cohort Size:** 20 fictional student records across 2 class sections (Section A and Section B).
- **Attributes:**
  - `student_id`: Unique identifier (e.g., `SCH-101` to `SCH-120`).
  - `student_name`: Fictional student names.
  - `department`: Class section (`Section A` or `Section B`).
  - `attendance`: Attendance percentage (ranging from 61.0% to 97.5%).
  - 5 Subjects (Max Marks: 100 each): `English`, `Mathematics`, `Science`, `Social_Studies`, `Second_Language`.

#### B. College Dataset (`data/sample_college.csv`)
- **Cohort Size:** 25 fictional student records across 3 engineering departments (`CSE`, `IT`, `ECE`).
- **Attributes:**
  - `student_id`: 3-digit strings preserving leading zeros (`"001"`, `"002"`, ..., `"025"`).
  - `student_name`: Fictional student names.
  - `department`: Academic department.
  - `attendance`: Attendance percentage (55.0% to 98.0%).
  - 6 Subjects with Heterogeneous Maximum Marks (Total Possible: 450 marks):
    - Theory Courses (Max: 100): `Data_Structures`, `Algorithms`, `Operating_Systems`.
    - Lab / Practical Courses (Max: 50): `Database_Lab`, `Web_Tech_Lab`, `Project_Phase_1`.

---

### 5. Implementation
The project follows a **Headless Modular Monolith** architecture with strict separation of concerns:
- **`security/upload_checks.py`:** Enforces computational bounds (2 MB size limit, 5,000 rows max, 30 columns max) and defuses CSV spreadsheet formula injection (CWE-1236) by neutralizing `=`, `+`, `-`, `@`, `\t`, `\r` prefixes with a prepended single quote (`'`).
- **`core/loader.py`:** Reads raw CSV bytes safely, detects character encodings (UTF-8, UTF-8-BOM, Latin-1 fallback), preserves string identifiers with leading zeros, detects empty or whitespace-only headers, rejects duplicate headers (including duplicates after whitespace normalization), and verifies consistent row lengths.
- **`core/validation.py`:** Validates schema integrity, missing mapped subject and metadata columns, unique case-insensitive student IDs, non-empty student names (supporting international Unicode characters), finite attendance percentages ($0.0 \le \text{att} \le 100.0$), finite subject scores, and rejects non-finite numerical representations (`NaN`, `Inf`, `-Inf`, `Infinity`). Flags empty mark cells as missing data while supporting explicit absence markers (`ABS`, `ABSENT`). Returns structured errors referencing specific spreadsheet rows and columns.
- **`core/grading.py`:** Implements:
  - `InstitutionMetadata`: Dataclass capturing institution name, academic level, program name, and academic term.
  - `GRADING_PRESETS`: Registry of illustrative institutional grading policies (`Default EduMetrics`, `Example School`, `Example College`).
  - Proportional score normalization:
    $$\text{Percentage} = \left( \frac{\sum \text{Marks Obtained}}{\sum \text{Maximum Possible Marks}} \right) \times 100$$
  - Customizable grade boundaries with strict validation (2 to 12 tiers, finite $[0.0, 100.0]$, strict descending monotonic order, unique labels, lowest boundary at $0.0\%$).
  - Per-subject passing thresholds (`subject_pass_overrides`) evaluated independently per course.
  - Dual-layer pass/fail criteria (requiring passing marks in every subject as well as aggregate threshold).
  - Decoupled attendance warning policy: low attendance triggers pastoral alerts but never causes academic failure.
  - Full numerical precision (`raw_percentage` unrounded float) for all grade assignments, subject-level passing, aggregate passing, tie-broken rankings, and attention triggers, while reserving 2-decimal rounding (`percentage`) solely for user presentation. Machine precision tolerance (`1e-12` in `is_greater_or_close`) defends exact mathematical boundaries against IEEE 754 binary representation artifacts. Fail-safe direct validation rejects invalid, non-numeric, non-finite, negative, or exceeding scores, invalid attendance, and missing student IDs/names with `ValueError`.
- **`core/analytics.py`:** Uses NumPy and Pandas to compute class-level metrics (mean, median, standard deviation, extremes, pass percentage), subject difficulty rankings, departmental comparisons, deterministic tie-broken rankings (using full precision `raw_percentage`), and rule-based academic attention flags.
- **`core/reports.py`:** Packages results into sanitized CSV files and human-readable plain-text audit summaries including `[0] INSTITUTION DETAILS` when supplied.
- **`core/session_state.py`:** Manages multi-user isolation, deterministic dataset fingerprinting (MD5), tracking configuration parameters in `create_analysis_config`, and automated staleness invalidation (`is_analysis_stale`).
- **`main.py`:** Standalone CLI driver executing the entire analysis headlessly via `argparse`, supporting institutional metadata flags, presets, custom grade boundaries, per-subject cutoffs, and export.
- **`app.py`:** Interactive Streamlit web application providing 7 clean configuration sections (Institution Details, Column Mapping, Subject Configuration, Grading Policy, Attendance Policy, Policy Preview, Run Analysis), metric cards, charts, student search, attention diagnostics, and downloads.

---

### 6. Key Features
1. **Zero Streamlit Coupling in Core Engine:** The entire analytical engine runs headlessly in scripts and automated tests without web dependencies.
2. **Institutional Flexibility:** Supports optional institutional metadata (institution name, academic level, program name, academic term) that formats seamlessly into reports.
3. **Custom Grade Boundaries & Presets:** Educators can customize letter grade labels and thresholds, choose presets, and add/remove grade tiers with live preview and validation.
4. **Proportional Normalization for Mixed Maximum Marks:** Correctly weights subjects with different maximums (e.g., 50 vs. 100 marks).
5. **Per-Subject Passing Thresholds:** Supports individual subject cutoff overrides (e.g., 45% in Math, 40% in others).
6. **Decoupled Attendance Warnings:** Configurable attendance warning threshold that alerts educators without unfairly failing students academically.
7. **Dual-Layer Institutional Pass/Fail Logic:** Distinguishes students who pass overall aggregate percentage but fail an individual required subject, providing precise diagnostic reasons.
8. **Deterministic Ranking & Tie-Breaking:** Resolves ties using explicit criteria: Percentage (descending) $\rightarrow$ Attendance (descending) $\rightarrow$ Student ID (ascending).
9. **Transparent Academic Attention Indicators:** Rule-based heuristics flag students who need help:
   - *Conceptual Support:* High attendance ($\ge 85\%$) but low score ($< 50\%$).
   - *Critical Intervention:* Low attendance ($< 75\%$) and low score ($< 50\%$).
   - *Subject-Specific Remediation:* Passing well overall but failing a single course.
   - *Borderline At-Risk:* Passing within 5 percentage points of failure.
10. **CSV Formula Injection Sanitization:** Neutralizes spreadsheet execution exploits on export.
11. **Ephemeral Zero-Storage Privacy:** In the web UI, data exists exclusively in transient session memory.
12. **Automatic Staleness Invalidation:** Prevents displaying outdated results when configuration or datasets change.

---

### 7. Output / Screenshots

#### CLI Formatted Execution Output with Institutional Metadata
```
==============================================================================
             EDUMETRICS — ACADEMIC PERFORMANCE ANALYTICS CLI
==============================================================================
[*] Ingesting academic dataset: data/sample_school.csv
[+] Successfully loaded 20 records across 9 columns.
[+] Identified 5 subjects: English (Max: 100), Mathematics (Max: 100), Science (Max: 100), Social_Studies (Max: 100), Second_Language (Max: 100)
[*] Validating dataset records against academic integrity constraints...
[+] Validation Passed cleanly with 0 errors and 0 warning(s).
[*] Computing normalized scores, grades, and pass/fail statuses...

[0] INSTITUTION DETAILS
  * Institution Name      : Springfield Academy
  * Academic Level        : School
  * Program / Course      : Grade 10-A
  * Term / Semester       : Semester 1

[1] APPLIED ACADEMIC POLICY
  * Grading Scale         : A+ (>=90.0%), A (>=80.0%), B (>=70.0%), C (>=60.0%), D (>=40.0%), F (>=0.0%)
  * Subject Pass Cutoff   : 40.0%
  * Aggregate Pass Cutoff : 40.0%
  * Attendance Warning    : <75.0% (Enabled)

[2] CLASS PERFORMANCE SUMMARY
  * Total Students        : 20
  * Passed Students       : 16 (80.0%)
  * Failed Students       : 4 (20.0%)
  * Class Average Score   : 71.05%
  * Class Median Score    : 73.10%
  * Std Deviation         : 18.18%
  * Highest Performer     : Ishita Gupta (SCH-106) - 95.0%
  * Lowest Performer      : Farhan Akhtar (SCH-117) - 36.2%
  * Class Mean Attendance : 85.9%
  * Attendance Warnings   : 4 students
------------------------------------------------------------------------------
[3] GRADE DISTRIBUTION
  Grade A  :   3 students ( 15.0%) ###
  Grade A+ :   4 students ( 20.0%) ####
  Grade B  :   1 students (  5.0%) #
  Grade C  :   1 students (  5.0%) #
  Grade D  :   3 students ( 15.0%) ###
  Grade F  :   1 students (  5.0%) #
------------------------------------------------------------------------------
[4] SUBJECT-WISE PERFORMANCE & DIFFICULTY RANKING
  Subject              Max   Pass Cut   Avg Score   Pass %   Min    Max    Rank 
  -------------------------------------------------------------------------------
  Mathematics          100   40.0%      69.0        85.0     30.0   98.0   #1   
  Science              100   40.0%      70.7        90.0     34.0   96.0   #2   
  English              100   40.0%      71.5        95.0     35.0   94.0   #3   
  Second_Language      100   40.0%      72.0        95.0     36.0   95.0   #4   
  Social_Studies       100   40.0%      72.0        100.0    40.0   94.0   #5   

==============================================================================
  TOP 5 PERFORMERS LEADERBOARD (DETERMINISTIC RANKING)
==============================================================================
 rank student_id   student_name department  percentage grade  attendance
    1    SCH-106   Ishita Gupta  Section A        95.0    A+        95.0
    2    SCH-112 Tanvi Deshmukh  Section B        92.0    A+        97.5
    3    SCH-102     Diya Patel  Section A        91.8    A+        96.0
    4    SCH-101   Aarav Sharma  Section A        90.0    A+        94.5
    5    SCH-116    Rhea Kapoor  Section B        89.8     A        93.0
```

---

### 8. Final Outcome
- The core analytical requirements of the EWB assignment were fully met using Python, NumPy, and Pandas.
- The platform operates as both a standalone CLI and an interactive web application.
- 134 automated tests pass cleanly with 100% success rate across Python 3.9, 3.10, and 3.11.
- Two distinct fictional datasets demonstrate flexibility across K-12 and university academic structures.
- All export files are protected against spreadsheet formula execution.

---

### 9. Challenges & Learning
1. **Pandas Automatic Header Mangling:**
   - *Challenge:* Pandas silently renames duplicate column headers (e.g. renaming a second `'Math'` column to `'Math.1'`), bypassing simple set comparison checks.
   - *Learning:* Built pre-ingestion byte inspection using Python's `csv.reader` directly on the raw file bytes, catching duplicates before DataFrame creation.
2. **Preserving String Identifiers:**
   - *Challenge:* Default CSV readers convert numeric strings like `"0042"` to integers `42`, stripping institutional leading zeros.
   - *Learning:* Enforced string data types on identifier columns during ingestion and validated preservation through dedicated unit tests.
3. **Academic Score Normalization:**
   - *Challenge:* Computing unweighted averages across courses with unequal maximum marks distorts student percentages.
   - *Learning:* Implemented proportional sum normalization ($\frac{\sum \text{obtained}}{\sum \text{max}} \times 100$), ensuring correct percentage calculation regardless of course weights.
4. **Resisting Premature Complexity:**
   - *Challenge:* Temptation to introduce premature microservices, databases, or black-box machine learning.
   - *Learning:* Focused on a clean, modular monolith with transparent heuristics, ensuring high testability, fast execution, and zero compliance liabilities for student records.
5. **Configurable Dynamic Grade Boundary Validation:**
   - *Challenge:* Allowing end users to define arbitrary grade tiers risks non-monotonic boundaries, duplicate grade labels, gaps, or omitting the zero baseline.
   - *Learning:* Implemented formal policy validation requiring strict descending monotonicity, distinct labels, and a mandatory 0.0% floor, pairing it with live preview cards and automated staleness detection so stale results are never shown.

---

### 10. GitHub Repository
- **Current Repository:** [https://github.com/rajkiranmishra/private](https://github.com/rajkiranmishra/private)
- **Target Repository Name:** `edumetrics` *(Renaming pending user approval)*
- **Working Branch:** `fix/v1-hardening`
- **License:** MIT License
- **Automated Testing:** GitHub Actions CI (`.github/workflows/ci.yml`)
