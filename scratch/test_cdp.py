import urllib.request
import json
import subprocess
import time
import os

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

# Let's see if we can run headless Edge to take full-page screenshot or use CDP
proc = subprocess.Popen([
    edge_path,
    '--headless',
    '--disable-gpu',
    '--remote-debugging-port=9222',
    'http://127.0.0.1:8000/design/'
])

time.sleep(2)

try:
    with urllib.request.urlopen('http://127.0.0.1:9222/json') as resp:
        tabs = json.loads(resp.read().decode('utf-8'))
        print('Tabs:', len(tabs))
        for t in tabs:
            print('Tab title:', t.get('title'), 'url:', t.get('url'))
finally:
    proc.terminate()
