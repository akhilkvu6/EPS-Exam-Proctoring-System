import asyncio
import aiohttp
import subprocess
import base64
import os

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
artifact_dir = r'C:\Users\akhil\.gemini\antigravity\brain\7803f368-4895-48f6-848f-f72cd4bf5659'
user_data_dir = r'c:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\scratch\edge_batch_profile'

async def main():
    os.makedirs(user_data_dir, exist_ok=True)
    proc = subprocess.Popen([
        edge_path,
        '--headless',
        '--disable-gpu',
        '--remote-debugging-port=9222',
        f'--user-data-dir={user_data_dir}',
        '--window-size=1280,900',
        'http://127.0.0.1:8000/accounts/login/'
    ])
    await asyncio.sleep(2.5)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://127.0.0.1:9222/json') as resp:
                tabs = await resp.json()
            ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if 'http://127.0.0.1:8000/' in t.get('url', ''))

            async with session.ws_connect(ws_url) as ws:
                cid = 1
                async def send(method, params=None):
                    nonlocal cid
                    curr_id = cid
                    cid += 1
                    await ws.send_json({'id': curr_id, 'method': method, 'params': params or {}})
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == curr_id:
                            return msg.get('result', {})

                await send('Page.enable')

                async def snap(url, filename, width=1280, height=900, evaluate_js=None, wait_time=2.0):
                    await send('Emulation.setDeviceMetricsOverride', {
                        'width': width,
                        'height': height,
                        'deviceScaleFactor': 1,
                        'mobile': width < 600
                    })
                    await send('Page.navigate', {'url': url})
                    await asyncio.sleep(wait_time)

                    if evaluate_js:
                        await send('Runtime.evaluate', {'expression': evaluate_js})
                        await asyncio.sleep(1.0)

                    res = await send('Page.captureScreenshot', {'format': 'png'})
                    img_data = base64.b64decode(res['data'])
                    filepath = os.path.join(artifact_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                    print(f"Captured: {filename} ({len(img_data)} bytes)")

                # 1. Student Registration with Academic Batch & Visual Roll Grid
                student_reg_js = """
                (async function() {
                    const sel = document.getElementById('student-batch-select');
                    if (sel && sel.options.length > 1) {
                        sel.selectedIndex = 1;
                        sel.dispatchEvent(new Event('change'));
                        for (let i = 0; i < 20; i++) {
                            await new Promise(r => setTimeout(r, 200));
                            const cells = document.querySelectorAll('.roll-cell-reg--available');
                            if (cells.length > 0) {
                                cells[0].click();
                                break;
                            }
                        }
                    }
                })();
                """
                await snap('http://127.0.0.1:8000/accounts/register/?role=student', 'batch_student_registration_grid.png', 1280, 1050, evaluate_js=student_reg_js, wait_time=2.5)

                # 2. Login as admin
                admin_login_js = """
                (function() {
                    const idInput = document.getElementById('login-identifier-input');
                    const pwdInput = document.getElementById('login-password-input');
                    const btn = document.getElementById('login-submit-btn');
                    if (idInput && pwdInput && btn) {
                        idInput.value = 'admin';
                        pwdInput.value = 'admin123';
                        btn.click();
                    }
                })();
                """
                await send('Page.navigate', {'url': 'http://127.0.0.1:8000/accounts/login/'})
                await asyncio.sleep(2.0)
                await send('Runtime.evaluate', {'expression': admin_login_js})
                await asyncio.sleep(3.0)

                # 3. Admin Batches Dashboard
                await snap('http://127.0.0.1:8000/accounts/admin/batches/', 'batch_admin_batches_dashboard.png', 1280, 900)

                # 4. Admin Batch Detail with 01-60 Roll Availability Grid
                await snap('http://127.0.0.1:8000/accounts/admin/batches/1/', 'batch_admin_detail_grid.png', 1280, 1050)

                # 5. Batch Semester Promotion
                await snap('http://127.0.0.1:8000/accounts/admin/batches/1/promote/', 'batch_admin_promote.png', 1280, 900)

                # 6. Controlled Roll Number Correction
                await snap('http://127.0.0.1:8000/accounts/admin/roll-correction/', 'batch_admin_roll_correction.png', 1280, 950)

    finally:
        proc.terminate()

if __name__ == '__main__':
    asyncio.run(main())
