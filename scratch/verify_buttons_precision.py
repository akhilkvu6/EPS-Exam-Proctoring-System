import asyncio
import aiohttp
import json
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
                msg_counter = 1
                async def eval_js(js):
                    nonlocal msg_counter
                    cid = msg_counter
                    msg_counter += 1
                    await ws.send_json({'id': cid, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == cid:
                            return msg.get('result', {}).get('result', {}).get('value')

                check_script = '''
                (function() {
                    const buttons = [
                        { label: 'Sec2 Lock Attempt (Danger Red)', sel: '.semantic-matrix-table .btn-danger' },
                        { label: 'Sec2 Issue Warning (Warning Orange)', sel: '.semantic-matrix-table .btn-warning' },
                        { label: 'Sec2 Approve Pass (Success Green)', sel: '.semantic-matrix-table .btn-success' },
                        { label: 'Sec2 Instructions (Primary Blue)', sel: '.semantic-matrix-table .btn-primary' },
                        { label: 'Sec2 Cancel (Secondary Grey)', sel: '.semantic-matrix-table .btn-secondary' },
                        { label: 'Sec4 Primary Blue', sel: '#buttons .btn-primary' },
                        { label: 'Sec4 Success Green', sel: '#buttons .btn-success' },
                        { label: 'Sec4 Danger Red', sel: '#buttons .btn-danger' },
                        { label: 'Sec4 Warning Orange', sel: '#buttons .btn-warning' },
                        { label: 'Sec4 Secondary Grey', sel: '#buttons .btn-secondary' },
                    ];
                    return buttons.map(b => {
                        const el = document.querySelector(b.sel);
                        if (!el) return { label: b.label, error: 'not found' };
                        const cs = window.getComputedStyle(el);
                        return {
                            label: b.label,
                            bg: cs.backgroundColor,
                            color: cs.color,
                            borderColor: cs.borderColor,
                            height: cs.height,
                            padding: cs.padding,
                            transform: cs.transform
                        };
                    });
                })()
                '''

                # 1. LIGHT THEME
                await eval_js("document.documentElement.setAttribute('data-theme', 'light');")
                light_res = await eval_js(check_script)
                print('=== LIGHT THEME COMPUTED STYLES ===')
                for item in light_res:
                    print(f"  {item['label']}:")
                    print(f"    bg: {item.get('bg')}, color: {item.get('color')}, border: {item.get('borderColor')}")

                # 2. DARK THEME
                await eval_js("document.documentElement.setAttribute('data-theme', 'dark');")
                dark_res = await eval_js(check_script)
                print('\n=== DARK THEME COMPUTED STYLES ===')
                for item in dark_res:
                    print(f"  {item['label']}:")
                    print(f"    bg: {item.get('bg')}, color: {item.get('color')}, border: {item.get('borderColor')}")

    finally:
        proc.terminate()

asyncio.run(main())
