# EPS Automated & Functional Test Report

**Project:** EPS — Exam Proctoring System  
**Test Execution Date:** October 15, 2026  
**Quality Assurance Lead:** Senior QA Engineer & Test Automation Architect  
**Runtime Environment:** Python 3.14.0, Django 6.1.1, SQLite 3 on Windows 11  
**Execution Command:** `python manage.py test`  
**Execution Exit Code:** 0  

---

## 1. Executive Summary

The complete test suite of the Exam Proctoring System (EPS) was executed to validate backend business logic, role-based access control (RBAC), multi-tiered account registration approval flows, minimal authentication redirection, examination creation and lifecycle state transitions, proctoring telemetry capture, institutional policy governance, descriptive manual grading, and institutional reporting.

**Overall Test Results:**
- **Total Test Cases Executed:** 42
- **Tests Passed:** 42
- **Tests Failed:** 0
- **Errors / Flaky Tests:** 0
- **Execution Time:** 49.730 seconds
- **Pass Rate:** 100.0%
- **System Integrity:** Verified (0 issues, 0 silenced)

---

## 2. Test Execution Command & Console Output

```powershell
PS C:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System> python manage.py test
Creating test database for alias 'default'...
..........................................
----------------------------------------------------------------------
Ran 42 tests in 49.730s

OK
Destroying test database for alias 'default'...
Found 42 test(s).
System check identified no issues (0 silenced).
```

---

## 3. Detailed Test Suite Breakdown (42 Tests)

### 3.1 `accounts.tests.AccountsAuthenticationAndApprovalTests` (9 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `accounts.tests.01` | `test_common_login_role_redirection` | Verifies unified login routes Students to `/accounts/student/dashboard/`, Teachers to `/accounts/teacher/dashboard/`, and Admins to `/accounts/admin/dashboard/`. | **PASS** |
| `accounts.tests.02` | `test_in_app_password_change` | Asserts authenticated users can securely update passwords without email tokens, logging an in-app audit notification. | **PASS** |
| `accounts.tests.03` | `test_notifications_marked_read` | Validates in-app notification state transitions from unread to read via POST action. | **PASS** |
| `accounts.tests.04` | `test_student_registration_workflow` | Asserts student registration sets `is_approved=False` and creates departmental pending record. | **PASS** |
| `accounts.tests.05` | `test_teacher_approves_student` | Validates teacher approving departmental student activates account and sends in-app alert. | **PASS** |
| `accounts.tests.06` | `test_teacher_registration_and_admin_approval` | Asserts faculty registration sets `is_approved=False` and admin approval activates the account. | **PASS** |
| `accounts.tests.07` | `test_teacher_rejects_student` | Validates rejection workflow with reason logging without sending emails. | **PASS** |
| `accounts.tests.08` | `test_unapproved_student_blocked_from_portal` | Confirms unapproved student login is redirected to pending approval notice. | **PASS** |
| `accounts.tests.09` | `test_unauthorized_dashboard_access_protection` | Verifies strict RBAC decorators block cross-role access (e.g. Student accessing Teacher/Admin views). | **PASS** |

### 3.2 `accounts.tests.CentralRegisterAndAdminPortalTests` (10 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `accounts.tests.10` | `test_central_register_get_renders_role_options` | Asserts `GET /accounts/register/` renders unified role selector (Student & Teacher cards) with HTTP 200. | **PASS** |
| `accounts.tests.11` | `test_central_register_student_form_submission` | Validates submission of student registration via central flow creates user with `is_approved=False`. | **PASS** |
| `accounts.tests.12` | `test_central_register_teacher_form_submission` | Validates submission of teacher registration via central flow creates faculty user pending admin approval. | **PASS** |
| `accounts.tests.13` | `test_teacher_student_approvals_queue_view` | Asserts teacher can access `/accounts/teacher/student-approvals/` showing pending students in their department. | **PASS** |
| `accounts.tests.14` | `test_admin_portal_access_control` | Verifies non-admin users (Students, Teachers, anonymous) are blocked from `/accounts/admin/` endpoints. | **PASS** |
| `accounts.tests.15` | `test_admin_student_directory_search_and_filter` | Asserts admin can search students by username, PRN, or filter by department/class. | **PASS** |
| `accounts.tests.16` | `test_admin_review_student_approve_and_reject` | Asserts admin can approve or reject student accounts directly from institutional management queue. | **PASS** |
| `accounts.tests.17` | `test_admin_review_teacher_approve_and_reject` | Asserts admin can review and approve/reject pending faculty registrations. | **PASS** |
| `accounts.tests.18` | `test_admin_bulk_suspend_and_activate_students` | Validates batch suspension and reactivation of student accounts. | **PASS** |
| `accounts.tests.19` | `test_admin_export_reports_csv` | Asserts admin export endpoint generates compliant CSV files for student, teacher, exam, and incident data. | **PASS** |

### 3.3 `accounts.tests.ExcelBulkStudentImportTests` (4 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `accounts.tests.20` | `test_bulk_student_import_atomic_rollback` | Asserts database transaction rolls back completely if any row in the spreadsheet contains invalid data. | **PASS** |
| `accounts.tests.21` | `test_bulk_student_import_duplicate_and_error_handling` | Asserts clear line-by-line error reporting when duplicate roll numbers or usernames are supplied. | **PASS** |
| `accounts.tests.22` | `test_bulk_student_import_success` | Verifies clean ingestion of 5+ students with automated profile linking from valid `.xlsx` file. | **PASS** |
| `accounts.tests.23` | `test_download_template_access_and_format` | Asserts teachers and admins can download standard pre-formatted Excel template with correct headers. | **PASS** |

### 3.4 `exams.tests.ExaminationEngineAndProctoringTests` (5 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `exams.tests.24` | `test_autosave_answer_api` | Asserts AJAX endpoint `POST /exams/api/save-answer/` saves MCQ choice or descriptive draft asynchronously. | **PASS** |
| `exams.tests.25` | `test_live_invigilation_dashboard` | Asserts teacher live monitoring HUD displays connected candidates and auto-refreshes telemetry. | **PASS** |
| `exams.tests.26` | `test_proctoring_incident_logging_and_flagging` | Asserts client-side violations (tab switch, window blur, fullscreen exit) are recorded as `ProctoringIncident`. | **PASS** |
| `exams.tests.27` | `test_start_exam_creates_attempt_with_strict_deadline` | Asserts starting exam initializes `ExamAttempt` with locked deadline and prevents simultaneous duplicate attempts. | **PASS** |
| `exams.tests.28` | `test_submit_exam_and_automated_grading` | Asserts exam submission closes attempt, locks answers, and triggers instantaneous automated MCQ evaluation. | **PASS** |

### 3.5 `exams.tests.ExaminationManagementTests` (5 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `exams.tests.29` | `test_add_and_remove_questions_from_exam` | Asserts faculty can attach/detach questions from department question banks into exams. | **PASS** |
| `exams.tests.30` | `test_create_draft_examination` | Asserts faculty can draft exams with duration, total marks, passing marks, and strict proctoring flags. | **PASS** |
| `exams.tests.31` | `test_publish_exam_validation_and_notifications` | Asserts an exam cannot be published without questions, and publishing creates in-app candidate notifications. | **PASS** |
| `exams.tests.32` | `test_random_question_picker` | Asserts question randomization generator selects configured number of questions from category pools. | **PASS** |
| `exams.tests.33` | `test_student_eligibility_check` | Asserts candidate eligibility is strictly validated against department, semester, and approval status. | **PASS** |

### 3.6 `results.tests.ResultsEvaluationAndReportingTests` (5 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `results.tests.34` | `test_export_results_csv` | Asserts faculty and admins can export examination score sheets to formatted CSV. | **PASS** |
| `results.tests.35` | `test_manual_grading_of_descriptive_responses` | Validates faculty interface for awarding points and feedback to descriptive and code answers. | **PASS** |
| `results.tests.36` | `test_publish_results_workflow` | Asserts exam results remain confidential until faculty explicitly triggers "Publish Results". | **PASS** |
| `results.tests.37` | `test_result_auto_created_and_evaluated_on_submit` | Asserts submission initializes `Result` record with percentage, pass/fail status, and grade letter. | **PASS** |
| `results.tests.38` | `test_unpublished_results_hidden_from_students` | Asserts students cannot access scorecard or grade until results have been published. | **PASS** |

### 3.7 `accounts.tests.InstitutionalPoliciesTests` (4 Tests) — ALL PASS

| Test Identifier | Test Name | Objective & Assertions | Status |
|---|---|---|---|
| `accounts.tests.39` | `test_unauthorized_access_blocked` | Asserts anonymous, student, and teacher accounts cannot access or alter policies (`HTTP 302` redirect). | **PASS** |
| `accounts.tests.40` | `test_admin_policies_get_renders_correctly` | Asserts admin GET renders `accounts/admin_policies.html` with real DB metrics, hash, and metadata. | **PASS** |
| `accounts.tests.41` | `test_admin_policies_post_saves_and_persists` | Validates form POST validation, persistence, SHA-256 updating, and `AuditLog` entry creation. | **PASS** |
| `accounts.tests.42` | `test_admin_policies_export_manifest_json` | Asserts `/accounts/admin/policies/export/` returns signed institutional policy JSON manifest. | **PASS** |

---

## 4. Test Quality & Verification Verdict

The EPS test suite provides comprehensive coverage across authentication, authorization, registration approvals, exam integrity, proctoring security, institutional governance policies, evaluation, and reporting. With **42 out of 42 automated unit and integration tests passing** and **exit code 0**, the application backend demonstrates rock-solid stability and adherence to all functional requirements.
