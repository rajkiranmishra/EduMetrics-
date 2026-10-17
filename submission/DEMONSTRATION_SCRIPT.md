# EduMetrics — 3–5 Minute Demonstration Outline 🎙️
### Live Presentation & Video Walkthrough Script for Academic Evaluation

**Target Duration:** 3 to 5 minutes  
**Presenter:** Rajkiran Mishra  
**Evaluator Audience:** EWB Courses Faculty, Evaluators & Academic Reviewers  
**Demonstration Scope:** Standalone Python CLI, NumPy/Pandas Analytical Engine, Streamlit Web Dashboard, Formula Injection Defense, and Academic Attention Heuristics  

---

## ⏱️ Presentation Timeline at a Glance

| Segment | Timing | Topic | Primary Screen / Artifact |
| :---: | :---: | :--- | :--- |
| **1** | 0:00 – 0:30 | **Introduction & Problem Statement** | Slide / README Overview |
| **2** | 0:30 – 1:30 | **Pure Python CLI Demonstration** | Terminal: `python main.py` |
| **3** | 1:30 – 2:45 | **Interactive Web Dashboard & Policy Configuration** | Browser: `Upload & Configure` |
| **4** | 2:45 – 3:45 | **Analytics, Rankings & Academic Attention** | Browser: `Dashboard` & `Attention` |
| **5** | 3:45 – 4:30 | **Defensive CSV Export, Audit Reports & Reset** | Browser: `Reports` & Excel View |
| **6** | 4:30 – 5:00 | **Conclusion & Quality Verification** | Terminal: `pytest -v` (134 tests) |

---

## 🎙️ Spoken Script & Action Walkthrough

### Segment 1: Introduction & Problem Statement (0:00 – 0:30)
- **Spoken:**
  > *"Good day, respected evaluators. My name is Rajkiran Mishra, and today I am demonstrating EduMetrics—an academic performance analytics platform developed for the EWB Courses capstone assignment.*
  > 
  > *In educational institutions, calculating student grades across spreadsheets often leads to skewed results when courses have mixed maximum marks, fails to enforce dual-layer pass rules, and exposes educators to spreadsheet formula injection exploits. EduMetrics solves these challenges through a modular, headless Python analytics engine that operates both as a standalone terminal CLI and an interactive web dashboard."*

---

### Segment 2: Pure Python CLI Execution (0:30 – 1:30)
- **Action:** Open terminal and run:
  ```bash
  python main.py --file data/sample_school.csv
  ```
- **Spoken:**
  > *"First, let us examine the mandatory Python CLI engine in `main.py`. The engine requires zero web dependencies and relies purely on Python, NumPy, and Pandas.*
  > 
  > *Notice that upon loading `sample_school.csv`, the engine automatically validates schema integrity, detects all 5 courses, and validates every mark. It computes proportional percentages, letter grades, class averages, standard deviation, and difficulty rankings using NumPy.*
  > 
  > *Now, let us test the college dataset with custom institutional metadata, mixed maximum marks (100 for theory, 50 for labs), and custom grade boundaries:"*
- **Action:** Run:
  ```bash
  python main.py --file data/sample_college.csv \
    --institution "National Tech Institute" \
    --level "College" \
    --program "B.Tech CSE" \
    --term "Semester IV" \
    --grade-boundaries "Distinction:85,First:65,Second:50,Pass:40,Fail:0" \
    --subject-pass-overrides "Algorithms:45" \
    --export college_report.csv
  ```
- **Spoken:**
  > *"Notice how the CLI correctly identifies lab courses with 50 maximum marks, applies proportional normalization, preserves leading zeros in student IDs (`001`, `002`), and exports an audit-ready, formula-defused CSV report."*

---

### Segment 3: Interactive Web Dashboard & Policy Configuration (1:30 – 2:45)
- **Action:** Switch to browser displaying `http://localhost:8501` (or deployed public URL).
- **Spoken:**
  > *"Now let us turn to the interactive Streamlit web dashboard. In accordance with strict privacy principles, the dashboard operates with zero permanent database storage—all calculations exist ephemerally in active session memory.*
  > 
  > *Under the 'Upload & Configure' tab, we can load a dataset with 1 click. Let's load the built-in School dataset.*
  > 
  > *The configuration is structured into clean sections:*
  > 1. *We can enter institutional metadata: Springfield Academy, Grade 10.*
  > 2. *Column mappings are automatically detected.*
  > 3. *Course maximum marks and individual passing thresholds can be adjusted.*
  > 4. *In the Grading Policy editor, we can choose presets or dynamically add or remove grade levels. Notice that adding or removing tiers preserves our previous edits with live validation.*
  > 5. *In the Attendance Policy, warning cutoffs are decoupled from academic scores.*
  > 
  > *Let's click 'Run Academic Analysis'. If we ever change a threshold later, the system automatically marks the analysis stale to prevent data inconsistency."*

---

### Segment 4: Analytics, Rankings & Academic Attention Flags (2:45 – 3:45)
- **Action:** Click **"📊 Performance Dashboard"** tab, then **"📚 Subject Analysis"**, then **"🔍 Student Explorer"**, then **"⚠️ Academic Attention"**.
- **Spoken:**
  > *"Once evaluated, the Performance Dashboard provides an executive summary: Total Students (20), 80% Pass Rate, 71.1% Class Average, and a deterministic leaderboard using multi-column tie breaking.*
  > 
  > *Under 'Subject Analysis', each course is ranked by difficulty based on pass rates and averages.*
  > 
  > *Under 'Student Explorer', educators can search for students. Even if a user enters special punctuation like brackets or wildcards, the search handles it safely without crashing.*
  > 
  > *Crucially, in the 'Academic Attention' tab, EduMetrics surfaces students who need early support using transparent, rule-based heuristics:*
  > - *'Conceptual Support Needed' flags students with high attendance ($\ge 85\%$) but low scores ($< 50\%$). They are engaged, but struggling with core concepts.*
  > - *'Critical Intervention' flags chronic absenteeism compounded by failing scores.*
  > - *'Subject-Specific Remediation' flags students who are strong overall but failed a single stumbling-block course."*

---

### Segment 5: Defensive Report Export & Privacy Model (3:45 – 4:30)
- **Action:** Click **"📥 Reports & Export"** tab. Show the text summary preview and click **"⬇️ Download Sanitized CSV"**.
- **Spoken:**
  > *"In the Reports & Export tab, educators can download two artifacts:*
  > 1. *A comprehensive summary text audit report including institutional details, active policies, and statistical tables.*
  > 2. *A sanitized CSV report.*
  > 
  > *To protect educators against CSV Formula Injection (CWE-1236), EduMetrics automatically sanitizes every exported cell. If an untrusted cell begins with `=`, `+`, `-`, `@`, `\t`, `\r`, or `%`—even with leading spaces—the engine prepends a single quote, ensuring Microsoft Excel and Apple Numbers display it strictly as harmless text.*
  > 
  > *Finally, clicking 'Start New Analysis / Reset' in the sidebar completely clears session memory, guaranteeing no data persists between uses."*

---

### Segment 6: Conclusion & Quality Verification (4:30 – 5:00)
- **Action:** Switch back to terminal and run `pytest -v`.
- **Spoken:**
  > *"To verify quality and reliability, EduMetrics includes a comprehensive automated test suite of 134 tests covering data loading, academic validation, grading precision, security defenses, CLI execution, and multi-user concurrency.*
  > 
  > *As you can see, all 134 tests pass cleanly with 100% success rate across Python 3.9, 3.10, and 3.11.*
  > 
  > *In conclusion, EduMetrics demonstrates the full potential of Python, NumPy, and Pandas in solving a real-world educational challenge with academic rigor, security defense, and user-centric design. Thank you, and I look forward to your questions."*
