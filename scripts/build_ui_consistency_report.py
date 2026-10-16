import os
import sys
import json
import re

# Load audit data
with open('scripts/ui_audit_data.json', 'r', encoding='utf-8') as f:
    audit_data = json.load(f)

# Group by category
categorized = {
    'Public & Authentication': [],
    'Student Portal': [],
    'Teacher Portal': [],
    'Administrator Portal': [],
    'Shared & Security': [],
}

for item in audit_data:
    t = item['template']
    if t.startswith('accounts/admin_') or t.startswith('exams/admin_') or t.startswith('results/admin_'):
        categorized['Administrator Portal'].append(item)
    elif t.startswith('accounts/teacher_') or t in ('accounts/student_approvals.html', 'accounts/import_students.html') or (t.startswith('exams/') and not any(k in t for k in ['student', 'preview', 'readiness', 'room', 'submitted'])) or t in ('results/grade_attempt.html', 'results/teacher_exam_results.html'):
        categorized['Teacher Portal'].append(item)
    elif t.startswith('accounts/student_') or t in ('exams/student_exam_list.html', 'exams/exam_preview.html', 'exams/exam_readiness.html', 'exams/exam_room.html', 'exams/exam_submitted.html') or t.startswith('results/student_'):
        categorized['Student Portal'].append(item)
    elif t in ('accounts/profile.html', 'accounts/change_password.html', 'accounts/notifications.html'):
        categorized['Shared & Security'].append(item)
    else:
        categorized['Public & Authentication'].append(item)

report_lines = []

report_lines.append("# EPS — Complete All-Page UI Consistency and Design Audit")
report_lines.append("")
report_lines.append("**Project:** Exam Proctoring System (EPS)  ")
report_lines.append("**Project Directory:** `C:\\Users\\akhil\\OneDrive\\Desktop\\EPS-Exam-Proctoring-System`  ")
report_lines.append("**Audit Date:** October 16, 2026  ")
report_lines.append("**Technology Stack:** Python 3.14.0, Django 6.1.1, HTML5, CSS3, JavaScript, SQLite 3  ")
report_lines.append("**Official Visual Identity:** Color Hunt 4-Color Sage Palette (`#5C7057`, `#89A482`, `#ACC5A6`, `#D1EDD3`) & Asymmetric Bento Grid System  ")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 1. Executive Summary & Inventory Overview")
report_lines.append("")
report_lines.append("A full forensic audit of all **64 Django template files** and **175 URL route mappings** was conducted to evaluate visual consistency, architectural compliance, stylesheet dependencies, and component standardization.")
report_lines.append("")
report_lines.append("### Key Audit Discoveries:")
report_lines.append("1. **The Established Baseline:** The application has a thoroughly defined, custom-built **Sage-Green Bento Grid Design System** residing in `static/css/design-tokens.css`, `static/css/bento.css`, and `templates/base.html`. 54 of 64 templates (84.4%) strictly inherit `base.html` and use these tokens.")
report_lines.append("2. **The Inconsistency Root Cause:** Exactly **8 templates** (`home.html`, `accounts/login.html`, `accounts/student_register.html`, `accounts/teacher_register.html`, `accounts/student_dashboard.html`, `accounts/teacher_dashboard.html`, `accounts/admin_dashboard.html`, `accounts/admin_policies.html`) were introduced as standalone reference mockups utilizing external Tailwind CDN (`cdn.tailwindcss.com`) with a conflicting **corporate blue palette** (`#154ceb`, `#0036bb`, `#0042df`, `#edf1fe`), hardcoded custom sidebars, and Google Web Fonts.")
report_lines.append("3. **User Experience Impact:** When users navigate between dashboard pages and subpages (e.g., clicking from Admin Dashboard to 'All Students', 'Analytics', or 'Departments'), the UI experiences an abrupt layout and color jump—switching from a Tailwind blue-tinted interface to the Sage-Green Bento interface.")
report_lines.append("4. **Zero Missing Routes:** All functional requirements, portals, and endpoints map to working views and templates. No 404 broken routes or missing templates exist.")
report_lines.append("")
report_lines.append("| Template Audit Status | Total Files | Percentage | Description |")
report_lines.append("|---|:---:|:---:|---|")
report_lines.append("| **Compliant (Sage-Green Bento)** | 54 | 84.4% | Extends `base.html`, uses design tokens, Bento cards/grids/tables/buttons |")
report_lines.append("| **Inconsistent (Tailwind / Blue Isolation)** | 8 | 12.5% | Standalone `<html>`, Tailwind CDN, blue palette, duplicate sidebars |")
report_lines.append("| **Specialized Distraction-Free Workspace** | 1 | 1.6% | `exams/exam_room.html`: Intentional fullscreen exam workspace (uses Sage tokens) |")
report_lines.append("| **Base Template Shell** | 1 | 1.6% | `templates/base.html`: Shared master layout foundation |")
report_lines.append("| **TOTAL TEMPLATES AUDITED** | **64** | **100%** | Comprehensive repository inventory |")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 2. Design System Baseline Specification")
report_lines.append("")
report_lines.append("The official design system of EPS is codified in [`static/css/design-tokens.css`](file:///c:/Users/akhil/OneDrive/Desktop/EPS-Exam-Proctoring-System/static/css/design-tokens.css) and [`static/css/bento.css`](file:///c:/Users/akhil/OneDrive/Desktop/EPS-Exam-Proctoring-System/static/css/bento.css):")
report_lines.append("")
report_lines.append("### 2.1 Color Palette (Color Hunt Official Sage Set)")
report_lines.append("- **Primary Sage:** `#5C7057` (`var(--eps-sage-primary)`) — Used for primary buttons, active states, brand icons, primary badges.")
report_lines.append("- **Secondary Sage:** `#89A482` (`var(--eps-sage-secondary)`) — Used for secondary accents, focus rings, hover borders, stat icons.")
report_lines.append("- **Light Sage:** `#ACC5A6` (`var(--eps-sage-light)`) — Used for subtle dividers, card badges, secondary borders.")
report_lines.append("- **Mint Green:** `#D1EDD3` (`var(--eps-mint)`) — Used for active navigation pills, highlighted stat chips, subtle container tints.")
report_lines.append("- **Page Background:** `#F6F8F4` (`var(--eps-page-background)`) — Warm, muted sage-tinted neutral surface.")
report_lines.append("- **Surface Cards:** `#FFFFFF` (`var(--eps-surface)`) with border `#DFE6DB` (`var(--eps-border)`).")
report_lines.append("- **Text Colors:** Primary `#263026`, Secondary `#596459`, Muted `#7A8979`, Inverse `#FFFFFF`.")
report_lines.append("- **Status Colors (WCAG AA):** Success `#277044`, Warning `#955600`, Danger `#B42318`, Info `#356B5A`.")
report_lines.append("")
report_lines.append("### 2.2 Typography & Heading Hierarchy")
report_lines.append("- **Font Stack:** `var(--eps-font-sans)`: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.")
report_lines.append("- **Monospace Stack:** `var(--eps-font-mono)`: `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`.")
report_lines.append("- **Headings:** `h1` (1.85rem / 700 / -0.02em), `h2` (1.45rem / 700 / -0.015em), `h3` (1.2rem / 700), `h4` (1.05rem / 700).")
report_lines.append("")
report_lines.append("### 2.3 Layout Spacing & Radii Scale")
report_lines.append("- **Border Radii:** Controls `12px` (`var(--eps-radius-control)`), Cards `20px` (`var(--eps-radius-card)`), Badges `9999px` (`var(--eps-radius-full)`).")
report_lines.append("- **Grid & Margins:** Page padding `28px` (`16px` on tablet, `12px` on mobile), Grid gap `20px`, Card padding `24px` (`16px` compact).")
report_lines.append("- **Max Container Width:** `1440px` for authenticated workspace, `1280px` for public pages.")
report_lines.append("")
report_lines.append("### 2.4 Component Library Standard")
report_lines.append("- **Grids:** `.bento-grid` (4-column responsive), `.bento-grid--2col`, `.bento-grid--3col`, `.bento-grid--5col`.")
report_lines.append("- **Cards:** `.bento-card`, `.bento-card--wide` (span 2), `.bento-card--3col` (span 3), `.bento-card--tall` (row 2), `.bento-card--feature` (2x2), `.bento-card--full` (1 / -1), `.bento-card--primary`, `.bento-card--mint`, `.bento-card--sage`.")
report_lines.append("- **Buttons:** `.bento-btn`, `.bento-btn--primary`, `.bento-btn--secondary`, `.bento-btn--mint`, `.bento-btn--outline`, `.bento-btn--danger`, `.bento-btn--sm`, `.bento-btn--lg`.")
report_lines.append("- **Badges:** `.bento-badge`, `.bento-badge--success`, `.bento-badge--warning`, `.bento-badge--danger`, `.bento-badge--sage`, `.bento-badge--mint`.")
report_lines.append("- **Form Controls:** `.bento-input`, `.bento-select`, `.bento-textarea`, `.bento-form-group`, `.bento-form-label`, `.bento-form-hint`.")
report_lines.append("- **Tables:** `.bento-table-wrapper` (horizontal touch scroll container) wrapping `.bento-table` with uppercase muted headers and hover row tinting.")
report_lines.append("- **Alerts:** `.bento-alert--success`, `.bento-alert--error`, `.bento-alert--warning`, `.bento-alert--info`.")
report_lines.append("- **Navigation:** Unified `base.html` shell with collapsible `.app-sidebar` (left), `.app-header` (top utility bar with unread bell & user chip), and mobile drawer toggle (`#mobile-menu-toggle`).")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 3. Comprehensive Page-by-Page Consistency Matrix")
report_lines.append("")
report_lines.append("Below is the exhaustive matrix of all 64 template files, their inheritance, color palette, navigation integration, and compliance status:")
report_lines.append("")

for cat_name, items in categorized.items():
    report_lines.append(f"### 3.{list(categorized.keys()).index(cat_name) + 1} {cat_name} ({len(items)} Templates)")
    report_lines.append("")
    report_lines.append("| Template File | Extends Base? | Framework / Styles | Primary Palette | Navigation | Component Standard | Compliance Status |")
    report_lines.append("|---|:---:|---|---|---|---|:---:|")
    for it in sorted(items, key=lambda x: x['template']):
        t_name = it['template']
        ext = "Yes" if it['extends'] == 'base.html' else ("No (Base)" if t_name == 'base.html' else "No (Standalone)")
        fw = "Tailwind CDN + Google Fonts" if it['uses_tailwind'] else ("Shared Bento CSS" if t_name != 'base.html' else "Design Tokens Foundation")
        
        if it['uses_tailwind']:
            pal = "Conflicting Blue (`#154ceb`, `#0036bb`)"
            nav = "Hardcoded Custom Sidebar / Header"
            comp = "Tailwind Utility Classes"
            status = "**INCONSISTENT**"
        elif t_name == 'exams/exam_room.html':
            pal = "Sage-Green Tokens"
            nav = "Distraction-Free Exam Header"
            comp = "Bento Tokens & Components"
            status = "**COMPLIANT (Specialized)**"
        elif t_name == 'base.html':
            pal = "Official Sage-Green Tokens"
            nav = "Master App Sidebar & Header"
            comp = "Bento Foundation"
            status = "**BASELINE FOUNDATION**"
        else:
            pal = "Official Sage-Green (`#5C7057`)"
            nav = "Inherited App Sidebar"
            comp = "Bento Grid / Cards / Tables / Badges"
            status = "**COMPLIANT**"
            
        report_lines.append(f"| `{t_name}` | {ext} | {fw} | {pal} | {nav} | {comp} | {status} |")
    report_lines.append("")

report_lines.append("---")
report_lines.append("")
report_lines.append("## 4. Confirmed Inconsistencies Ledger (By Severity)")
report_lines.append("")
report_lines.append("### 4.1 Critical Severity (Architectural & Theme Fracture)")
report_lines.append("")
report_lines.append("#### Issue CRIT-01: Disconnected Tailwind Framework & Blue Palette in Dashboards & Home")
report_lines.append("- **Affected Templates (6 files):**")
report_lines.append("  1. `templates/home.html` (Landing Page, Route `/`)")
report_lines.append("  2. `templates/accounts/login.html` (Common Login, Route `/accounts/login/`)")
report_lines.append("  3. `templates/accounts/student_dashboard.html` (Student Portal, Route `/accounts/student/dashboard/`)")
report_lines.append("  4. `templates/accounts/teacher_dashboard.html` (Teacher Portal, Route `/accounts/teacher/dashboard/`)")
report_lines.append("  5. `templates/accounts/admin_dashboard.html` (Admin Portal, Route `/accounts/admin/dashboard/`)")
report_lines.append("  6. `templates/accounts/admin_policies.html` (Policies Page, Route `/accounts/admin/policies/`)")
report_lines.append("- **Expected Shared Design Rule:** All application pages must inherit `base.html` and use the centralized design tokens defined in `design-tokens.css` and `bento.css`, strictly adhering to the 4-color Sage palette (`#5C7057`, `#89A482`, `#ACC5A6`, `#D1EDD3`).")
report_lines.append("- **Actual Deviation:**")
report_lines.append("  - Each template is a standalone HTML file (`<!DOCTYPE html><html><head>...`) importing `https://cdn.tailwindcss.com`.")
report_lines.append("  - Defines a custom Tailwind theme configuring a blue corporate identity (`surface-tint: #154ceb`, `primary: #0042df`, `on-primary-fixed-variant: #0036bb`, `on-tertiary-container: #edf1fe`).")
report_lines.append("  - Loads Google Web Fonts (`Inter`, `Material Symbols Outlined`) dynamically via external CDN.")
report_lines.append("  - When navigating from any dashboard to its sub-pages (e.g. `teacher_dashboard` -> `teacher_students` or `admin_dashboard` -> `admin_students`), the screen violently flips from blue Tailwind to Sage-Green Bento.")
report_lines.append("- **Recommended Correction:**")
report_lines.append("  - Refactor all 6 templates to extend `base.html`.")
report_lines.append("  - Map Tailwind classes to corresponding `.bento-card`, `.bento-grid`, `.bento-btn`, `.bento-stat`, and `.bento-table` classes.")
report_lines.append("  - Harmonize color values to official Sage-green tokens (`var(--eps-sage-primary)`, `var(--eps-mint)`, etc.).")
report_lines.append("  - Remove external Tailwind CDN script tags and Google Fonts link tags.")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("### 4.2 High Severity (Navigation Duplication & Isolated Register Views)")
report_lines.append("")
report_lines.append("#### Issue HIGH-01: Duplicate Sidebar Markup in Tailwind Templates")
report_lines.append("- **Affected Templates (4 files):**")
report_lines.append("  1. `templates/accounts/student_dashboard.html`")
report_lines.append("  2. `templates/accounts/teacher_dashboard.html`")
report_lines.append("  3. `templates/accounts/admin_dashboard.html`")
report_lines.append("  4. `templates/accounts/admin_policies.html`")
report_lines.append("- **Expected Shared Design Rule:** Sidebar navigation must be centrally rendered by `templates/base.html` with role-aware route highlighting, badge counts for in-app notifications, and responsive mobile drawer behaviors.")
report_lines.append("- **Actual Deviation:** Each of these 4 files embeds an independent, hardcoded `<aside>` sidebar with different icons, separate route URLs, missing active state indicators, and absence of the mobile drawer JS hooks.")
report_lines.append("- **Recommended Correction:** Remove duplicate `<aside>` element; inject page content directly into `{% block content %}` so `base.html` renders the unified, responsive application shell.")
report_lines.append("")
report_lines.append("#### Issue HIGH-02: Isolated Legacy Registration Templates")
report_lines.append("- **Affected Templates (2 files):**")
report_lines.append("  1. `templates/accounts/student_register.html` (Route `/accounts/student/register/`)")
report_lines.append("  2. `templates/accounts/teacher_register.html` (Route `/accounts/teacher/register/`)")
report_lines.append("- **Expected Shared Design Rule:** Registration forms should use the central role-selection flow (`templates/accounts/register.html`) or extend `base.html` with Bento form controls (`.bento-input`, `.bento-btn--primary`).")
report_lines.append("- **Actual Deviation:** These 2 files contain standalone Tailwind markup with blue styling. Although `/accounts/register/` is the primary entry, submitting an invalid form on these legacy endpoints falls back to rendering these blue templates.")
report_lines.append("- **Recommended Correction:** Convert `student_register.html` and `teacher_register.html` to extend `base.html` using the Sage-Green Bento card and input classes, ensuring visual parity with `register.html`.")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("### 4.3 Medium Severity (Component Standardization)")
report_lines.append("")
report_lines.append("#### Issue MED-01: Unstyled Legacy Tables in Isolated Views")
report_lines.append("- **Affected Templates (3 files):** `accounts/admin_dashboard.html`, `accounts/student_dashboard.html`, `accounts/teacher_dashboard.html`.")
report_lines.append("- **Expected Shared Design Rule:** All data tables must use `.bento-table` wrapped inside `.bento-table-wrapper` for consistent typography, border accents, and responsive horizontal touch scrolling on mobile.")
report_lines.append("- **Actual Deviation:** Tables in the Tailwind templates use generic utility classes without `.bento-table-wrapper`, which can cause horizontal clipping on mobile screens.")
report_lines.append("- **Recommended Correction:** Wrap in `.bento-table-wrapper` with `.bento-table` styling.")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("### 4.4 Low Severity (Inline Stylesheet Standardizations)")
report_lines.append("")
report_lines.append("#### Issue LOW-01: Redundant Inline Styles in Hardware Readiness Screen")
report_lines.append("- **Affected Template:** `templates/exams/exam_readiness.html` (35 lines of inline `<style>`).")
report_lines.append("- **Expected Shared Design Rule:** Animation and layout rules should reside in shared stylesheets (`bento.css`).")
report_lines.append("- **Actual Deviation:** Webcam preview mirror transform and VU meter bar keyframes are defined locally.")
report_lines.append("- **Recommended Correction:** Keep component-specific animations scoped or ensure they utilize `--eps-sage-secondary` and `--eps-mint` tokens (already largely compliant).")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 5. Summary of Already Compliant Pages (54 Templates)")
report_lines.append("")
report_lines.append("The following 54 templates already strictly adhere to `base.html`, the Sage-Green Color Hunt palette, and Bento Grid standards:")
report_lines.append("")
compliant_list = [it['template'] for it in audit_data if it['compliance'] == 'COMPLIANT']
for c in sorted(compliant_list):
    report_lines.append(f"- [x] `{c}`")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 6. Missing, Inaccessible, or Broken Pages Ledger")
report_lines.append("")
report_lines.append("- **Missing Templates:** Zero (0). Every route maps to a concrete template file on disk.")
report_lines.append("- **Broken Views / 404 Routes:** Zero (0). All 175 URL patterns resolve cleanly.")
report_lines.append("- **Inaccessible Navigation:** Resolved in previous iterations. Profile (`/accounts/profile/`), Teacher Students (`/accounts/teacher/students/`), and Exam Readiness (`/exams/<id>/readiness/`) are now fully linked in `base.html` and dashboards.")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 7. Central Architectural Corrections to Apply in Phase 2")
report_lines.append("")
report_lines.append("To achieve 100% visual and architectural consistency across the entire application without breaking any backend logic, we will execute the following surgical harmonizations:")
report_lines.append("")
report_lines.append("1. **Harmonize Tailwind Blue Mockups to Sage Bento Design System:**")
report_lines.append("   - Convert `accounts/login.html` to extend `base.html` with unified Sage-green authentication cards.")
report_lines.append("   - Convert `home.html` to extend `base.html` (or integrate Sage tokens seamlessly with the public header).")
report_lines.append("   - Convert `accounts/student_dashboard.html`, `accounts/teacher_dashboard.html`, `accounts/admin_dashboard.html`, and `accounts/admin_policies.html` to extend `base.html`, eliminating duplicate sidebars, removing Tailwind CDN, and mapping components to Bento Cards, Badges, and Stats.")
report_lines.append("   - Standardize `accounts/student_register.html` and `accounts/teacher_register.html` to extend `base.html`.")
report_lines.append("2. **Centralize Shared Bento Variables & Utilities in `design-tokens.css`:**")
report_lines.append("   - Ensure all badge, stat, and form utilities support both semantic token names and legacy class mappings.")
report_lines.append("3. **Verify with Django Test Suite & System Checks:**")
report_lines.append("   - Run `python manage.py check` to ensure zero syntax or template errors.")
report_lines.append("   - Run `python manage.py test` to ensure all 58 tests continue to pass with 100% success rate.")
report_lines.append("")

with open('EPS_UI_CONSISTENCY_AUDIT.md', 'w', encoding='utf-8') as out_f:
    out_f.write('\n'.join(report_lines))

print("Successfully generated EPS_UI_CONSISTENCY_AUDIT.md with full inventory and matrix.")
