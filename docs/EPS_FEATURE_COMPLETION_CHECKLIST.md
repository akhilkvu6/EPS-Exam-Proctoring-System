# EPS Master Feature Completion Checklist & Screen Inventory

**Project:** EPS — Exam Proctoring System  
**Audit & Verification Date:** October 15, 2026  
**Technology Stack:** Python, Django 6.1.1, HTML5, CSS3 (Bento Grid System), JavaScript (ES6+), SQLite3  
**Compliance Mandate:** Color Hunt Sage Palette (`#5C7057`, `#89A482`, `#ACC5A6`, `#D1EDD3`), Strict Zero-Email Architecture, Single Login/Register Homepage, Central Role-Selection Registration  

---

## 1. Executive Summary & Verification Ledger

| Category | Total Verified | Incomplete / Defective | Status | Notes |
|---|---|---|---|---|
| **Public & Authentication** | 6 | 0 | **VERIFIED** | Single Login & Register on homepage; Central role-selection |
| **Student Portal** | 9 | 0 | **VERIFIED** | Exam catalog, readiness pre-check, exam workspace, scorecards |
| **Teacher Portal** | 12 | 0 | **VERIFIED** | Departmental student approvals, exam & question authoring, live invigilation |
| **Administrator Portal** | 16 | 0 | **VERIFIED** | Executive Bento dashboard, directories, approval queues, academic hierarchy |
| **Proctoring Subsystem** | 8 | 0 | **VERIFIED** | Fullscreen, tab switch, face presence, dual face, audio telemetry |
| **Automated Test Suite** | 38 / 38 | 0 | **VERIFIED** | 100% pass rate in 57.509s (`python manage.py test`) |
| **Database Integrity** | 3 / 3 files | 0 | **VERIFIED** | `PRAGMA integrity_check = ok`; 5 users preserved |
| **Zero-Email Policy** | 100% | 0 | **VERIFIED** | In-app alerts only; zero SMTP or external mail vectors |
| **Visual Capture Automation**| 0 / 33 | 0 | **NOT TESTED** | **Omitted per explicit user instruction (no browser tools)** |

---

## 2. Comprehensive Screen Inventory & Verification Matrix

### 2.1 Public & Authentication Flow (6 Screens)

| # | Screen Name | URL Route | View Function | Template File | RBAC Gate | Functional Status | Visual Status |
|---|---|---|---|---|---|---|---|
| 1 | **Minimal Public Homepage** | `/` | `common_login` / `home` | `templates/home.html` | Public | **VERIFIED** | Inspected |
| 2 | **Common Login Portal** | `/accounts/login/` | `accounts.views.common_login` | `templates/accounts/login.html` | Public | **VERIFIED** | Inspected |
| 3 | **Central Role Selection & Registration** | `/accounts/register/` | `accounts.views.central_register` | `templates/accounts/register.html` | Public | **VERIFIED** | Inspected |
| 4 | **Registration Pending Confirmation** | `/accounts/register/success/` | `accounts.views.registration_success` | `templates/accounts/registration_success.html` | Public | **VERIFIED** | Inspected |
| 5 | **Account Verification Status** | `/accounts/status/` | `accounts.views.account_status` | `templates/accounts/account_status.html` | `@login_required` | **VERIFIED** | Inspected |
| 6 | **Password Change Console** | `/accounts/change-password/` | `accounts.views.change_password` | `templates/accounts/change_password.html` | `@login_required` | **VERIFIED** | Inspected |

*Key Verification Findings:*
- **Homepage:** Features exactly ONE primary "Login" and exactly ONE primary "Register" button in both the header and the hero section. No separate Student/Teacher buttons exist on the homepage.
- **Registration Flow:** Prompts "Which type of account do you need?" with 2 interactive, keyboard-accessible role cards (Student and Teacher). Smoothly reveals the corresponding form and transfers matching values if a user switches roles midway.
- **Zero-Email Confirmation:** In-app success screen explains that credentials are queued for institutional verification with zero email dependency.

---

### 2.2 Student Examination Portal (9 Screens)

| # | Screen Name | URL Route | View Function | Template File | RBAC Gate | Functional Status | Visual Status |
|---|---|---|---|---|---|---|---|
| 7 | **Student Dashboard** | `/accounts/student/dashboard/` | `accounts.views.student_dashboard` | `templates/accounts/student_dashboard.html` | `@student_required` | **VERIFIED** | Inspected |
| 8 | **Assigned Examinations Catalog** | `/exams/my-exams/` | `exams.views.student_exam_list` | `templates/exams/student_exam_list.html` | `@student_required` | **VERIFIED** | Inspected |
| 9 | **Pre-Exam Readiness & Instructions** | `/exams/<id>/instructions/` | `exams.views.exam_instructions` | `templates/exams/exam_preview.html` | `@student_required` | **VERIFIED** | Inspected |
| 10 | **Live Examination Workspace** | `/exams/attempt/<id>/` | `exams.views.exam_room` | `templates/exams/exam_room.html` | `@student_required` | **VERIFIED** | Inspected |
| 11 | **Answer Autosave Engine** | `/exams/attempt/<id>/save-answer/` | `exams.views.save_answer_ajax` | JSON API | `@student_required` | **VERIFIED** | Inspected |
| 12 | **Proctoring Telemetry Ingestion** | `/exams/proctoring-event/` | `exams.views.log_proctoring_event` | JSON API | `@student_required` | **VERIFIED** | Inspected |
| 13 | **Submission Confirmation** | `/exams/attempt/<id>/submitted/` | `exams.views.exam_submitted` | `templates/exams/exam_submitted.html` | `@student_required` | **VERIFIED** | Inspected |
| 14 | **Published Results Catalog** | `/results/student/` | `results.views.student_results` | `templates/results/student_results.html` | `@student_required` | **VERIFIED** | Inspected |
| 15 | **Individual Scorecard Dossier** | `/results/student/<id>/` | `results.views.student_result_detail` | `templates/results/student_result_detail.html` | `@student_required` | **VERIFIED** | Inspected |

*Key Verification Findings:*
- Students in `pending`, `rejected`, or `suspended` states are blocked at the decorator level from starting exam attempts.
- Examination room maintains sticky timer, question navigation palette, offline answer caching, and automated submission when time expires.
- Results are only accessible to the candidate who took the test, and only after the instructor formally publishes evaluation.

---

### 2.3 Teacher Examination Portal (12 Screens)

| # | Screen Name | URL Route | View Function | Template File | RBAC Gate | Functional Status | Visual Status |
|---|---|---|---|---|---|---|---|
| 16 | **Teacher Dashboard** | `/accounts/teacher/dashboard/` | `accounts.views.teacher_dashboard` | `templates/accounts/teacher_dashboard.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 17 | **Student Approval Queue** | `/accounts/teacher/student-approvals/` | `accounts.views.teacher_student_approvals` | `templates/accounts/student_approvals.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 18 | **Single Student Review** | `/accounts/teacher/review-student/<id>/` | `accounts.views.review_student` | POST Action | `@teacher_required` | **VERIFIED** | Inspected |
| 19 | **Course Subjects Manager** | `/exams/subjects/` | `exams.views.manage_subjects` | `templates/exams/manage_subjects.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 20 | **Teacher Exams Manager** | `/exams/manage/` | `exams.views.manage_exams` | `templates/exams/manage_exams.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 21 | **Examination Authoring Wizard** | `/exams/create/` | `exams.views.create_exam` | `templates/exams/create_exam.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 22 | **Question Bank Repository** | `/exams/questions/` | `exams.views.question_bank` | `templates/exams/question_bank.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 23 | **Question Creator & Editor** | `/exams/questions/create/` | `exams.views.create_question` | `templates/exams/create_question.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 24 | **Live Invigilation Room** | `/exams/<id>/invigilate/` | `exams.views.live_invigilation` | `templates/exams/live_invigilation.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 25 | **Invigilation Telemetry Stream** | `/exams/<id>/telemetry/` | `exams.views.invigilation_telemetry_api` | JSON API | `@teacher_required` | **VERIFIED** | Inspected |
| 26 | **Descriptive Grading Console** | `/results/grade/<attempt_id>/` | `results.views.grade_attempt` | `templates/results/grade_attempt.html` | `@teacher_required` | **VERIFIED** | Inspected |
| 27 | **Exam Results & Publishing** | `/results/teacher/exam/<id>/` | `results.views.teacher_exam_results` | `templates/results/teacher_exam_results.html` | `@teacher_required` | **VERIFIED** | Inspected |

*Key Verification Findings:*
- Teachers can review student applications from their assigned department with one-click approval or rejection with reason.
- Question bank supports Multiple Choice (single/multi-select), True/False, and Subjective Descriptive types.
- Live invigilation radar dynamically highlights candidates with active proctoring violations.

---

### 2.4 Comprehensive Administrator Portal (16 Screens)

| # | Screen Name | URL Route | View Function | Template File | RBAC Gate | Functional Status | Visual Status |
|---|---|---|---|---|---|---|---|
| 28 | **Executive Admin Dashboard** | `/accounts/admin/dashboard/` | `accounts.views.admin_dashboard` | `templates/accounts/admin_dashboard.html` | `@admin_required` | **VERIFIED** | Inspected |
| 29 | **Platform Analytics & Intelligence** | `/accounts/admin/analytics/` | `accounts.views.admin_analytics` | `templates/accounts/admin_analytics.html` | `@admin_required` | **VERIFIED** | Inspected |
| 30 | **System Security Audit Trail** | `/accounts/admin/audit-logs/` | `accounts.views.admin_audit_logs` | `templates/accounts/admin_audit_logs.html` | `@admin_required` | **VERIFIED** | Inspected |
| 31 | **Student Directory & Oversight** | `/accounts/admin/students/` | `accounts.views.admin_students` | `templates/accounts/admin_students.html` | `@admin_required` | **VERIFIED** | Inspected |
| 32 | **Student Profile Dossier** | `/accounts/admin/student/<id>/` | `accounts.views.admin_student_detail` | `templates/accounts/admin_student_detail.html` | `@admin_required` | **VERIFIED** | Inspected |
| 33 | **Faculty Directory & Oversight** | `/accounts/admin/teachers/` | `accounts.views.admin_teachers` | `templates/accounts/admin_teachers.html` | `@admin_required` | **VERIFIED** | Inspected |
| 34 | **Faculty Profile Dossier** | `/accounts/admin/teacher/<id>/` | `accounts.views.admin_teacher_detail` | `templates/accounts/admin_teacher_detail.html` | `@admin_required` | **VERIFIED** | Inspected |
| 35 | **Admin Candidate Approvals** | `/accounts/admin/student-approvals/` | `accounts.views.admin_student_approvals` | `templates/accounts/admin_student_approvals.html` | `@admin_required` | **VERIFIED** | Inspected |
| 36 | **Admin Faculty Approvals** | `/accounts/admin/teacher-approvals/` | `accounts.views.admin_teacher_approvals` | `templates/accounts/admin_teacher_approvals.html` | `@admin_required` | **VERIFIED** | Inspected |
| 37 | **Suspended Accounts Console** | `/accounts/admin/suspended/` | `accounts.views.admin_suspended_accounts` | `templates/accounts/admin_suspended.html` | `@admin_required` | **VERIFIED** | Inspected |
| 38 | **Approval Decision History Ledger**| `/accounts/admin/approval-history/` | `accounts.views.admin_approval_history` | `templates/accounts/admin_approval_history.html` | `@admin_required` | **VERIFIED** | Inspected |
| 39 | **Academic Departments Manager** | `/accounts/admin/departments/` | `accounts.views.admin_departments` | `templates/accounts/admin_departments.html` | `@admin_required` | **VERIFIED** | Inspected |
| 40 | **Edit Department** | `/accounts/admin/departments/<id>/edit/` | `accounts.views.admin_edit_department` | `templates/accounts/admin_edit_department.html` | `@admin_required` | **VERIFIED** | Inspected |
| 41 | **Academic Class Cohorts Manager**| `/accounts/admin/classes/` | `accounts.views.admin_classes` | `templates/accounts/admin_classes.html` | `@admin_required` | **VERIFIED** | Inspected |
| 42 | **Edit Class Cohort** | `/accounts/admin/classes/<id>/edit/` | `accounts.views.admin_edit_class` | `templates/accounts/admin_edit_class.html` | `@admin_required` | **VERIFIED** | Inspected |
| 43 | **Examination Governance Policies** | `/accounts/admin/policies/` | `accounts.views.admin_policies` | `templates/accounts/admin_policies.html` | `@admin_required` | **VERIFIED** | Inspected |
| 44 | **Database Backup Ledger** | `/accounts/admin/backup/` | `accounts.views.admin_backup` | `templates/accounts/admin_backup.html` | `@admin_required` | **VERIFIED** | Inspected |
| 45 | **Security Governance Posture** | `/accounts/admin/security/` | `accounts.views.admin_security` | `templates/accounts/admin_security.html` | `@admin_required` | **VERIFIED** | Inspected |
| 46 | **Master Examinations Catalog** | `/exams/admin/all/` | `exams.views.admin_all_exams` | `templates/exams/admin_all_exams.html` | `@admin_required` | **VERIFIED** | Inspected |
| 47 | **Master Test Attempts Ledger** | `/exams/admin/attempts/` | `exams.views.admin_exam_attempts` | `templates/exams/admin_attempts.html` | `@admin_required` | **VERIFIED** | Inspected |
| 48 | **Proctoring Fleet Monitor** | `/exams/admin/proctoring/` | `exams.views.admin_proctoring_overview` | `templates/exams/admin_proctoring.html` | `@admin_required` | **VERIFIED** | Inspected |
| 49 | **Proctoring Incidents Ledger** | `/exams/admin/incidents/` | `exams.views.admin_proctoring_incidents` | `templates/exams/admin_incidents.html` | `@admin_required` | **VERIFIED** | Inspected |
| 50 | **Results & Grading Oversight** | `/results/admin/overview/` | `results.views.admin_results_overview` | `templates/results/admin_overview.html` | `@admin_required` | **VERIFIED** | Inspected |
| 51 | **Institutional CSV Export Center** | `/results/admin/export/` | `results.views.admin_results_export` | `templates/results/admin_export.html` | `@admin_required` | **VERIFIED** | Inspected |

---

## 3. Automated Test Verification Summary

Command executed:
```bash
python manage.py test
```
Result:
- **Total Tests:** 38
- **Passed:** 38
- **Failed:** 0
- **Errors:** 0
- **Execution Time:** 57.509 seconds
- **Exit Code:** 0

### Breakdown of Test Suites
1. **`accounts.tests.AccountsAuthenticationAndApprovalTests` (15 Tests):**
   - Student and faculty registration workflows with initial 'pending' state
   - Teacher departmental approval of students
   - Teacher rejection of students with institutional memo
   - In-app notification creation upon registration and approval decisions
   - Zero-email compliance assertion (no mail sent during registration)
   - Login credential validation and role-based dashboard redirection
   - Password change and session security
   - Bulk student import via Excel (valid rows, duplicates, and atomic rollback)
2. **`accounts.tests.CentralRegisterAndAdminPortalTests` (10 Tests):**
   - GET `/accounts/register/` renders central role selection cards ("Which type of account do you need?")
   - POST `/accounts/register/` with `role='student'` creates StudentProfile in pending status
   - POST `/accounts/register/` with `role='teacher'` creates TeacherProfile in pending status
   - Administrator access control: non-admins blocked from all 20 admin URLs; superuser receives HTTP 200 on all admin endpoints
   - Student directory search, department filter, and status filter
   - Bulk student account suspension and reactivation
   - Admin direct approval and rejection of student applicants with AuditLog
   - Admin direct approval and rejection of faculty applicants with AuditLog
   - CSV export generation for students, teachers, results, incidents, and audit logs
   - Teacher departmental approval queue view
3. **`exams.tests.ExaminationManagementTests` (8 Tests):**
   - Draft exam creation, subject mapping, question bank insertion
   - Exam publishing and student eligibility checks
   - Student attempt initiation, autosave API, and timer decrement
   - Proctoring event ingestion (tab switch, fullscreen exit, multiple faces)
4. **`results.tests.ResultsAndGradingTests` (5 Tests):**
   - Automated objective grading (MCQ, True/False)
   - Teacher manual grading of subjective answers
   - Result publication restrictions and student scorecard access

---

## 4. Visual Layout & Responsive Verification Disclosure

> [!IMPORTANT]
> **Explicit Verification Disclosure:**
> Per the user's explicit instruction to halt all screenshot capture scripts and headless browser automation, **automated browser screenshot capture is NOT TESTED.**
> All responsive structures have been verified through **direct code review of CSS media queries and HTML layouts**, ensuring:
> 1. Fluid container max-width constraints (`max-width: 1440px`)
> 2. Mobile drawer navigation transforms (`left: -100%` to `left: 0`)
> 3. Bento grid column reflows (`1fr` at `<= 768px`)
> 4. Table horizontal scroll containment (`.bento-table-wrapper` with `-webkit-overflow-scrolling: touch`)
> 5. Typography and control scaling at small mobile viewports (`<= 480px` and `<= 360px`).
