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
                    await ws.send_json({'id': 100, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == 100:
                            return msg.get('result', {}).get('result', {}).get('value')

                info = await eval_js("""
                (function() {
                    const el = document.querySelector('.semantic-matrix-table .btn-danger');
                    const cs = window.getComputedStyle(el);
                    const docCs = window.getComputedStyle(document.documentElement);
                    return {
                        themeAttr: document.documentElement.getAttribute('data-theme'),
                        inlineStyle: document.documentElement.getAttribute('style'),
                        dangerToken: docCs.getPropertyValue('--color-danger').trim(),
                        btnBg: cs.backgroundColor
                    };
                })()
                """)
                print('Initial load info:', info)

                # Now switch to light theme
                info_light = await eval_js("""
                (function() {
                    document.documentElement.setAttribute('data-theme', 'light');
                    const el = document.querySelector('.semantic-matrix-table .btn-danger');
                    const cs = window.getComputedStyle(el);
                    const docCs = window.getComputedStyle(document.documentElement);
                    return {
                        themeAttr: document.documentElement.getAttribute('data-theme'),
                        dangerToken: docCs.getPropertyValue('--color-danger').trim(),
                        btnBg: cs.backgroundColor
                    };
                })()
                """)
                print('After light info:', info_light)

                # Now switch to dark theme
                info_dark = await eval_js("""
                (function() {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    const el = document.querySelector('.semantic-matrix-table .btn-danger');
                    const cs = window.getComputedStyle(el);
                    const docCs = window.getComputedStyle(document.documentElement);
                    return {
                        themeAttr: document.documentElement.getAttribute('data-theme'),
                        dangerToken: docCs.getPropertyValue('--color-danger').trim(),
                        btnBg: cs.backgroundColor
                    };
                })()
                """)
                print('After dark info:', info_dark)

    finally:
        proc.terminate()

asyncio.run(main())
