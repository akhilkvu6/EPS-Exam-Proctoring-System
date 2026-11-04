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

                async def capture_element(selector, output_path):
                    doc = await send('DOM.getDocument')
                    root_id = doc['root']['nodeId']
                    node = await send('DOM.querySelector', {'nodeId': root_id, 'selector': selector})
                    node_id = node.get('nodeId')
                    if not node_id:
                        print(f"Could not find {selector}")
                        return
                    box = await send('DOM.getBoxModel', {'nodeId': node_id})
                    model = box.get('model', {})
                    border = model.get('border', [])
                    if len(border) >= 8:
                        x = min(border[0], border[2], border[4], border[6])
                        y = min(border[1], border[3], border[5], border[7])
                        w = max(border[0], border[2], border[4], border[6]) - x
                        h = max(border[1], border[3], border[5], border[7]) - y
                        # Scroll into view first
                        await send('DOM.scrollIntoViewIfNeeded', {'nodeId': node_id})
                        await asyncio.sleep(0.3)
                        # Re-fetch box model after scroll
                        box2 = await send('DOM.getBoxModel', {'nodeId': node_id})
                        border2 = box2.get('model', {}).get('border', [])
                        x2 = min(border2[0], border2[2], border2[4], border2[6])
                        y2 = min(border2[1], border2[3], border2[5], border2[7])
                        w2 = max(border2[0], border2[2], border2[4], border2[6]) - x2
                        h2 = max(border2[1], border2[3], border2[5], border2[7]) - y2
                        shot = await send('Page.captureScreenshot', {
                            'format': 'png',
                            'clip': {'x': max(0, x2), 'y': max(0, y2), 'width': max(10, w2), 'height': max(10, h2), 'scale': 1}
                        })
                        if 'data' in shot:
                            with open(output_path, 'wb') as f:
                                f.write(base64.b64decode(shot['data']))
                            print(f"Saved {output_path}")

                await send('DOM.enable')
                await send('CSS.enable')

                # 1. Dark Mode captures
                await send('Runtime.evaluate', {'expression': "localStorage.setItem('eps-theme', 'dark');"})
                await reload_page()
                await capture_element('.semantic-matrix-table', r'scratch\dark_sec2_matrix.png')
                await capture_element('#buttons .card:first-of-type', r'scratch\dark_sec4_buttons.png')

                # 2. Light Mode captures
                await send('Runtime.evaluate', {'expression': "localStorage.setItem('eps-theme', 'light');"})
                await reload_page()
                await capture_element('.semantic-matrix-table', r'scratch\light_sec2_matrix.png')
                await capture_element('#buttons .card:first-of-type', r'scratch\light_sec4_buttons.png')

    finally:
        proc.terminate()

asyncio.run(main())
