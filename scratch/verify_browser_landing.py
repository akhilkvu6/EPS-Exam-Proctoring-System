import asyncio
import aiohttp
import json
import subprocess
import time
import base64

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

async def main():
    user_data_dir = r'c:\Users\akhil\OneDrive\Desktop\EPS-Exam-Proctoring-System\scratch\edge_landing_profile'
    proc = subprocess.Popen([
        edge_path,
        '--headless',
        '--disable-gpu',
        '--remote-debugging-port=9222',
        f'--user-data-dir={user_data_dir}',
        '--window-size=1440,1024',
        'http://127.0.0.1:8000/'
    ])
    await asyncio.sleep(2)
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

                async def eval_js(js):
                    res = await send('Runtime.evaluate', {'expression': js, 'returnByValue': True})
                    return res.get('result', {}).get('value')

                await send('DOM.enable')
                await send('Page.enable')

                # 1. Check Responsive Viewports & Horizontal Overflow
                viewports = [
                    (1440, 900, 'Desktop 1440px'),
                    (1280, 800, 'Laptop 1280px'),
                    (1024, 768, 'Tablet 1024px'),
                    (768, 1024, 'Tablet 768px'),
                    (390, 844, 'Mobile 390px'),
                    (360, 740, 'Mobile 360px'),
                ]

                print('=== RESPONSIVE VIEWPORT & OVERFLOW CHECKS ===')
                for w, h, label in viewports:
                    await send('Emulation.setDeviceMetricsOverride', {
                        'width': w,
                        'height': h,
                        'deviceScaleFactor': 1,
                        'mobile': (w <= 768)
                    })
                    await asyncio.sleep(0.3)
                    overflow = await eval_js("document.documentElement.scrollWidth > window.innerWidth")
                    scroll_w = await eval_js("document.documentElement.scrollWidth")
                    inner_w = await eval_js("window.innerWidth")
                    print(f"[{label}] innerWidth={inner_w}, scrollWidth={scroll_w} -> Overflow: {overflow} ({'PASS' if not overflow else 'FAIL'})")

                # Reset to 1280x900 for capturing screenshots
                await send('Emulation.setDeviceMetricsOverride', {
                    'width': 1280,
                    'height': 900,
                    'deviceScaleFactor': 1,
                    'mobile': False
                })
                await asyncio.sleep(0.5)

                # 2. Check Light Mode Hero & Proctoring Screenshots
                await eval_js("document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('eps-theme', 'light');")
                await asyncio.sleep(0.3)
                shot_light_hero = await send('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot_light_hero:
                    with open(r'scratch\landing_light_hero.png', 'wb') as f:
                        f.write(base64.b64decode(shot_light_hero['data']))
                    print('Captured scratch/landing_light_hero.png')

                # Scroll to Proctoring / Student sections
                await eval_js("document.getElementById('proctoring').scrollIntoView();")
                await asyncio.sleep(0.5)
                shot_light_proc = await send('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot_light_proc:
                    with open(r'scratch\landing_light_proctoring.png', 'wb') as f:
                        f.write(base64.b64decode(shot_light_proc['data']))
                    print('Captured scratch/landing_light_proctoring.png')

                # 3. Check Dark Mode Hero & Proctoring Screenshots
                await eval_js("document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('eps-theme', 'dark');")
                await eval_js("window.scrollTo(0, 0);")
                await asyncio.sleep(0.5)
                shot_dark_hero = await send('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot_dark_hero:
                    with open(r'scratch\landing_dark_hero.png', 'wb') as f:
                        f.write(base64.b64decode(shot_dark_hero['data']))
                    print('Captured scratch/landing_dark_hero.png')

                await eval_js("document.getElementById('proctoring').scrollIntoView();")
                await asyncio.sleep(0.5)
                shot_dark_proc = await send('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot_dark_proc:
                    with open(r'scratch\landing_dark_proctoring.png', 'wb') as f:
                        f.write(base64.b64decode(shot_dark_proc['data']))
                    print('Captured scratch/landing_dark_proctoring.png')

                # 4. Check Mobile Drawer Interaction (390px)
                await send('Emulation.setDeviceMetricsOverride', {
                    'width': 390,
                    'height': 844,
                    'deviceScaleFactor': 1,
                    'mobile': True
                })
                await eval_js("document.getElementById('lp-mobile-menu-toggle').click();")
                await asyncio.sleep(0.3)
                is_drawer_open = await eval_js("document.getElementById('lp-mobile-drawer').classList.contains('is-open')")
                print(f"Mobile Drawer Opened on click: {is_drawer_open}")
                shot_mobile = await send('Page.captureScreenshot', {'format': 'png'})
                if 'data' in shot_mobile:
                    with open(r'scratch\landing_mobile_drawer.png', 'wb') as f:
                        f.write(base64.b64decode(shot_mobile['data']))
                    print('Captured scratch/landing_mobile_drawer.png')

    finally:
        proc.terminate()

asyncio.run(main())
