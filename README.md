# EPS Phoenix (Examination Proctoring System Phoenix)

EPS Phoenix is an enterprise-grade, secure, production-oriented online examination and intelligent proctoring platform for institutional education.

## Architecture

- **Backend**: Python + Django (Modular Monolith)
- **Frontend**: Django Templates + HTML5 + CSS3 (Design Tokens) + Vanilla JavaScript
- **Database**: PostgreSQL (Authoritative Production DB)
- **Security & Privacy**: Zero continuous video recording; client-side hybrid event monitoring; server-authoritative timers; concurrency-safe roll allocation; strictly scoped academic permissions.

## Directory Structure

```text
eps_phoenix/
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/
│   ├── accounts/
│   ├── admissions/
│   ├── academics/
│   ├── assignments/
│   ├── question_bank/
│   ├── examinations/
│   ├── exam_engine/
│   ├── proctoring/
│   ├── incidents/
│   ├── evaluation/
│   ├── results/
│   └── appearance/
├── templates/
│   ├── base/
│   ├── components/
│   ├── accounts/
│   ├── admin/
│   ├── teacher/
│   ├── student/
│   └── errors/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── tests/
```

## Setup & Installation

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```
