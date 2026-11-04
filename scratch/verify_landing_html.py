import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam.settings')
import django
django.setup()
from django.test import Client
from django.urls import reverse

c = Client()
resp = c.get('/')
print('Homepage status code:', resp.status_code)
content = resp.content.decode('utf-8')

# Verify sections
expected_sections = [
    'SECTION 1: STICKY NAVIGATION BAR',
    'SECTION 2: HERO SECTION',
    'SECTION 3: PLATFORM OVERVIEW',
    'SECTION 4: EXAMINATION LIFECYCLE',
    'SECTION 5: INTELLIGENT PROCTORING',
    'SECTION 6: STUDENT EXPERIENCE',
    'SECTION 7: TEACHER EXPERIENCE',
    'SECTION 8: ADMINISTRATION',
    'SECTION 9: RESULTS AND EVALUATION',
    'SECTION 10: SECURITY AND TRANSPARENCY',
    'SECTION 11: THREE ROLES, ONE PLATFORM',
    'SECTION 12: FINAL CALL TO ACTION',
    'SECTION 13: FOOTER'
]

for s in expected_sections:
    if s in content:
        print(f'  [PASS] Found {s}')
    else:
        print(f'  [FAIL] Missing {s}')

# Verify navigation links
anchors = ['#features', '#workflow', '#teachers', '#students', '#security']
for a in anchors:
    target_id = a.replace('#', '')
    has_target = f'id="{target_id}"' in content
    print(f'  Anchor {a} -> Target id="{target_id}" exists: {has_target}')

# Verify login & register URLs
login_url = reverse('common_login')
register_url = reverse('register')
print(f'  Login URL: {login_url} in content: {login_url in content}')
print(f'  Register URL: {register_url} in content: {register_url in content}')
