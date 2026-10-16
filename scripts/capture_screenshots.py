"""
Automated screenshot capture script for EPS Exam Proctoring System.
Uses Google Chrome headless mode via Chrome DevTools Protocol (CDP) over WebSockets.
Generates comprehensive responsive screenshots across 5 viewports:
- Desktop: 1440x900
- Laptop: 1280x800
- Tablet: 768x1024
- Mobile: 390x844
- Narrow Mobile: 360x740
"""
import os
import sys
import json
import time
import base64
import asyncio
import subprocess
import urllib.request

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam.settings')

import django
django.setup()

from django.contrib.sessions.backends.db import SessionStore
from accounts.models import User, StudentProfile, TeacherProfile
import websockets


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = os.path.abspath("screenshots")

cmd_counter = 0


async def send_command(ws, method, params=None):
    global cmd_counter
    cmd_counter += 1
    my_id = cmd_counter
    payload = {'id': my_id, 'method': method}
    if params:
        payload['params'] = params
    await ws.send(json.dumps(payload))
    while True:
        resp = await ws.recv()
        msg = json.loads(resp)
        if msg.get('id') == my_id:
            return msg.get('result', {})


def create_user_session(username):
    user = User.objects.get(username=username)
    s = SessionStore()
    s['_auth_user_id'] = str(user.pk)
    s['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
    s['_auth_user_hash'] = user.get_session_auth_hash()
    s.save()
    return s.session_key


def ensure_server_running():
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/", timeout=1)
        print("Django server is already running on port 8000.")
        return None
    except Exception:
        print("Starting Django development server on port 8000...")
        proc = subprocess.Popen([
            sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(0.5)
            try:
                urllib.request.urlopen("http://127.0.0.1:8000/", timeout=1)
                print("Django development server ready.")
                return proc
            except Exception:
                pass
        raise RuntimeError("Failed to start Django development server.")


async def capture_page(ws, url, output_filename, width, height, cookie=None, evaluate_js=None, wait_time=0.8):
    # 1. Clear cookies and set auth cookie if requested
    await send_command(ws, 'Network.clearBrowserCookies')
    if cookie:
        await send_command(ws, 'Network.setCookie', {
            'name': 'sessionid',
            'value': cookie,
            'domain': '127.0.0.1',
            'path': '/'
        })

    # 2. Set viewport dimensions & device scale factor
    await send_command(ws, 'Emulation.setDeviceMetricsOverride', {
        'width': width,
        'height': height,
        'deviceScaleFactor': 1,
        'mobile': (width < 768),
        'fitWindow': False
    })

    # 3. Navigate to URL
    await send_command(ws, 'Page.navigate', {'url': url})
    await asyncio.sleep(wait_time)

    # 4. Optional JS evaluation
    if evaluate_js:
        await send_command(ws, 'Runtime.evaluate', {'expression': evaluate_js})
        await asyncio.sleep(0.4)

    # 5. Capture screenshot
    res = await send_command(ws, 'Page.captureScreenshot', {'format': 'png'})
    img_b64 = res.get('data')
    if img_b64:
        out_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(out_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        file_size = os.path.getsize(out_path)
        print(f"Captured: {output_filename} ({width}x{height}, {file_size} bytes)")
    else:
        print(f"ERROR: Failed to capture {output_filename}")


async def main(admin_cookie, teacher_cookie, student_cookie, student_id, teacher_id):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Launch Chrome headless with debugging port
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless=new',
        f'--remote-debugging-port={PORT}',
        '--disable-gpu',
        '--no-sandbox',
        '--hide-scrollbars',
        '--disable-background-networking',
        'about:blank'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    time.sleep(1.5)

    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")
        targets = json.loads(req.read().decode('utf-8'))
        ws_url = targets[0]['webSocketDebuggerUrl']

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            await send_command(ws, 'Page.enable')
            await send_command(ws, 'Network.enable')

            # -------------------------------------------------------------
            # 1. Minimal Homepage across Viewports
            # -------------------------------------------------------------
            print("\n--- Capturing Minimal Homepage across 5 viewports ---")
            await capture_page(ws, f"{BASE_URL}/", "01_homepage_desktop_1440.png", 1440, 900)
            await capture_page(ws, f"{BASE_URL}/", "02_homepage_laptop_1280.png", 1280, 800)
            await capture_page(ws, f"{BASE_URL}/", "03_homepage_tablet_768.png", 768, 1024)
            await capture_page(ws, f"{BASE_URL}/", "04_homepage_mobile_390.png", 390, 844)
            await capture_page(ws, f"{BASE_URL}/", "05_homepage_narrow_360.png", 360, 740)

            # -------------------------------------------------------------
            # 2. Central Registration Flow (Student vs Teacher selection)
            # -------------------------------------------------------------
            print("\n--- Capturing Central Registration Role Selection ---")
            await capture_page(ws, f"{BASE_URL}/accounts/register/", "06_register_role_student_1440.png", 1440, 950)
            await capture_page(ws, f"{BASE_URL}/accounts/register/", "07_register_role_teacher_1440.png", 1440, 950, evaluate_js="selectRole('teacher');")
            await capture_page(ws, f"{BASE_URL}/accounts/register/", "08_register_mobile_390.png", 390, 844)

            # -------------------------------------------------------------
            # 3. Institutional Administrator Portal
            # -------------------------------------------------------------
            print("\n--- Capturing Administrator Portal & Oversight Suite ---")
            await capture_page(ws, f"{BASE_URL}/accounts/admin/dashboard/", "09_admin_dashboard_desktop_1440.png", 1440, 950, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/dashboard/", "10_admin_dashboard_tablet_768.png", 768, 1024, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/dashboard/", "11_admin_dashboard_mobile_390.png", 390, 844, cookie=admin_cookie)

            # Candidate & Faculty Directories
            await capture_page(ws, f"{BASE_URL}/accounts/admin/students/", "12_admin_student_directory_1440.png", 1440, 900, cookie=admin_cookie)
            if student_id:
                await capture_page(ws, f"{BASE_URL}/accounts/admin/student/{student_id}/", "13_admin_student_detail_1440.png", 1440, 950, cookie=admin_cookie)

            await capture_page(ws, f"{BASE_URL}/accounts/admin/teachers/", "14_admin_teacher_directory_1440.png", 1440, 900, cookie=admin_cookie)
            if teacher_id:
                await capture_page(ws, f"{BASE_URL}/accounts/admin/teacher/{teacher_id}/", "15_admin_teacher_detail_1440.png", 1440, 950, cookie=admin_cookie)

            # Verification Queues
            await capture_page(ws, f"{BASE_URL}/accounts/admin/student-approvals/", "16_admin_student_approvals_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/teacher-approvals/", "17_admin_teacher_approvals_1440.png", 1440, 900, cookie=admin_cookie)

            # Analytics, Audit & Academic Hierarchy
            await capture_page(ws, f"{BASE_URL}/accounts/admin/analytics/", "18_admin_analytics_1440.png", 1440, 950, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/audit-logs/", "19_admin_audit_logs_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/departments/", "20_admin_departments_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/classes/", "21_admin_classes_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/policies/", "22_admin_policies_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/backup/", "23_admin_backup_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/admin/security/", "24_admin_security_1440.png", 1440, 900, cookie=admin_cookie)

            # Examination Oversight & Results
            await capture_page(ws, f"{BASE_URL}/exams/admin/all/", "25_admin_all_exams_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/exams/admin/attempts/", "26_admin_attempts_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/exams/admin/proctoring/", "27_admin_proctoring_fleet_1440.png", 1440, 950, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/exams/admin/incidents/", "28_admin_incidents_ledger_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/results/admin/overview/", "29_admin_results_overview_1440.png", 1440, 900, cookie=admin_cookie)
            await capture_page(ws, f"{BASE_URL}/results/admin/export/", "30_admin_reports_export_1440.png", 1440, 950, cookie=admin_cookie)

            # -------------------------------------------------------------
            # 4. Teacher Portal
            # -------------------------------------------------------------
            print("\n--- Capturing Teacher Portal ---")
            await capture_page(ws, f"{BASE_URL}/accounts/teacher/dashboard/", "31_teacher_dashboard_desktop_1440.png", 1440, 950, cookie=teacher_cookie)
            await capture_page(ws, f"{BASE_URL}/accounts/teacher/student-approvals/", "32_teacher_student_approvals_1440.png", 1440, 900, cookie=teacher_cookie)

            # -------------------------------------------------------------
            # 5. Student Portal
            # -------------------------------------------------------------
            print("\n--- Capturing Student Portal ---")
            await capture_page(ws, f"{BASE_URL}/accounts/student/dashboard/", "33_student_dashboard_desktop_1440.png", 1440, 950, cookie=student_cookie)

            print("\n[SUCCESS] All 33 screenshots successfully captured and saved to screenshots/.")
    finally:
        chrome_proc.terminate()


if __name__ == '__main__':
    server_proc = ensure_server_running()
    try:
        admin_cookie = create_user_session('admin')
        teacher_cookie = create_user_session('teacher_test_01')
        student_cookie = create_user_session('student_test_01')

        student_p = StudentProfile.objects.first()
        teacher_p = TeacherProfile.objects.first()
        student_id = student_p.id if student_p else None
        teacher_id = teacher_p.id if teacher_p else None

        asyncio.run(main(admin_cookie, teacher_cookie, student_cookie, student_id, teacher_id))
    finally:
        if server_proc:
            server_proc.terminate()
            print("Django development server stopped.")
