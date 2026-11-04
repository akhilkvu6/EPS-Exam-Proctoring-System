# EPS Phoenix (Examination Proctoring System Phoenix)

[![Django Version](https://img.shields.io/badge/Django-5.1-092e20?logo=django)](https://www.djangoproject.com/)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?logo=python)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql)](https://www.postgresql.org/)
[![Build & Test Status](https://img.shields.io/badge/Tests-109%20Passed%20(100%25)-success)](#automated-testing)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-orange)](#system-architecture)

**EPS Phoenix** is an enterprise-grade, highly secure, production-ready online examination and intelligent proctoring platform developed for institutional education.

---

## 🏛️ Core Features Across Lifecycle

1. **Identity & Authentication**: Custom `User` model with strict Role-Based Access Control (`ADMIN`, `TEACHER`, `STUDENT`) and role-segregated login workflows.
2. **Admissions & Roll Allocation**: Monotonically increasing sequential roll number allocation utilizing database row-level locking (`select_for_update`) to prevent race conditions during concurrent faculty approvals.
3. **Academic Scoping**: Full academic hierarchy: Department &rarr; Course &rarr; Academic Batch &rarr; Semester &rarr; Subject &rarr; Teacher Assignment &rarr; Student Enrollment.
4. **Question Bank**: 8 supported question formats (Single MCQ, Multi MCQ, True/False, Blanks, Numerical with tolerance window, Short Answer, Descriptive with rubrics, and Image-based prompts). Questions lock onto immutable, versioned `QuestionSnapshot` records when added to exams.
5. **Examination Delivery Engine**: Distraction-free exam room with server-authoritative countdown timers (`expires_at`), anti-tampering guards, and cryptographic SHA-256 submission receipts.
6. **Dual-Layer Autosave**:
   - *Layer 1*: 600ms debounced network persistence to transactional sync endpoint.
   - *Layer 2*: Offline IndexedDB/localStorage journal that seamlessly queues answers during network dropouts and flushes upon reconnection.
7. **Privacy-First AI & Browser Proctoring**:
   - **Strictly Zero Continuous Video/Audio Recording** across the entire platform.
   - Client-side edge computer vision telemetry (offscreen canvas heuristics) detects presence, multiple faces, device intrusion, and gaze deviation.
   - 1.5-second OS window blur noise-filtering eliminates false positives.
   - Dynamic candidate Trust Score tracking.
8. **Live Invigilator Console**: Real-time candidate monitoring dashboard allowing faculty to issue warning alerts, grant time extensions, and terminate attempts for cause.
9. **Deterministic Evaluation**: Automated grading for objective question types, negative marking support, and an intuitive subjective rubric grading queue for faculty.
10. **Cryptographic Scorecards**: Cohort results publication with institutional grading scale (`O`, `A+`, `A`, `B+`, `B`, `C`, `F`), ReportLab PDF transcript generation, and a public verification portal.
11. **Appearance Customization**: ChatGPT-inspired appearance engine supporting Light, Dark, and System modes, custom accent colors, layout density controls, and high-contrast accessibility.
12. **In-App Notifications**: Real-time notification dispatcher and unread badge indicator.

---

## 📐 System Architecture & Technology Stack

- **Backend**: Python 3.13 + Django 5.1 (Modular Monolith)
- **Frontend**: Django Templates + HTML5 + CSS3 (Design Tokens) + Vanilla JavaScript (Strictly NO React / Next.js / SPAs)
- **Database**: PostgreSQL (Authoritative Production DB) / SQLite (Local Development Fallback)
- **Application Server**: Gunicorn (`gthread` worker model)
- **Web Server / Reverse Proxy**: Nginx (SSL/TLS, HSTS, Static/Media Routing)
- **PDF Engine**: ReportLab 4.2+
- **Image Processing**: Pillow 10.4+

For architectural diagrams and data flows, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).  
For the faculty and administrator operating manual, see [docs/ADMINISTRATIVE_HANDBOOK.md](docs/ADMINISTRATIVE_HANDBOOK.md).

---

## 📁 Project Structure

```text
EPS-Exam-Proctoring-System/
├── manage.py
├── requirements.txt
├── .env.example
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── gunicorn.conf.py
│   ├── nginx/
│   │   └── eps_phoenix.conf
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/          # Custom User, Auth, RBAC
│   ├── administration/    # Institutional Governance & Audit Logs
│   ├── admissions/        # Concurrency-safe roll allocation
│   ├── academics/         # Dept -> Course -> Batch -> Subject hierarchy
│   ├── question_bank/     # Multi-format items, versioned snapshots
│   ├── examinations/      # Scheduling & cohort rosters
│   ├── exam_engine/       # Delivery room, timer, dual-layer autosave
│   ├── proctoring/        # Edge AI telemetry, noise filtering, trust score
│   ├── incidents/         # Live invigilator console, warnings
│   ├── evaluation/        # Deterministic auto-grader, subjective rubrics
│   ├── results/           # PDF scorecards, verification portal
│   ├── notifications/     # Notification dispatcher, badge counts
│   ├── appearance/        # ChatGPT-inspired personalization
│   ├── student/           # Student workspace, self-service dashboard
│   ├── teacher/           # Faculty workspace, admission review
│   └── core/              # Design tokens, error views, health checks
├── templates/             # SSR templates & UI components
├── static/                # CSS design tokens, Vanilla JS engines
├── media/                 # Question diagrams & uploaded documents
├── docs/                  # Architecture & Administrative Handbooks
└── tests/                 # Integration, E2E lifecycle & security audit suites
```

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10 - 3.13
- PostgreSQL (Production) or SQLite (Local Dev)
- Git

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/akhilkvu6/EPS-Exam-Proctoring-System.git
cd EPS-Exam-Proctoring-System

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Upgrade pip & install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```
Ensure `DJANGO_SETTINGS_MODULE=config.settings.development` for local work or `config.settings.production` for production.

### 3. Run Migrations & Provision Admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Automated Testing

EPS Phoenix maintains a 100% passing automated test suite covering all modules, end-to-end examination lifecycles, and security invariants:

```bash
# Run the entire test suite (109 tests across all apps and suites)
python manage.py test

# Run End-to-End Lifecycle Integration Test
python manage.py test tests.test_e2e_lifecycle

# Run Comprehensive Security & IDOR Hardening Audit
python manage.py test tests.test_security_audit
```

---

## 🚢 Production Deployment

### 1. Pre-Deployment Check
```bash
python manage.py check --deploy --settings=config.settings.production
```

### 2. Static Assets Compilation
```bash
python manage.py collectstatic --noinput --settings=config.settings.production
```

### 3. Launching Gunicorn
```bash
gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

### 4. Configuring Nginx
Deploy the provided [config/nginx/eps_phoenix.conf](config/nginx/eps_phoenix.conf) to `/etc/nginx/sites-available/` and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/eps_phoenix.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📄 License & Institutional Rights

© 2026 EPS Phoenix. Developed as an institutional examination and intelligent proctoring platform. All rights reserved.
