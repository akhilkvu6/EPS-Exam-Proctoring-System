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
                    res = await ws.receive_json()
                    return res.get('result', {}).get('result', {}).get('value')

                theme_now = await eval_js("document.documentElement.getAttribute('data-theme')")
                print('Theme on page load:', theme_now)
                color_now = await eval_js("window.getComputedStyle(document.documentElement).getPropertyValue('--color-danger').trim()")
                print('--color-danger on page load:', color_now)

                # Set to light
                await eval_js("document.documentElement.setAttribute('data-theme', 'light')")
                theme_light = await eval_js("document.documentElement.getAttribute('data-theme')")
                color_light = await eval_js("window.getComputedStyle(document.documentElement).getPropertyValue('--color-danger').trim()")
                print('After setting light -> theme:', theme_light, 'danger:', color_light)

                # Set to dark
                await eval_js("document.documentElement.setAttribute('data-theme', 'dark')")
                theme_dark = await eval_js("document.documentElement.getAttribute('data-theme')")
                color_dark = await eval_js("window.getComputedStyle(document.documentElement).getPropertyValue('--color-danger').trim()")
                print('After setting dark -> theme:', theme_dark, 'danger:', color_dark)

                # Check body data-theme?
                body_theme = await eval_js("document.body.getAttribute('data-theme')")
                print('Body data-theme:', body_theme)

    finally:
        proc.terminate()

asyncio.run(main())
