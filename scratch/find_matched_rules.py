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

                await send('DOM.enable')
                await send('CSS.enable')

                # Switch to light mode first
                await send('Runtime.evaluate', {'expression': "document.documentElement.setAttribute('data-theme', 'light');"})

                doc = await send('DOM.getDocument')
                root_node_id = doc['root']['nodeId']
                
                # Query selector for .semantic-matrix-table .btn-danger
                node = await send('DOM.querySelector', {'nodeId': root_node_id, 'selector': '.semantic-matrix-table .btn-danger'})
                btn_node_id = node['nodeId']
                print('Found button nodeId:', btn_node_id)

                matched = await send('CSS.getMatchedStylesForNode', {'nodeId': btn_node_id})
                print('\n--- MATCHED RULES FOR .btn-danger ---')
                for rule_match in matched.get('matchedCSSRules', []):
                    rule = rule_match['rule']
                    sel = rule['selectorList']['text']
                    origin = rule.get('origin', '')
                    css_text = rule['style'].get('cssText', '')
                    # Print if background or color is in rule
                    if 'background' in css_text or 'color' in css_text:
                        print(f"Selector: {sel} (origin: {origin})")
                        for prop in rule['style']['cssProperties']:
                            if any(k in prop['name'] for k in ['background', 'color', 'border']):
                                print(f"    {prop['name']}: {prop['value']}")

    finally:
        proc.terminate()

asyncio.run(main())
