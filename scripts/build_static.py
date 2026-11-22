"""Build the GitHub Pages edition from the shared UI and JS strategies."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from queens.service import dispatch
out = ROOT / 'docs'
out.mkdir(exist_ok=True)
html = (ROOT / 'queens/web/index.html').read_text().replace('href="/"','href="./"').replace('href="/style.css"','href="./style.css"').replace('<script src="/app.js" defer>','<script type="module" src="./app.js">')
(out / 'index.html').write_text(html)
(out / 'style.css').write_text((ROOT / 'queens/web/style.css').read_text())
s = (ROOT / 'queens/web/app.js').read_text()
a,b=s.index('async function api('),s.index('function options()')
s=s[:a]+s[b:]
s="import {api} from './client.mjs';\n"+s
s=s.replace("const response = await fetch('/api/algorithms'); if (!response.ok) throw new Error('Could not load algorithms'); catalog = await response.json();",'catalog = '+json.dumps(dispatch('algorithms', {}))+';')
s=s.replace("navigator.sendBeacon('/api/generation/cancel', new Blob([JSON.stringify({job_id:generationJob})], {type:'application/json'}))", "api('generation/cancel', {job_id:generationJob}).catch(() => {})")
s=s.replace('Could not connect to the local server: ', 'Could not initialize the browser app: ')
(out/'app.js').write_text(s)
for file in (ROOT/'browser').glob('*.mjs'):(out/file.name).write_text(file.read_text())
(out/'.nojekyll').touch()
print('Built docs/ (no Python server required).')
