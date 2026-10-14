# Security Policy & Threat Model
## EduMetrics — Academic Performance Analytics Platform

**Document Version:** 1.0.0  
**Target Release:** EduMetrics V1  
**Status:** Active Security Policy  

---

## 1. Threat Model (STRIDE Analysis)

EduMetrics implements defense-in-depth principles appropriate for an educational web analytics service.

| Category | Threat Description | Severity | Countermeasures Implemented |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Adversary attempts to impersonate another educator or forge user identity. | Low | EduMetrics V1 operates anonymously without user accounts or stored identities. Sessions are isolated per browser tab. |
| **Tampering** | Uploading malformed CSV files containing binary payloads, invalid characters, or SQL injection strings. | Medium | 1. Byte inspection rejects null bytes and binary magic headers.<br>2. Strict CSV parser bounds cells.<br>3. Zero `eval()` or `exec()` execution on input values. |
| **Repudiation** | Claiming an analytical calculation was computed under a different policy than actual. | Low | Exported reports embed an immutable audit summary with timestamp, record counts, and full grading policy thresholds. |
| **Information Disclosure** | Data from User Session A leaking into User Session B. | High | **Zero global mutable state.** Data exists strictly in `st.session_state` or local function scope. Thread concurrency tests (`test_sessions.py`) verify complete data isolation. |
| **Denial of Service (DoS)** | Exhausting server memory or CPU by uploading a multi-gigabyte file or 1,000,000 rows. | High | **Strict Resource Limits:**<br>- Maximum file size: **2 MB**<br>- Maximum row count: **5,000 rows**<br>- Maximum column count: **30 columns**<br>Files exceeding limits are rejected before memory allocation. |
| **Elevation of Privilege** | **CSV Formula Injection (CWE-1236):** Malicious CSV containing `=CMD|' /C calc'!A0` designed to execute commands when an educator opens exported CSV in Microsoft Excel or Apple Numbers. | High | **Formula Defusion:** In `core/reports.py`, all exported text fields starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are sanitized by prepending a single quote (`'`), neutralizing spreadsheet formula execution. |

---

## 2. Privacy by Design Principles

1. **Transient In-Memory Processing:** Student records uploaded to EduMetrics exist strictly within transient RAM for the duration of the user's active session.
2. **Zero Persistent Data:** No student names, marks, or identifiers are logged to server disks, databases, or external third-party analytics services.
3. **Session Dereferencing:** Closing the browser tab or clicking "Start New Analysis / Reset" purges the data from session memory.
4. **Fictional Data Standard:** The public demonstration repository contains only fictional datasets (`sample_school.csv`, `sample_college.csv`). Real identifiable student records must never be committed to source control.

---

## 3. Known Limitations (V1)

- **Unauthenticated Environment:** Because V1 does not require login, anyone with the public URL can use the analytics engine. Do not upload confidential student data covered by FERPA or GDPR without institutional hosting approval.
- **Shared Container Restarts:** On free cloud hosting tiers (Streamlit Community Cloud), containers periodically recycle. Active sessions will reset if the container reboots.

---

## 4. Responsible Vulnerability Disclosure

If you discover a security vulnerability in EduMetrics, please report it privately:
- **Email:** rajkiranmishra@example.com (or via private GitHub Security Advisory)
- **Response Target:** 48 hours for triage and acknowledgment.
- **Public Disclosure:** Please allow 14 days for mitigation before public discussion.
