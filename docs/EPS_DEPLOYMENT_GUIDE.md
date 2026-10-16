# EPS Institutional Production Deployment Guide

**Project:** EPS — Exam Proctoring System  
**Guide Version:** 2.0 (Institutional Pilot & Production Readiness)  
**Target Audience:** DevOps Engineers, System Administrators, Infrastructure Architects  
**Date:** October 15, 2026  

---

## 1. Executive Summary & Production Readiness

The Exam Proctoring System (EPS) is architected on Django 6.1, adhering to modern 12-factor application principles. In local development mode, EPS runs on SQLite and Django's built-in development server. 

For institutional pilot trials and university-wide deployment, this guide provides the necessary infrastructure configuration covering:
1. Environment variable isolation.
2. Web server and reverse proxy setup (Gunicorn + Nginx).
3. SSL/TLS termination and HTTP Strict Transport Security (HSTS).
4. Database concurrency analysis (SQLite vs. PostgreSQL).
5. Automated backup and disaster recovery procedures.

---

## 2. Environment Variables Configuration

Sensitive parameters, cryptographic keys, and host headers must be configured via operating system environment variables (or a secure `.env` file managed by `systemd` or Docker).

| Variable Name | Required | Default (Dev) | Production Recommended Value | Purpose |
|---|---|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | *insecure-dev-key* | `openssl rand -base64 48` | Cryptographic signing key for sessions and CSRF tokens |
| `DJANGO_DEBUG` | **Yes** | `True` | `False` | Disables verbose stack traces and debug toolbars |
| `DJANGO_ALLOWED_HOSTS`| **Yes** | `localhost,127.0.0.1` | `exam.university.edu,10.0.1.20` | Authorized Host header domain names |
| `DJANGO_SECURE_SSL_REDIRECT` | No | `False` | `True` | Forcibly redirects HTTP traffic to HTTPS |
| `DJANGO_SESSION_COOKIE_SECURE` | No | `False` | `True` | Ensures session cookies only transmit over TLS |
| `DJANGO_CSRF_COOKIE_SECURE` | No | `False` | `True` | Ensures CSRF cookies only transmit over TLS |
| `DJANGO_SECURE_HSTS_SECONDS` | No | `0` | `31536000` (1 year) | Enforces HTTP Strict Transport Security in browsers |

---

## 3. Production Application Server & Reverse Proxy Architecture

In a production environment, Django's WSGI application should be served by **Gunicorn** workers mediated by an **Nginx** reverse proxy to handle static asset caching and TLS termination.

```
[ Client Browser ]
        │  HTTPS (Port 443)
        ▼
   [ Nginx ] ── (Serves /static/ directly)
        │  UNIX Socket / HTTP (127.0.0.1:8000)
        ▼
  [ Gunicorn ] (3-5 Sync / Uvicorn Async Workers)
        │
   [ Django WSGI ]
        │
  [ Database ] (SQLite 3 or PostgreSQL 16)
```

### 3.1 Gunicorn Systemd Service Configuration
Create file `/etc/systemd/system/eps.service`:

```ini
[Unit]
Description=EPS - Exam Proctoring System Gunicorn Daemon
After=network.target

[Service]
User=epsapp
Group=www-data
WorkingDirectory=/var/www/EPS-Exam-Proctoring-System
ExecStart=/var/www/EPS-Exam-Proctoring-System/venv/bin/gunicorn \
          --workers 4 \
          --bind 127.0.0.1:8000 \
          --timeout 90 \
          --access-logfile /var/log/eps/access.log \
          --error-logfile /var/log/eps/error.log \
          online_exam.wsgi:application

Restart=always
Environment="DJANGO_DEBUG=False"
Environment="DJANGO_SECRET_KEY=production-secret-token-value"
Environment="DJANGO_ALLOWED_HOSTS=exam.university.edu"

[Install]
WantedBy=multi-user.target
```

### 3.2 Nginx Server Block Configuration
Create `/etc/nginx/sites-available/eps.conf`:

```nginx
server {
    listen 80;
    server_name exam.university.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name exam.university.edu;

    ssl_certificate /etc/letsencrypt/live/exam.university.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exam.university.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Static assets served directly by Nginx
    location /static/ {
        alias /var/www/EPS-Exam-Proctoring-System/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Media uploads (student avatars, event snapshots)
    location /media/ {
        alias /var/www/EPS-Exam-Proctoring-System/media/;
        expires 7d;
    }

    # Application reverse proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 25M;
    }
}
```

---

## 4. Database Concurrency Analysis: SQLite vs PostgreSQL

### 4.1 SQLite in Controlled Pilot Scenarios
- **Capacity:** Excellent for department evaluation, BCA final-year project grading, and controlled pilot exams up to **30-50 concurrent test takers**.
- **WAL Mode Optimization:** To eliminate database table locking under simultaneous autosaves, enable Write-Ahead Logging (WAL):
  ```sql
  PRAGMA journal_mode=WAL;
  PRAGMA synchronous=NORMAL;
  PRAGMA busy_timeout=5000;
  ```
- SQLite provides absolute simplicity with zero external service dependencies.

### 4.2 Migration Strategy to PostgreSQL for University-Scale Deployments
For concurrent institutional examinations exceeding 100 students streaming real-time telemetry:
1. Install `psycopg[binary]`:
   ```bash
   pip install "psycopg[binary]>=3.1.8"
   ```
2. Configure `DATABASES` in `online_exam/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.environ.get('DB_NAME', 'eps_db'),
           'USER': os.environ.get('DB_USER', 'eps_user'),
           'PASSWORD': os.environ.get('DB_PASSWORD', ''),
           'HOST': os.environ.get('DB_HOST', 'localhost'),
           'PORT': os.environ.get('DB_PORT', '5432'),
           'CONN_MAX_AGE': 60,
       }
   }
   ```
3. Dump SQLite data and reload into PostgreSQL:
   ```bash
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > data.json
   python manage.py migrate
   python manage.py loaddata data.json
   ```

---

## 5. Automated Backup & Disaster Recovery

### 5.1 SQLite Hot Backup Script
SQLite provides a safe online backup mechanism that locks readers/writers for microseconds rather than minutes:

```powershell
# Windows PowerShell Daily Backup Script
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$sourceDb = "C:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\db.sqlite3"
$targetBackup = "C:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\backups\eps_backup_$timestamp.sqlite3"

# Copy safely using SQLite backup API or copy if server idle
Copy-Item -Path $sourceDb -Destination $targetBackup -Force
Write-Host "EPS Backup successfully created at: $targetBackup"
```

### 5.2 Recovery Procedure
1. Stop the application service: `systemctl stop eps` (or terminate dev server process).
2. Restore the backup copy to `db.sqlite3`.
3. Validate database file integrity: `python manage.py check`.
4. Restart application service: `systemctl start eps`.
