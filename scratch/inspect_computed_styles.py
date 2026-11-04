import asyncio
import aiohttp
import json
import subprocess
import time
import base64

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

async def main():
    # Start Edge with remote debugging
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
            
            design_tab = next(t for t in tabs if 'http://127.0.0.1:8000/design/' in t.get('url', ''))
            ws_url = design_tab['webSocketDebuggerUrl']
            print('Connecting to:', ws_url)

            async with session.ws_connect(ws_url) as ws:
                msg_id = 1
                async def send_cmd(method, params=None):
                    nonlocal msg_id
                    mid = msg_id
                    msg_id += 1
                    await ws.send_json({'id': mid, 'method': method, 'params': params or {}})
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == mid:
                            return msg.get('result', {})

                # 1. Enable Runtime
                await send_cmd('Runtime.enable')

                # JS to check computed styles
                check_js = '''
                (function() {
                    const results = {};
                    const targets = [
                        { name: 'Sec2 Danger (Lock Attempt)', sel: '.semantic-matrix-table .btn-danger' },
                        { name: 'Sec2 Warning (Issue Warning)', sel: '.semantic-matrix-table .btn-warning' },
                        { name: 'Sec2 Success (Approve Pass)', sel: '.semantic-matrix-table .btn-success' },
                        { name: 'Sec2 Primary (Instructions)', sel: '.semantic-matrix-table .btn-primary' },
                        { name: 'Sec2 Secondary (Cancel)', sel: '.semantic-matrix-table .btn-secondary' },
                        { name: 'Sec4 Primary (Save Changes)', sel: '#buttons .btn-primary' },
                        { name: 'Sec4 Success (Approve)', sel: '#buttons .btn-success' },
                        { name: 'Sec4 Danger (Delete)', sel: '#buttons .btn-danger' },
                        { name: 'Sec4 Warning (Flag)', sel: '#buttons .btn-warning' },
                        { name: 'Sec4 Secondary (Cancel)', sel: '#buttons .btn-secondary' },
                    ];
                    
                    targets.forEach(t => {
                        const el = document.querySelector(t.sel);
                        if (!el) {
                            results[t.name] = 'NOT FOUND';
                        } else {
                            const cs = window.getComputedStyle(el);
                            results[t.name] = {
                                bg: cs.backgroundColor,
                                color: cs.color,
                                border: cs.borderColor,
                                text: el.innerText.trim().replace(/\\s+/g, ' ')
                            };
                        }
                    });
                    return results;
                })()
                '''

                # Evaluate in Light Mode
                await send_cmd('Runtime.evaluate', {'expression': "document.documentElement.setAttribute('data-theme', 'light');"})
                res_light = await send_cmd('Runtime.evaluate', {'expression': check_js, 'returnByValue': True})
                print('\n=== COMPUTED STYLES IN LIGHT THEME ===')
                print(json.dumps(res_light.get('result', {}).get('value', {}), indent=2))

                # Evaluate in Dark Mode
                await send_cmd('Runtime.evaluate', {'expression': "document.documentElement.setAttribute('data-theme', 'dark');"})
                res_dark = await send_cmd('Runtime.evaluate', {'expression': check_js, 'returnByValue': True})
                print('\n=== COMPUTED STYLES IN DARK THEME ===')
                print(json.dumps(res_dark.get('result', {}).get('value', {}), indent=2))

                # Take screenshots of Section 2 and Section 4 in Dark Mode
                # First let's scroll to Section 2 and capture
                await send_cmd('Runtime.evaluate', {'expression': "document.getElementById('colors').scrollIntoView();"})
                await asyncio.sleep(0.5)
                shot1 = await send_cmd('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot1:
                    with open(r'scratch\sec2_dark.png', 'wb') as sf:
                        sf.write(base64.b64decode(shot1['data']))
                    print('Saved scratch/sec2_dark.png')

                # Scroll to Section 4 and capture
                await send_cmd('Runtime.evaluate', {'expression': "document.getElementById('buttons').scrollIntoView();"})
                await asyncio.sleep(0.5)
                shot2 = await send_cmd('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot2:
                    with open(r'scratch\sec4_dark.png', 'wb') as sf:
                        sf.write(base64.b64decode(shot2['data']))
                    print('Saved scratch/sec4_dark.png')

                # Now switch to Light Theme and capture Section 2 and Section 4
                await send_cmd('Runtime.evaluate', {'expression': "document.documentElement.setAttribute('data-theme', 'light');"})
                await send_cmd('Runtime.evaluate', {'expression': "document.getElementById('colors').scrollIntoView();"})
                await asyncio.sleep(0.5)
                shot3 = await send_cmd('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot3:
                    with open(r'scratch\sec2_light.png', 'wb') as sf:
                        sf.write(base64.b64decode(shot3['data']))
                    print('Saved scratch/sec2_light.png')

                await send_cmd('Runtime.evaluate', {'expression': "document.getElementById('buttons').scrollIntoView();"})
                await asyncio.sleep(0.5)
                shot4 = await send_cmd('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot4:
                    with open(r'scratch\sec4_light.png', 'wb') as sf:
                        sf.write(base64.b64decode(shot4['data']))
                    print('Saved scratch/sec4_light.png')

    finally:
        proc.terminate()

asyncio.run(main())
