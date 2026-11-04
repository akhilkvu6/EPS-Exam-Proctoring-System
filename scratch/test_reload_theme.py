import asyncio
import aiohttp
import subprocess
import time

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

async def main():
    user_data_dir = r'c:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\scratch\edge_profile'
    proc = subprocess.Popen([
        edge_path,
        '--headless',
        '--disable-gpu',
        '--remote-debugging-port=9222',
        f'--user-data-dir={user_data_dir}',
        'http://127.0.0.1:8000/design/'
    ])
    await asyncio.sleep(2)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://127.0.0.1:9222/json') as resp:
                tabs = await resp.json()
            ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if 'http://127.0.0.1:8000/design/' in t.get('url', ''))
            async with session.ws_connect(ws_url) as ws:
                async def eval_js(js):
                    await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
                    msg = await ws.receive_json()
                    return msg.get('result', {}).get('result', {}).get('value')

                # Clear localStorage and set light
                await eval_js("localStorage.setItem('eps-theme', 'light');")
                # Reload page
                await ws.send_json({'id': 2, 'method': 'Page.reload', 'params': {}})
                await ws.receive_json()
                await asyncio.sleep(1)

                res = await eval_js("""
                (function() {
                    const el = document.querySelector('.semantic-matrix-table .btn-danger');
                    const cs = window.getComputedStyle(el);
                    return {
                        theme: document.documentElement.getAttribute('data-theme'),
                        bg: cs.backgroundColor,
                        color: cs.color,
                        token: window.getComputedStyle(document.documentElement).getPropertyValue('--color-danger').trim()
                    };
                })()
                """)
                print('Reloaded with Light in localStorage:', res)

                # Now set to dark in localStorage and reload
                await eval_js("localStorage.setItem('eps-theme', 'dark');")
                await ws.send_json({'id': 3, 'method': 'Page.reload', 'params': {}})
                await ws.receive_json()
                await asyncio.sleep(1)

                res_dark = await eval_js("""
                (function() {
                    const el = document.querySelector('.semantic-matrix-table .btn-danger');
                    const cs = window.getComputedStyle(el);
                    return {
                        theme: document.documentElement.getAttribute('data-theme'),
                        bg: cs.backgroundColor,
                        color: cs.color,
                        token: window.getComputedStyle(document.documentElement).getPropertyValue('--color-danger').trim()
                    };
                })()
                """)
                print('Reloaded with Dark in localStorage:', res_dark)

    finally:
        proc.terminate()

asyncio.run(main())
