import ast
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / 'backend/catalog.json').read_text())
REPO = 'razaele0003/iz_time'
DB_PATH = Path(os.environ.get('EPISTEME_DB', ROOT / 'data/progress.sqlite3'))
LOCK = threading.Lock()
app = FastAPI(title='Project Episteme')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost','testserver'] + os.environ.get('EPISTEME_HOSTS','').split(','))

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS progress(id TEXT PRIMARY KEY, status TEXT NOT NULL, checks TEXT NOT NULL, sha TEXT NOT NULL, updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS syncs(id INTEGER PRIMARY KEY, sha TEXT, source TEXT, created_at TEXT);
      CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()

def github(path):
    headers = {'Accept':'application/vnd.github+json','User-Agent':'Project-Episteme','X-GitHub-Api-Version':'2022-11-28'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        url = f'https://api.github.com/repos/{REPO}' + (f'/{path}' if path else '')
        response = httpx.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, 'GitHub could not be read. Check connectivity, repository access or the API rate limit. Saved progress was kept.') from exc

def snapshot():
    repo = github('')
    commit = github('commits/' + quote(repo['default_branch'], safe=''))
    sha = commit['sha']
    tree = github(f'git/trees/{sha}?recursive=1')
    if tree.get('truncated'):
        raise HTTPException(502, 'GitHub returned an incomplete file tree. Saved progress was kept.')
    wanted = {p['path'] + '/' + name for p in CATALOG for name in ('main.py','README.md')}
    files = {}
    for entry in tree['tree']:
        if entry['path'] not in wanted or entry.get('mode') not in ('100644','100755'):
            continue
        if entry.get('size',0) > 100000:
            raise HTTPException(422, 'A milestone file exceeds the 100 KB analysis limit.')
        blob = github('git/blobs/' + entry['sha'])
        if blob.get('encoding') != 'base64':
            raise HTTPException(502, 'GitHub returned an unsupported file encoding.')
        try:
            files[entry['path']] = base64.b64decode(blob['content']).decode('utf-8-sig')
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, 'Milestone files must use UTF-8 text.') from exc
    return sha, files

def analyze(project, files):
    code = files.get(project['path'] + '/main.py', '')
    notes = files.get(project['path'] + '/README.md', '')
    tree = None
    try:
        tree = ast.parse(code) if code.strip() else None
    except (SyntaxError, ValueError, RecursionError):
        pass
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == project['function']), None) if tree else None
    body = [n for n in function.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))] if function else []
    implemented = bool(body) and not all(isinstance(n,(ast.Pass,ast.Raise)) or (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant)) for n in body)
    checks = [
      {'label':'main.py contains valid Python', 'passed':bool(tree)},
      {'label':f"{project['function']} has a non-stub body", 'passed':implemented},
      {'label':f"Function includes {project['node']}", 'passed':bool(function) and any(type(n).__name__ == project['node'] for n in ast.walk(function))},
      {'label':'README has at least 40 words of explanation', 'passed':len(notes.split()) >= 40}
    ]
    status = 'completed' if all(c['passed'] for c in checks) else 'in_progress' if code.strip() else 'not_started'
    return status, checks

def sync(source='manual', delivery=None):
    with LOCK:
        with database() as db:
            if delivery and db.execute('SELECT 1 FROM deliveries WHERE id=?',(delivery,)).fetchone():
                return {'duplicate':True}
        sha, files = snapshot()
        results = [(p, *analyze(p,files)) for p in CATALOG]
        timestamp = now()
        with database() as db:
            for p, status, checks in results:
                db.execute('INSERT OR REPLACE INTO progress VALUES(?,?,?,?,?)',(p['id'],status,json.dumps(checks),sha,timestamp))
            db.execute('INSERT INTO syncs(sha,source,created_at) VALUES(?,?,?)',(sha,source,timestamp))
            if delivery:
                db.execute('INSERT INTO deliveries VALUES(?,?)',(delivery,timestamp))
        return {'sha':sha,'synced_at':timestamp}

@app.get('/api/progress')
def progress():
    with database() as db:
        records = {r['id']:dict(r) for r in db.execute('SELECT * FROM progress')}
        activity = [dict(r) for r in db.execute('SELECT * FROM syncs ORDER BY id DESC LIMIT 8')]
    projects = []
    for p in CATALOG:
        saved = records.get(p['id'])
        status, checks = analyze(p,{})
        projects.append({**p,'status':saved['status'] if saved else status,'checks':json.loads(saved['checks']) if saved else checks})
    completed = sum(p['status']=='completed' for p in projects)
    return {'repository':REPO,'projects':projects,'completed':completed,'total':len(projects),'percent':round(completed/len(projects)*100) if projects else 0,'activity':activity,'last_sync':activity[0] if activity else None,'webhook_configured':bool(os.environ.get('GITHUB_WEBHOOK_SECRET'))}

@app.post('/api/sync')
def manual_sync(request: Request):
    # Browser requests need an explicit header; cross-origin preflights are not allowed.
    if request.headers.get('x-episteme-client') != 'dashboard':
        raise HTTPException(403,'Use the dashboard to sync.')
    # Never expose this unauthenticated control through a public reverse proxy.
    if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
        raise HTTPException(403,'Manual sync is local only.')
    return sync()

@app.post('/api/webhooks/github')
async def webhook(request: Request):
    secret = os.environ.get('GITHUB_WEBHOOK_SECRET')
    if not secret:
        raise HTTPException(503,'Webhook secret has not been configured.')
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks)>2_000_000:
            raise HTTPException(413,'Webhook exceeds 2 MB.')
    body = bytes(chunks)
    expected = 'sha256=' + hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,request.headers.get('x-hub-signature-256','')):
        raise HTTPException(403,'Invalid webhook signature.')
    try:
        payload = json.loads(body)
        if not isinstance(payload,dict):
            raise ValueError()
    except ValueError:
        raise HTTPException(400,'Invalid JSON payload.')
    repository = payload.get('repository')
    if not isinstance(repository,dict) or repository.get('full_name','').lower()!=REPO.lower():
        raise HTTPException(403,'Unexpected repository.')
    event = request.headers.get('x-github-event')
    if event == 'ping':
        return {'pong':True}
    if event != 'push' or payload.get('deleted') or payload.get('ref')!='refs/heads/' + str(repository.get('default_branch')):
        return {'ignored':True}
    delivery = request.headers.get('x-github-delivery','')
    if not re.fullmatch(r'[A-Za-z0-9-]{1,100}',delivery):
        raise HTTPException(400,'Missing or invalid delivery ID.')
    # Synchronous acknowledgement: failures remain retryable through GitHub redelivery.
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(sync,'webhook',delivery)

if (ROOT / 'dist/assets').exists():
    app.mount('/assets',StaticFiles(directory=ROOT / 'dist/assets'),name='assets')

@app.get('/')
def index():
    if not (ROOT / 'dist/index.html').exists():
        raise HTTPException(503,'Build the frontend with npm run build first.')
    return FileResponse(ROOT / 'dist/index.html')
