import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam.settings')
import django
django.setup()
from django.test import Client

c = Client()
pages_to_check = [
    ('/', 200, 'Landing Page'),
    ('/accounts/login/', 200, 'Login Page'),
    ('/accounts/register/', 200, 'Register Page'),
    ('/accounts/student/login/', 200, 'Student Login'),
    ('/accounts/teacher/login/', 200, 'Teacher Login'),
    ('/design/', 200, 'Design Foundation'),
]

for url, expected_status, label in pages_to_check:
    resp = c.get(url)
    status_match = resp.status_code == expected_status
    print(f"{label} ({url}): status {resp.status_code} [Expected {expected_status}] -> {'OK' if status_match else 'FAIL'}")
    if url in ['/accounts/login/', '/accounts/register/']:
        content = resp.content.decode('utf-8')
        # Check that public-header is preserved on guest pages
        has_public_header = 'public-header' in content
        print(f"  {label} retains default public-header: {has_public_header}")
