"""
Gunicorn Production Server Configuration for EPS Phoenix.
Compliant with Section 3.4 & Section 21 (Production Deployment & Hardening).
"""

import multiprocessing
import os

# Server Socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker Processes & Concurrency
# Formula: (2 * CPU cores) + 1 for high-throughput WSGI concurrency
workers = int(os.environ.get("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_connections = 1000
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 60))
keepalive = 5

# Memory Leak Prevention & Lifecycle Management
max_requests = 1200
max_requests_jitter = 150

# Security & Limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging Configuration
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"   # stderr
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s µs'

# Process Naming
proc_name = "eps_phoenix_wsgi"
