# System Architecture & Technical Design
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.0.0  
**Target Release:** EduMetrics V1  
**Architecture Pattern:** Headless Modular Monolith with Ephemeral Presentation  

---

## 1. High-Level Architectural Overview

EduMetrics is organized as a **Headless Modular Monolith**. The core business logic, validation engine, and statistical calculations are completely isolated from the presentation layer. Neither `core/` nor `security/` imports `streamlit`.

```
+-------------------------------------------------------------------------------+
|                             PRESENTATION LAYER                                |
|                                                                               |
|   +------------------------------------+    +-----------------------------+   |
|   |         Streamlit Web App          |    |       Standalone CLI        |   |
|   |             (app.py)               |    |          (main.py)          |   |
|   |  - Session-scoped state (ephemeral)|    |  - Headless argparse        |   |
|   |  - Interactive widgets & mapping   |    |  - Formatted terminal table |   |
|   |  - Visual charts & CSV download    |    |  - Direct exit codes (0/1)  |   |
|   +-----------------+------------------+    +--------------+--------------+   |
+---------------------|--------------------------------------|------------------+
                      |                                      |
                      +-------------------+------------------+
                                          |
+-----------------------------------------v-------------------------------------+
|                              CORE ENGINE LAYER                                |
|                        (Pure Python / Pandas / NumPy)                         |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   | 1. Security & Ingestion Checks (security/upload_checks.py)             |   |
|   |    - File size limit (< 2 MB)        - Byte header inspection         |   |
|   |    - Row limit (< 5,000 rows)        - Column count limit (< 30 cols) |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |                                       |
|   +-----------------------------------v-----------------------------------+   |
|   | 2. CSV Loader & Normalizer (core/loader.py)                           |   |
|   |    - Encoding fallback (UTF-8, Latin-1)  - String IDs (preserve zeros)|   |
|   |    - Whitespace trimming                 - Deduplication of headers   |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |                                       |
|   +-----------------------------------v-----------------------------------+   |
|   | 3. Academic Validator (core/validation.py)                            |   |
|   |    - Missing mandatory fields        - Score range validation (0..max)|   |
|   |    - Attendance bounds (0..100%)     - Duplicate student ID checks    |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |                                       |
|   +-----------------------------------v-----------------------------------+   |
|   | 4. Policy & Grading Engine (core/grading.py)                          |   |
|   |    - Heterogeneous subject maximums  - Proportional percentage        |   |
|   |    - Configurable grade boundaries   - Subject & aggregate pass/fail  |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |                                       |
|   +-----------------------------------v-----------------------------------+   |
|   | 5. Statistical Analytics Engine (core/analytics.py)                   |   |
|   |    - Class-level metrics (mean, med) - Subject-wise distributions     |   |
|   |    - Deterministic tie-break ranking - Rule-based attention flags     |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |                                       |
|   +-----------------------------------v-----------------------------------+   |
|   | 6. Reporting & Export Sanitizer (core/reports.py)                     |   |
|   |    - CSV formula injection defusion  - Structured summary packaging   |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

---

## 2. Module Responsibilities

| Module | Location | Purpose & Architectural Invariants |
| :--- | :--- | :--- |
| **Security** | `security/upload_checks.py` | Enforces byte size limits, checks magic bytes against binary/null payloads, caps row/column counts, and provides formula injection defusion. |
| **Loader** | `core/loader.py` | Safe byte reading, character encoding detection (UTF-8, BOM, Latin-1), string ID preservation, raw duplicate header detection. |
| **Validation** | `core/validation.py` | Validates presence of mandatory columns, duplicate IDs, attendance range [0, 100], and score boundaries [0, max_mark]. Returns structured dataclasses. |
| **Grading** | `core/grading.py` | Proportional score normalization across mixed maximum marks, monotonic grade boundary validation, dual-layer pass/fail logic, attendance warnings. |
| **Analytics** | `core/analytics.py` | Pure NumPy/Pandas calculation of class averages, medians, standard deviations, extremes, pass rates, subject difficulty rankings, tie-broken leaderboards, and rule-based attention indicators. |
| **Reporting** | `core/reports.py` | Sanitized CSV generation (defusing spreadsheet formulas per CWE-1236) and formatted plain-text ASCII reports. |
| **CLI** | `main.py` | Headless command-line entrypoint using `argparse`. Zero web framework dependency. |
| **Web UI** | `app.py` | Streamlit web application. Manages UI tabs, session state, interactive widgets, and downloads. |

---

## 3. State Management & Session Lifecycle

In EduMetrics V1:
1. **Zero Server-Side Storage:** No student records are written to disk or database.
2. **Session Ephemerality:** All data loaded via the web dashboard is stored exclusively within Streamlit's `st.session_state`.
3. **Session Dereferencing:** When a user closes their browser tab or clicks the **"Start New Analysis / Reset"** button, all `session_state` keys are purged, releasing DataFrames for Python garbage collection.
4. **Thread Safety & Multi-User Isolation:** Core calculation functions accept `(df, policy)` as explicit arguments and return new objects. Because there are no global mutable variables, concurrent user requests execute completely independently.

---

## 4. Future Relational Database Architecture (V2 Roadmap)

For future institutional releases requiring persistent storage, multi-tenancy, and authenticated role-based access control, the following normalized relational schema is designed:

```sql
-- Core Institutions and Tenancy
CREATE TABLE institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('ADMIN', 'COORDINATOR', 'INSTRUCTOR')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (institution_id, email)
);

CREATE TABLE academic_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    name VARCHAR(64) NOT NULL, -- e.g. "Fall 2026", "Semester 1"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    term_id UUID NOT NULL REFERENCES academic_terms(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL, -- e.g. "Class 10-A", "B.Tech CSE Year 3"
    department VARCHAR(64)
);

CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    student_identifier VARCHAR(64) NOT NULL, -- e.g. "SCH-101", "001"
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (institution_id, student_identifier)
);

CREATE TABLE enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    attendance_percentage NUMERIC(5,2) CHECK (attendance_percentage BETWEEN 0 AND 100),
    UNIQUE (class_id, student_id)
);

CREATE TABLE subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    max_marks NUMERIC(6,2) NOT NULL CHECK (max_marks > 0),
    pass_mark NUMERIC(6,2) NOT NULL CHECK (pass_mark <= max_marks)
);

CREATE TABLE marks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    score NUMERIC(6,2) CHECK (score >= 0),
    is_absent BOOLEAN DEFAULT FALSE,
    UNIQUE (enrollment_id, subject_id)
);

CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Architectural Trade-offs Summary

1. **Modular Monolith vs. Microservices:**
   - *Chosen:* Single modular Python package.
   - *Rationale:* Microservices would introduce network serialization latency, operational deployment complexity, and RPC fragility with zero performance benefit for class-sized datasets.
2. **Session Memory vs. Database:**
   - *Chosen:* In-memory transient session storage for V1.
   - *Rationale:* Protects user privacy, eliminates compliance liability (FERPA/GDPR) on a public server, and ensures zero database maintenance.
3. **Headless Engine vs. Streamlit Coupling:**
   - *Chosen:* Strict decoupling.
   - *Rationale:* Enables CLI execution (`main.py`) for automated batch jobs, automated testing with `pytest`, and easy migration to alternative frontends (e.g., FastAPI + React) in the future.
