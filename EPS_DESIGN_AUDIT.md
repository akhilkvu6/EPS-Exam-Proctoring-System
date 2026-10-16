# EPS Frontend Design Audit & Migration Analysis

**Project:** Exam Proctoring System (EPS)  
**Date:** 2026-10-15  
**Audit Scope:** Complete frontend layer, templates, static stylesheets, scripts, layout structures, and visual components.

---

## 1. Discovered Templates and Stylesheets

### 1.1 Stylesheets & Static Scripts
- `static/css/styles.css` (494 lines): Legacy CSS defining generic navy blue (`#1e3a8a`), royal blue (`#2563eb`), and emerald green (`#059669`). Uses standard Bootstrap-like symmetrical card grids without asymmetric Bento layout.
- `static/js/main.js`: Basic alert dismissers and mobile hamburger stub.
- `static/js/exam_engine.js`: Client-side autosave, question palette navigation, and timer countdown synchronization.
- `static/js/proctoring.js`: WebRTC video stream preview, Web Audio API decibel spike listener, Fullscreen API, Page Visibility API tab-switch detector, and event telemetry dispatcher.

### 1.2 Discovered Template Inventory (32 Files)
```
templates/
├── base.html                                  [Application Shell & Global Navigation]
├── home.html                                  [Institutional Landing Page]
├── accounts/
│   ├── account_status.html                    [Account Approval/Hold Status]
│   ├── admin_dashboard.html                   [Institutional Administrator Portal]
│   ├── change_password.html                   [In-App Security & Password Management]
│   ├── import_students.html                   [Excel Bulk Enrollment Wizard]
│   ├── login.html                             [Unified Common Login]
│   ├── notifications.html                     [In-App Notification Center]
│   ├── student_dashboard.html                 [Student Portal Home]
│   ├── student_login.html                     [Legacy Redirect / Alias]
│   ├── student_register.html                  [Student Registration & Enrollment]
│   ├── student_registration_success.html      [Student Registration Confirmation]
│   ├── teacher_dashboard.html                 [Faculty Portal & Approval Queue]
│   ├── teacher_login.html                     [Legacy Redirect / Alias]
│   ├── teacher_register.html                  [Teacher Registration & Verification]
│   └── teacher_registration_success.html      [Teacher Registration Confirmation]
├── exams/
│   ├── create_exam.html                       [Exam Authoring & Proctoring Policy]
│   ├── create_question.html                   [Question Bank Authoring]
│   ├── edit_exam.html                         [Exam Modification]
│   ├── exam_detail.html                       [Exam Specs & Instructions]
│   ├── exam_preview.html                      [Paper Layout & Review]
│   ├── exam_room.html                         [Active Exam Workspace & Proctoring]
│   ├── exam_submitted.html                    [Submission Receipt]
│   ├── live_invigilation.html                 [Real-Time Faculty Proctoring Monitor]
│   ├── manage_exams.html                      [Faculty Exam Roster & Assignments]
│   ├── manage_subjects.html                   [Academic Subjects Directory]
│   ├── question_bank.html                     [Central Question Repository]
│   └── student_exam_list.html                 [Student Exam Schedule & Catalogue]
└── results/
    ├── grade_attempt.html                     [Faculty Essay & Descriptive Evaluation]
    ├── student_results.html                   [Student Exam History & Scores]
    ├── student_result_detail.html             [Student Detailed Scorecard]
    └── teacher_exam_results.html              [Exam Analytics & Gradebook Export]
```

---

## 2. Existing Design Issues & Technical Deficiencies

1. **Incorrect Color Scheme:** The existing stylesheets utilize generic corporate navy-blue (`#1e3a8a`) and royal blue (`#2563eb`), conflicting directly with the mandatory Color Hunt Sage Palette (`#5C7057`, `#89A482`, `#ACC5A6`, `#D1EDD3`).
2. **Monotonous Symmetrical Layouts:** All pages presently render repetitive, equal-width grids (`grid-cols-4`, `grid-cols-2`) that lack visual hierarchy and fail to provide the asymmetric priority expected from an institutional Bento Grid.
3. **Absence of Role-Specific Sidebar Navigation:** Authenticated users only see a crowded single-line top navbar rather than an institutional application shell featuring a collapsible, role-tailored sidebar with clear section grouping.
4. **Hardcoded CSS Values:** Colors, margins, and card elevations were scattered throughout templates and styles rather than centralized in semantic design tokens.
5. **Mobile & Tablet Sub-optimality:** Tables and wide cards on administrative and examination monitoring screens cause horizontal scroll issues on narrow viewports without dedicated responsive Bento stacking.
6. **Examination Workspace Density:** In `exam_room.html`, the question pane and proctoring telemetry tiles compete for vertical viewport height without an asymmetric Bento layout balancing question readability and device status.

---

## 3. Old Theme Dependencies to Safely Replace

| Legacy Class / Token | Purpose | Migration Path to Bento Design System |
| :--- | :--- | :--- |
| `--primary: #1e3a8a` | Main brand color | Replace with `--eps-sage-primary: #5C7057` |
| `--accent: #2563eb` | Secondary link/button | Replace with `--eps-sage-secondary: #89A482` |
| `--primary-light: #eff6ff` | Tinted background | Replace with `--eps-mint: #D1EDD3` & `--eps-surface-muted: #F0F4ED` |
| `.card` | Basic container | Migrate to `.bento-card` with variants (`--wide`, `--tall`, `--feature`, `--full`) |
| `.stat-card` | Numeric counter | Migrate to `.bento-card--compact` with sage accents and icon chips |
| `.navbar` | Single-bar top navigation | Refactor into Authenticated Application Shell (Top Header + Collapsible Sidebar) |
| `.btn-primary` | Main submit action | Restyle with `--eps-sage-primary`, rounded radii, and focus ring |
| `.status-badge` | Verification indicators | Standardize with semantic tokens (`--eps-success`, `--eps-warning`, `--eps-danger`) |

---

## 4. Reusable Component Inventory to Establish

1. `bento-grid`: 4-column responsive grid container with `--eps-grid-gap: 20px`.
2. `bento-card`: Standard card surface (`--eps-surface`, `--eps-radius-card: 20px`, `--eps-border: #DFE6DB`).
3. `bento-card--feature`: 2x2 asymmetric hero card for primary workflows.
4. `bento-card--wide`: 2-column span for analytics, short tables, and split forms.
5. `bento-card--tall`: 2-row span for live feeds, question palettes, and activity timelines.
6. `bento-card--full`: Full-width span for gradebooks, question lists, and exam catalogs.
7. `bento-card--mint` & `bento-card--sage`: Brand-accented background containers.
8. `bento-sidebar`: Collapsible, role-specific navigation sidebar with active indicator chips.
9. `bento-header`: Top utility bar with brand identity, breadcrumbs, live notification badge, and user profile chip.
10. `bento-status-pill`: Consistent status indicators for account statuses, exam states, and proctoring events.

---

## 5. Implementation Roadmap
- **Phase 2:** Author `design-tokens.css` and `bento.css`.
- **Phase 3:** Redesign `templates/base.html` shell with collapsible sidebar and mobile drawer.
- **Phase 4:** Migrate Common/Public entry pages (Home, Login, Registration, Account Status).
- **Phase 5:** Migrate Student Portal (Dashboard, Catalog, Readiness, Exam Room, Results, Scorecard).
- **Phase 6:** Migrate Teacher Portal (Dashboard, Approvals, Excel Import, Exam Manager, Question Bank, Invigilation, Manual Grading, Analytics).
- **Phase 7:** Migrate Administrator Portal (Dashboard, Teacher Reviews, Academic Structure, Policies, Audit Logs, Backup).
- **Phase 8:** Migrate Shared Notifications & Security Settings.
- **Phase 9:** Visual Verification, Screenshot Capture, and QA Reporting.
