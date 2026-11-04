import asyncio
import aiohttp
import subprocess
import time
import base64

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

async def main():
    user_data_dir = r'c:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\scratch\edge_profile'
    proc = subprocess.Popen([
        edge_path,
        '--headless',
        '--disable-gpu',
        '--remote-debugging-port=9222',
        f'--user-data-dir={user_data_dir}',
        '--window-size=1280,1024',
        'http://127.0.0.1:8000/design/'
    ])
    await asyncio.sleep(2)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://127.0.0.1:9222/json') as resp:
                tabs = await resp.json()
            ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if 'http://127.0.0.1:8000/design/' in t.get('url', ''))
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

                async def reload_page():
                    await send('Page.reload')
                    await asyncio.sleep(1.5)

                async def capture_viewport(scroll_to_sel, output_path):
                    await send('Runtime.evaluate', {
                        'expression': f"document.querySelector('{scroll_to_sel}').scrollIntoView({{ behavior: 'instant', block: 'start' }});"
                    })
                    await asyncio.sleep(0.5)
                    shot = await send('Page.captureScreenshot', {'format': 'png'})
                    if 'data' in shot:
                        with open(output_path, 'wb') as f:
                            f.write(base64.b64decode(shot['data']))
                        print(f"Captured {output_path} at {scroll_to_sel}")

                # 1. Dark Mode
                await send('Runtime.evaluate', {'expression': "localStorage.setItem('eps-theme', 'dark');"})
                await reload_page()
                await capture_viewport('.semantic-matrix-table', r'scratch\dark_sec2_matrix_view.png')
                await capture_viewport('#buttons', r'scratch\dark_sec4_buttons_view.png')

                # 2. Light Mode
                await send('Runtime.evaluate', {'expression': "localStorage.setItem('eps-theme', 'light');"})
                await reload_page()
                await capture_viewport('.semantic-matrix-table', r'scratch\light_sec2_matrix_view.png')
                await capture_viewport('#buttons', r'scratch\light_sec4_buttons_view.png')

    finally:
        proc.terminate()

asyncio.run(main())
