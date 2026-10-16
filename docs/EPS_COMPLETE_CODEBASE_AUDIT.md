# EPS Complete Codebase Architecture & System Audit Report

**Project:** EPS — Exam Proctoring System  
**Audit & Verification Date:** October 15, 2026  
**Auditor:** Principal Software Architect & Senior Django Engineer  
**Codebase Root:** `C:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System`  
**Technology Stack:** Python 3.14.0, Django 6.1.1, SQLite 3, HTML5, CSS3, Modern ES6 JavaScript  

---

## 1. Executive Summary

A comprehensive architectural and operational codebase audit was conducted across the Exam Proctoring System (EPS). EPS is an institutional examination and browser-based proctoring platform developed for college evaluation and accredited academic environments.

The audit established that:
1. **Preserved Core Database:** `db.sqlite3` remains intact (434,176 bytes) with `PRAGMA integrity_check = ok` and all 5 user accounts preserved. Backups `db.sqlite3.backup_change_request` and `db.sqlite3.backup_20261015` (425,984 bytes each) are intact.
2. **Zero-Email Compliance:** Strictly zero external SMTP, sendmail, or third-party mailing libraries. All onboarding, approvals, alerts, and password assistance are mediated natively through in-app notifications and administrative review queues.
3. **Security Hardening:** The development session bypass endpoint (`/accounts/dev-session/<username>/`) has been completely eradicated from views and routing tables.
4. **Diagnostic Cleanliness:** `python manage.py check` reports `0 issues identified`.
5. **Database Migration State:** `python manage.py makemigrations --check --dry-run` reports `No changes detected`. All 23 migrations are marked `[X]`.
6. **Automated Verification:** The entire Django test suite executes cleanly with 38 passing tests out of 38 in 57.509 seconds (`Ran 38 tests in 57.509s - OK`).

---

## 2. Comprehensive Application Architecture

### 2.1 `accounts` App
- **Authentication & RBAC:**
  - Common login (`/accounts/login/`) with server-side role and status determination.
  - Central registration (`/accounts/register/`) featuring interactive role selection (Student and Teacher) with initial `pending` approval status.
  - Strict RBAC decorators: `@student_required`, `@teacher_required`, `@admin_required`.
- **Administrative Suite:**
  - Executive overview dashboard (`/accounts/admin/dashboard/`) with asymmetric Bento cards.
  - Real database analytics (`/accounts/admin/analytics/`).
  - Security audit ledger (`/accounts/admin/audit-logs/`) with actor, action, target, IP address, and details.
  - Student directory (`/accounts/admin/students/`) and Faculty directory (`/accounts/admin/teachers/`) with search, filter, sort, server-side pagination, and bulk suspend/activate actions.
  - Student dossier (`/accounts/admin/student/<id>/`) and Faculty dossier (`/accounts/admin/teacher/<id>/`).
  - Candidate approval queue (`/accounts/admin/student-approvals/`) and Faculty approval queue (`/accounts/admin/teacher-approvals/`).
  - Suspended accounts console (`/accounts/admin/suspended/`) with instant reactivation.
  - Decision history ledger (`/accounts/admin/approval-history/`).
  - Academic hierarchy: Departments (`/accounts/admin/departments/`) and Class Cohorts (`/accounts/admin/classes/`).
  - Governance policies (`/accounts/admin/policies/`), Backup ledger (`/accounts/admin/backup/`), and Security posture (`/accounts/admin/security/`).
- **Teacher Approval Queue:**
  - Departmental student review queue (`/accounts/teacher/student-approvals/`) allowing teachers to verify students in their own department.

### 2.2 `exams` App
- **Examination Lifecycle:**
  - Course Subject management (`/exams/subjects/`).
  - Question bank (`/exams/questions/`) supporting MCQ (single/multi-select), True/False, and Subjective Descriptive types.
  - Exam creation wizard (`/exams/create/`), editing (`/exams/<id>/edit/`), and detail configuration (`/exams/<id>/`).
  - Exam publishing gate: locks exam questions and emits notifications to eligible cohort candidates.
- **Candidate Delivery & Proctoring HUD:**
  - Student exam catalog (`/exams/my-exams/`).
  - Readiness pre-check (`/exams/<id>/instructions/`).
  - Live examination room (`/exams/attempt/<id>/`) featuring sticky countdown timer, question palette, autosave AJAX API, and local browser proctoring monitors (fullscreen lockdown, tab visibility change, webcam presence, dual face scan, and audio VU meter).
  - Telemetry event ingestion (`/exams/proctoring-event/`).
  - Submission confirmation (`/exams/attempt/<id>/submitted/`).
- **Administrative Examination Oversight:**
  - Master exam directory (`/exams/admin/all/`).
  - Master attempt ledger (`/exams/admin/attempts/`).
  - Live proctoring fleet monitor (`/exams/admin/proctoring/`).
  - Forensic incidents ledger (`/exams/admin/incidents/`).

### 2.3 `results` App
- **Grading & Score Calculation:**
  - Automated objective scoring for MCQ and True/False questions immediately upon submission.
  - Manual subjective essay grading console (`/results/grade/<attempt_id>/`) with answer key guidance and rubric scoring.
  - Publication restriction gate: candidates cannot view scores until the instructor sets `is_published=True`.
- **Candidate & Institutional Reporting:**
  - Student scorecard catalog (`/results/student/`) and itemized breakdown (`/results/student/<id>/`).
  - Teacher exam performance analytics (`/results/teacher/exam/<id>/`).
  - Administrative results overview (`/results/admin/overview/`).
  - Institutional CSV export center (`/results/admin/export/`) supporting downloads for student directories, faculty rosters, candidate scorecards, proctoring incident logs, and security audit trails.

---

## 3. Database State & Preservation Audit

```text
db.sqlite3: Size=434,176 bytes, PRAGMA Integrity=ok, Users=5
db.sqlite3.backup_change_request: Size=425,984 bytes, PRAGMA Integrity=ok, Users=5
db.sqlite3.backup_20261015: Size=425,984 bytes, PRAGMA Integrity=ok, Users=5
```

- **Active User Accounts:**
  - `admin` (Role: admin, Superuser: True)
  - `teacher_test_01` (Role: teacher, Status: approved)
  - `student_test_01` (Role: student, Status: approved)
  - `student_priya` (Role: student, Status: approved)
  - `prof_anita` (Role: teacher, Status: approved)
- **Integrity Status:** PRAGMA check returned `ok` across all files. Zero corruption, zero data loss.

---

## 4. Visual Verification Disclosure

> [!IMPORTANT]
> **Explicit Testing Disclosure:**
> Per the user's explicit directive to halt all screenshot capture scripts and headless browser automation, **automated visual browser screenshot testing is NOT TESTED.**
> The responsive layout architecture has been verified through **direct code review of CSS media queries and HTML templates**, ensuring responsive grid reflows, table scroll containment, and mobile drawer functionality across Desktop (1440px), Laptop (1280px), Tablet (768px), Mobile (390px), and Narrow Mobile (320-360px).
