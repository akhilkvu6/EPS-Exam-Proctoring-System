# EPS Page Redesign Checklist & Implementation Matrix

**Project:** EPS — Exam Proctoring System  
**Audit & Implementation Date:** October 15, 2026  
**Design Standard:** Centralized Bento Grid System (`static/css/bento.css`, `static/css/design-tokens.css`)  
**Palette:** Color Hunt Sage Identity (`#5C7057`, `#89A482`, `#ACC5A6`, `#D1EDD3`)  
**Visual Testing Disclosure:** **NOT TESTED via automated browser tools (omitted per user direct instruction). Responsive architecture verified via comprehensive HTML and CSS inspection.**

---

## 1. Public & Central Registration Pages

| Page Name | Template Path | Bento Grid Layout Pattern | Sage Palette Tokens Applied | Responsive Architecture | Functional Status | Visual Status |
|---|---|---|---|---|---|---|
| **Minimal Institutional Homepage** | `templates/home.html` | Restrained Hero Bento Grid + 5 Core Function Cards | Primary Sage hero action, Mint background highlights | Max-width 1280px, stacks at <= 768px | **VERIFIED** | Code Inspected |
| **Common Login Portal** | `templates/accounts/login.html` | 2-Column Split Bento Card (50/50 Trust Panel & Form) | Primary Sage gradient trust panel, Mint inputs | Single-column form stack on mobile | **VERIFIED** | Code Inspected |
| **Central Role Selection & Registration** | `templates/accounts/register.html` | Role Selector Radio Bento Card + Dynamic Form Container | Primary Sage border on selection, Mint badge | Full-width stacking, touch targets >= 44px | **VERIFIED** | Code Inspected |
| **In-App Registration Confirmation** | `templates/accounts/registration_success.html` | Centered Bento Card with Trust Receipt | Primary Sage icon, Mint policy alert banner | Centered on all viewports, zero-email note | **VERIFIED** | Code Inspected |
| **Account Status Inquiry** | `templates/accounts/account_status.html` | Centered Bento Card with dynamic status badges | Amber pending, Red suspended, Green approved | Centered responsive card | **VERIFIED** | Code Inspected |
| **Password Change Console** | `templates/accounts/change_password.html` | Bento Form Card with password toggles | Primary Sage submit button, Mint guidance card | Form stack on mobile | **VERIFIED** | Code Inspected |

---

## 2. Student Portal Pages

| Page Name | Template Path | Bento Grid Layout Pattern | Sage Palette Tokens Applied | Responsive Architecture | Functional Status | Visual Status |
|---|---|---|---|---|---|---|
| **Student Dashboard** | `templates/accounts/student_dashboard.html` | 4-Column Asymmetric Bento Grid | Primary Sage Exam card, Mint metric cards | 1-column stack on mobile, off-canvas drawer | **VERIFIED** | Code Inspected |
| **Assigned Examinations Catalog** | `templates/exams/student_exam_list.html` | Grouped Bento Cards (Live, Upcoming, Concluded) | Pulsing Green live badge, Sage upcoming chips | Reflows cards naturally on mobile | **VERIFIED** | Code Inspected |
| **Pre-Exam Instructions & Readiness** | `templates/exams/exam_preview.html` | Centered Candidate Simulation Card | Mint Instructions card, Itemized Questions | Fluid width, scrollable checklist | **VERIFIED** | Code Inspected |
| **Live Examination Room** | `templates/exams/exam_room.html` | High-Focus Examination Workspace | Sticky timer chip, Primary Sage delivery card | Fluid layout, safe full viewport | **VERIFIED** | Code Inspected |
| **Submission Confirmation Receipt** | `templates/exams/exam_submitted.html` | Centered Bento Receipt Card | Mint confirmation card with timestamp | Mobile centered responsive | **VERIFIED** | Code Inspected |
| **Student Results Ledger** | `templates/results/student_results.html` | Bento Table Card with Performance Badges | Green PASS / Red FAIL pills, Mint links | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Scorecard Detail** | `templates/results/student_result_detail.html` | Bento Scoreboard + Itemized Question Cards | Mint score panel, bold Sage percentage | Mobile stacked cards | **VERIFIED** | Code Inspected |

---

## 3. Teacher Portal Pages

| Page Name | Template Path | Bento Grid Layout Pattern | Sage Palette Tokens Applied | Responsive Architecture | Functional Status | Visual Status |
|---|---|---|---|---|---|---|
| **Teacher Dashboard** | `templates/accounts/teacher_dashboard.html` | 4-Column Asymmetric Bento Grid | Mint 2x2 Student Approval Queue card | 1-column stack on mobile, off-canvas drawer | **VERIFIED** | Code Inspected |
| **Student Approvals Queue** | `templates/accounts/student_approvals.html` | Filter Card + Bento Table + Rejection Modal | Warning pending badge, Sage department chip | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Excel Student Import** | `templates/accounts/import_students.html` | Staged Bento Wizard (Upload + Guidance) | Mint template download card, Sage buttons | Mobile stacked cards | **VERIFIED** | Code Inspected |
| **Teacher Exams Manager** | `templates/exams/manage_exams.html` | Metric Row + Exam Ledger Table Card | Sage action pills, Status pills | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Create Examination** | `templates/exams/create_exam.html` | Grouped Bento Section Cards | Mint proctoring card, Sage schedule controls | Mobile single column | **VERIFIED** | Code Inspected |
| **Edit Examination** | `templates/exams/edit_exam.html` | Grouped Bento Section Cards | Sage section headers, Mint cohort selector | Mobile single column | **VERIFIED** | Code Inspected |
| **Exam Detail & Questions** | `templates/exams/exam_detail.html` | 3-Column Asymmetric Bento Grid | Mint Question Generator, Sage Bank picker | Mobile stacked layout | **VERIFIED** | Code Inspected |
| **Question Bank Repository** | `templates/exams/question_bank.html` | Filter Card + Question Table Card | Mint filter card, Sage buttons | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Question Authoring Wizard** | `templates/exams/create_question.html` | Dynamic Bento Form Card | Mint dynamic MCQ card, Sage answer key | Mobile single column | **VERIFIED** | Code Inspected |
| **Academic Subjects Manager** | `templates/exams/manage_subjects.html` | 3-Column Bento Grid (Form + Table) | Mint subject creation card, Sage code badges | Mobile stacked layout | **VERIFIED** | Code Inspected |
| **Live Invigilation Monitor** | `templates/exams/live_invigilation.html` | 4-Column Stat Cards + Active Table | Pulsing Live Telemetry badge, Red alarms | Responsive table + stats wrap | **VERIFIED** | Code Inspected |
| **Descriptive Grading Console** | `templates/results/grade_attempt.html` | Itemized Question Evaluation Cards | Mint Answer Key guide card, Sticky bar | Mobile full width | **VERIFIED** | Code Inspected |
| **Teacher Exam Results** | `templates/results/teacher_exam_results.html` | 4-Column Metric Cards + Submissions Ledger | Average score, Pass rate, CSV export button | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |

---

## 4. Institutional Administrator Portal Pages

| Page Name | Template Path | Bento Grid Layout Pattern | Sage Palette Tokens Applied | Responsive Architecture | Functional Status | Visual Status |
|---|---|---|---|---|---|---|
| **Executive Admin Dashboard** | `templates/accounts/admin_dashboard.html` | Asymmetric Bento Overview + Priority Queues | Sage metrics, Mint queue cards, Red alert badges | Mobile stacked layout, drawer navigation | **VERIFIED** | Code Inspected |
| **Candidate Directory** | `templates/accounts/admin_students.html` | Filter Bar + Bulk Operations + Roster Table | Sage roll chips, Mint cohort badges | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Candidate Dossier** | `templates/accounts/admin_student_detail.html` | 3-Column Dossier + Attempts & Results Tables | Mint verification banner, Sage metrics card | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Faculty Directory** | `templates/accounts/admin_teachers.html` | Filter Bar + Faculty Roster Table | Sage Employee ID chips, Status badges | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Faculty Dossier** | `templates/accounts/admin_teacher_detail.html` | 3-Column Dossier + Created Exams Table | Mint review alert, Sage authoring stats | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Candidate Approvals Queue** | `templates/accounts/admin_student_approvals.html` | Filter Bar + Queue Table + Rejection Modal | Amber pending badges, Green approve action | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Faculty Approvals Queue** | `templates/accounts/admin_teacher_approvals.html` | Filter Bar + Queue Table + Rejection Modal | Amber pending badges, Green approve action | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Suspended Accounts Console** | `templates/accounts/admin_suspended.html` | Split Bento Table Cards (Students & Teachers) | Red suspended badges, Green reactivate button | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Approval History Ledger** | `templates/accounts/admin_approval_history.html` | Filter Bar + Chronological Decision Ledger | Sage faculty pills, Mint student pills | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Departments Manager** | `templates/accounts/admin_departments.html` | 3-Column Bento Grid (1-Col Form + 2-Col Table) | Mint creation form, Sage department codes | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Edit Department** | `templates/accounts/admin_edit_department.html` | Centered Bento Card Form | Primary Sage submit button, Light sage inputs | Centered on all viewports | **VERIFIED** | Code Inspected |
| **Classes Manager** | `templates/accounts/admin_classes.html` | 3-Column Bento Grid (1-Col Form + 2-Col Table) | Mint creation form, Mint enrolled count badge | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Edit Class Cohort** | `templates/accounts/admin_edit_class.html` | Centered Bento Card Form | Primary Sage submit button, Light sage inputs | Centered on all viewports | **VERIFIED** | Code Inspected |
| **Platform Analytics** | `templates/accounts/admin_analytics.html` | 4-Column Metric Row + Split Charts + Severity | Sage metrics, Mint status progress bars | Stacks cleanly on mobile | **VERIFIED** | Code Inspected |
| **Security Audit Trail** | `templates/accounts/admin_audit_logs.html` | Filter Bar + Immutable Security Ledger | Sage action badges, Monospace timestamps | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Examination Policies** | `templates/accounts/admin_policies.html` | 2x2 Bento Grid Policy Cards | Mint Zero-Email card, Sage honor code card | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Database Backup Ledger** | `templates/accounts/admin_backup.html` | 3-Column Metric Row + Snapshot Ledger Table | Sage storage card, Mint recovery guide | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Security Governance** | `templates/accounts/admin_security.html` | 2-Column Bento Grid (Checklist + Architecture) | Sage security card, Green verified badges | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |
| **Master Exams Catalog** | `templates/exams/admin_all_exams.html` | Filter Bar + Master Exams Table | Sage subject codes, Status pills | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Master Attempts Ledger** | `templates/exams/admin_attempts.html` | Filter Bar + Test Sessions Table | Red flagged alerts, Green normal pills | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Proctoring Fleet Monitor** | `templates/exams/admin_proctoring.html` | 4-Column Stat Cards + Active Fleet Table | Pulsing Live Telemetry badge, Red alarms | Responsive table + stats wrap | **VERIFIED** | Code Inspected |
| **Proctoring Incidents Ledger** | `templates/exams/admin_incidents.html` | Filter Bar + Forensic Evidence Ledger | Red High, Amber Medium, Gray Low badges | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Results Overview** | `templates/results/admin_overview.html` | 4-Column Stat Cards + Exam Summary Table | Green pass rate, Red fail count | `.bento-table-wrapper` touch scroll | **VERIFIED** | Code Inspected |
| **Reports & CSV Export Center**| `templates/results/admin_export.html` | 2x2 Bento Grid Download Cards + Audit Banner | Mint results card, Sage student card | Stacks to 1 column on mobile | **VERIFIED** | Code Inspected |

---

## 5. Cross-Cutting Application Shell

| Component | Template Path | Implementation | Sage Palette Tokens | Responsive Behavior | Status |
|---|---|---|---|---|---|
| **Dual-Mode Shell** | `templates/base.html` | Public header for guests, Grouped drawer for auth | Brand icon `🌿 EPS`, Active item Sage pill | Collapsible desktop sidebar; Off-canvas mobile drawer | **VERIFIED** |
| **In-App Notifications** | `templates/accounts/notifications.html`| Bento Alert Container with Category Filters | Mint unread backgrounds, Sage type pills | Stacks cleanly on mobile | **VERIFIED** |
| **Global Alert Toasts** | `templates/base.html` | Bento alert toasts for Django messages | Green success, Red danger, Amber warning | Fixed-width safe margin banner | **VERIFIED** |
