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

                await eval_js("document.documentElement.setAttribute('data-theme', 'light');")
                ancestors = await eval_js("""
                (function() {
                    let el = document.querySelector('.semantic-matrix-table .btn-danger');
                    let trace = [];
                    while (el) {
                        const cs = window.getComputedStyle(el);
                        trace.push({
                            tag: el.tagName,
                            id: el.id,
                            cls: el.className,
                            danger: cs.getPropertyValue('--color-danger').trim(),
                            bg: cs.backgroundColor
                        });
                        el = el.parentElement;
                    }
                    return trace;
                })()
                """)
                import pprint
                pprint.pprint(ancestors)

    finally:
        proc.terminate()

asyncio.run(main())
