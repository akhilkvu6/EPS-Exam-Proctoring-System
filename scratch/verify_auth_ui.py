import asyncio
import aiohttp
import subprocess
import base64
import os

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
artifact_dir = r'C:\Users\akhil\.gemini\antigravity\brain\7803f368-4895-48f6-848f-f72cd4bf5659'
user_data_dir = r'c:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\scratch\edge_auth_profile'

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

                async def snap(url, filename, width=1280, height=900):
                    await send('Emulation.setDeviceMetricsOverride', {
                        'width': width,
                        'height': height,
                        'deviceScaleFactor': 1,
                        'mobile': width < 600
                    })
                    await send('Page.navigate', {'url': url})
                    await asyncio.sleep(1.8)
                    shot = await send('Page.captureScreenshot', {'format': 'png'})
                    img_bytes = base64.b64decode(shot['data'])
                    out_path = os.path.join(artifact_dir, filename)
                    with open(out_path, 'wb') as f:
                        f.write(img_bytes)
                    print(f'Captured {filename}: {len(img_bytes)} bytes')

                await snap('http://127.0.0.1:8000/accounts/login/', 'auth_login_desktop.png', 1280, 850)
                await snap('http://127.0.0.1:8000/accounts/login/', 'auth_login_mobile.png', 375, 812)
                await snap('http://127.0.0.1:8000/accounts/register/', 'auth_register_roles.png', 1280, 900)
                await snap('http://127.0.0.1:8000/accounts/register/?role=student', 'auth_register_student.png', 1280, 1100)
                await snap('http://127.0.0.1:8000/accounts/register/?role=teacher', 'auth_register_teacher.png', 1280, 1100)
                print('All 5 screenshots taken successfully!')
    finally:
        proc.kill()

if __name__ == '__main__':
    asyncio.run(main())
