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
                async def eval_js(js):
                    nonlocal cid
                    curr_id = cid
                    cid += 1
                    await ws.send_json({'id': curr_id, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == curr_id:
                            return msg.get('result', {}).get('result', {}).get('value')

                async def reload_page():
                    nonlocal cid
                    curr_id = cid
                    cid += 1
                    await ws.send_json({'id': curr_id, 'method': 'Page.reload', 'params': {}})
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == curr_id:
                            break
                    await asyncio.sleep(1.5)

                check_all_btn_js = '''
                (function() {
                    const list = [
                        // Section 2 Operational Matrix Buttons
                        { area: 'Sec2 Matrix', name: 'Danger (Lock Attempt)', sel: '.semantic-matrix-table .btn-danger' },
                        { area: 'Sec2 Matrix', name: 'Warning (Issue Warning)', sel: '.semantic-matrix-table .btn-warning' },
                        { area: 'Sec2 Matrix', name: 'Success (Approve Pass)', sel: '.semantic-matrix-table .btn-success' },
                        { area: 'Sec2 Matrix', name: 'Primary (Instructions)', sel: '.semantic-matrix-table .btn-primary' },
                        { area: 'Sec2 Matrix', name: 'Secondary (Cancel Action)', sel: '.semantic-matrix-table .btn-secondary' },

                        // Section 4 Standard Buttons
                        { area: 'Sec4 Showcase', name: 'Primary Blue (Save Changes)', sel: '#buttons .btn-primary' },
                        { area: 'Sec4 Showcase', name: 'Success Green (Approve)', sel: '#buttons .btn-success' },
                        { area: 'Sec4 Showcase', name: 'Danger Red (Delete)', sel: '#buttons .btn-danger' },
                        { area: 'Sec4 Showcase', name: 'Warning Orange (Flag)', sel: '#buttons .btn-warning' },
                        { area: 'Sec4 Showcase', name: 'Secondary Grey (Cancel)', sel: '#buttons .btn-secondary' },
                    ];

                    return list.map(item => {
                        const el = document.querySelector(item.sel);
                        if (!el) return { ...item, error: 'Element NOT found' };
                        const cs = window.getComputedStyle(el);
                        return {
                            area: item.area,
                            name: item.name,
                            text: el.innerText.trim().replace(/\\s+/g, ' '),
                            bg: cs.backgroundColor,
                            color: cs.color,
                            border: cs.borderColor,
                            height: cs.height,
                            padding: cs.padding
                        };
                    });
                })()
                '''

                # 1. LIGHT MODE TEST
                await eval_js("localStorage.setItem('eps-theme', 'light');")
                await reload_page()
                res_light = await eval_js(check_all_btn_js)

                print('======================================================================')
                print('LIGHT THEME BUTTON COMPUTED STYLES (theme = light)')
                print('======================================================================')
                for b in res_light:
                    print(f"[{b['area']}] {b['name']}:")
                    print(f"   Text: '{b.get('text')}'")
                    print(f"   Background: {b.get('bg')}")
                    print(f"   Color:      {b.get('color')}")
                    print(f"   Border:     {b.get('border')}")
                    print(f"   Height:     {b.get('height')}")

                # 2. DARK MODE TEST
                await eval_js("localStorage.setItem('eps-theme', 'dark');")
                await reload_page()
                res_dark = await eval_js(check_all_btn_js)

                print('\n======================================================================')
                print('DARK THEME BUTTON COMPUTED STYLES (theme = dark)')
                print('======================================================================')
                for b in res_dark:
                    print(f"[{b['area']}] {b['name']}:")
                    print(f"   Text: '{b.get('text')}'")
                    print(f"   Background: {b.get('bg')}")
                    print(f"   Color:      {b.get('color')}")
                    print(f"   Border:     {b.get('border')}")
                    print(f"   Height:     {b.get('height')}")

    finally:
        proc.terminate()

asyncio.run(main())
