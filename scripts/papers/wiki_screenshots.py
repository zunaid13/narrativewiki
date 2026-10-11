"""Screenshots of the B5 Anne wiki at two cutoffs for the qualitative appendix
(docs/paper/appendix/m-qualitative.tex). $0, no LLM call.

Run:
  .venv/Scripts/python.exe -m mkdocs build -f dist/anne@v2/mkdocs.yml -d <tmp>/anne-site
  (cd <tmp>/anne-site && python -m http.server 8765 --bind 127.0.0.1) &
  .venv/Scripts/python.exe scripts/papers/wiki_screenshots.py
-> docs/paper/figures/qual/*.png. Drives headless Edge through the DevTools protocol, because
`msedge --screenshot` cannot scroll to a section.
"""
import asyncio, base64, json, subprocess, time, urllib.request, os

EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
OUT = os.environ.get('QUAL_OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'paper', 'figures', 'qual')
BASE = 'http://127.0.0.1:8765'
W = 1280

# (file name, url, element selector to start at, element selector to stop before)
SHOTS = [  # [34] the v2 build (anne@v2): one Anne Shirley entity, so the relationship block is hers
    ('home', '/', None, None),
    ('gilbert-v02-overview', '/v02/character/gilbert-blythe/', '#overview', '#appearance'),
    ('gilbert-v04-overview', '/v04/character/gilbert-blythe/', '#overview', '#appearance'),
    ('gilbert-v02-rel', '/v02/character/gilbert-blythe/', '#anne-shirley-the-relationship', '#diana-barry-the-relationship'),
    ('gilbert-v04-rel', '/v04/character/gilbert-blythe/', '#anne-shirley-the-relationship', '#diana-barry-the-relationship'),
]

async def main():
    import websockets
    prof = os.path.join(os.environ.get('TEMP', '/tmp'), 'nw-edge-profile')
    p = subprocess.Popen([EDGE, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                          '--remote-debugging-port=9333', f'--user-data-dir={prof}',
                          f'--window-size={W},1000', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                tabs = json.load(urllib.request.urlopen('http://127.0.0.1:9333/json'))
                break
            except OSError:
                time.sleep(0.2)
        ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        async with websockets.connect(ws_url, max_size=2**28) as ws:
            n = 0
            async def call(method, **params):
                nonlocal n
                n += 1
                await ws.send(json.dumps({'id': n, 'method': method, 'params': params}))
                while True:
                    m = json.loads(await ws.recv())
                    if m.get('id') == n:
                        if 'error' in m:
                            raise RuntimeError(m['error'])
                        return m['result']
            await call('Emulation.setDeviceMetricsOverride', width=W, height=1000, deviceScaleFactor=2, mobile=False)
            for name, path, start, stop in SHOTS:
                await call('Page.navigate', url=BASE + path)
                await asyncio.sleep(1.5)
                if start:
                    js = (f"(()=>{{const a=document.querySelector('{start}').getBoundingClientRect();"
                          f"const b=document.querySelector('{stop}').getBoundingClientRect();"
                          f"const y=window.scrollY;return [a.top+y-12,b.top+y-8]}})()")
                    y0, y1 = (await call('Runtime.evaluate', expression=js, returnByValue=True))['result']['value']
                    # content column only (left nav and right TOC cropped out)
                    clip = {'x': 280, 'y': y0, 'width': 720, 'height': y1 - y0, 'scale': 1}
                else:
                    clip = {'x': 0, 'y': 0, 'width': W, 'height': 560, 'scale': 1}
                r = await call('Page.captureScreenshot', format='png', clip=clip, captureBeyondViewport=True)
                with open(os.path.join(OUT, name + '.png'), 'wb') as f:
                    f.write(base64.b64decode(r['data']))
                print(name, round(clip['height']))
    finally:
        p.terminate()

asyncio.run(main())
