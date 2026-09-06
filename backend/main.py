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
from urllib.parse import quote, urlparse
from pydantic import BaseModel

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
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS bound_progress(binding TEXT, id TEXT, status TEXT, checks TEXT, sha TEXT, updated_at TEXT, PRIMARY KEY(binding,id));
      CREATE TABLE IF NOT EXISTS bound_syncs(id INTEGER PRIMARY KEY, binding TEXT, sha TEXT, source TEXT, created_at TEXT);
      CREATE TABLE IF NOT EXISTS bound_deliveries(binding TEXT, id TEXT, created_at TEXT, PRIMARY KEY(binding,id));
    ''')
    try:
        with db:
            if not db.execute("SELECT 1 FROM settings WHERE key='binding'").fetchone():
                initial = {'repository':REPO,'root':'projects'}
                key = binding_key(initial)
                db.execute("INSERT INTO settings VALUES('binding',?)", (json.dumps(initial),))
                db.execute('INSERT OR IGNORE INTO bound_progress SELECT ?,id,status,checks,sha,updated_at FROM progress',(key,))
                db.execute('INSERT INTO bound_syncs(binding,sha,source,created_at) SELECT ?,sha,source,created_at FROM syncs',(key,))
                db.execute('INSERT OR IGNORE INTO bound_deliveries SELECT ?,id,created_at FROM deliveries',(key,))
            yield db
    finally:
        db.close()

def github(path, repository=None):
    repository = repository or binding()["repository"]
    headers = {'Accept':'application/vnd.github+json','User-Agent':'Project-Episteme','X-GitHub-Api-Version':'2022-11-28'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        url = f'https://api.github.com/repos/{repository}' + (f'/{path}' if path else '')
        response = httpx.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        response = exc.response
        if response.status_code in (403,429) and response.headers.get('x-ratelimit-remaining') == '0':
            message = 'GitHub API rate limit reached. Try again later or configure a read-only GITHUB_TOKEN in the backend.'
        elif response.status_code == 404:
            message = 'Repository or branch not found. Check owner/repository; private repositories require backend token access.'
        else:
            message = f'GitHub returned HTTP {response.status_code}. Try again; saved progress was kept.'
        raise HTTPException(502,message) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, 'GitHub could not be read. Check connectivity, repository access or the API rate limit. Saved progress was kept.') from exc

def snapshot(connection=None):
    connection = connection or binding()
    read = lambda path: github(path, connection["repository"])
    repo = read('')
    commit = read('commits/' + quote(repo['default_branch'], safe=''))
    sha = commit['sha']
    tree = read(f'git/trees/{sha}?recursive=1')
    if tree.get('truncated'):
        raise HTTPException(502, 'GitHub returned an incomplete file tree. Saved progress was kept.')
    folders = {p['path'] for p in catalog(connection)}
    actual_folders = {e['path'] for e in tree['tree'] if e.get('type')=='tree'}
    if not folders.intersection(actual_folders):
        names = {p['path'].split('/')[-1] for p in CATALOG}
        alternatives = sorted({p.rsplit('/',1)[0] if '/' in p else '' for p in actual_folders if p.split('/')[-1] in names})
        if alternatives:
            suggested = ', '.join(p or '(repository root)' for p in alternatives[:3])
            raise HTTPException(422, f'Project folders were found under {suggested}. Update Projects parent folder. Saved progress was kept.')
    wanted = {p['path'] + '/' + name for p in catalog(connection) for name in ('main.py','README.md')}
    files = {}
    for entry in tree['tree']:
        if entry['path'] not in wanted or entry.get('mode') not in ('100644','100755'):
            continue
        if entry.get('size',0) > 100000:
            raise HTTPException(422, 'A milestone file exceeds the 100 KB analysis limit.')
        blob = read('git/blobs/' + entry['sha'])
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

def binding_key(connection):
    return connection['repository'].lower() + ':' + connection['root']


def binding():
    with database() as db:
        return json.loads(db.execute("SELECT value FROM settings WHERE key='binding'").fetchone()[0])


def catalog(connection):
    root = connection['root']
    return [{**p,'path':'/'.join(filter(None,[root,p['path'].split('/')[-1]]))} for p in CATALOG]


class ConnectionInput(BaseModel):
    repository: str
    root: str = 'projects'


def normalize_connection(value):
    repo = value.repository.strip().rstrip('/')
    if repo.startswith('https://'):
        url = urlparse(repo)
        if url.netloc.lower() != 'github.com' or url.query or url.fragment:
            raise HTTPException(422,'Enter a github.com repository URL or owner/repository.')
        repo = url.path.strip('/')
    if repo.endswith('.git'):
        repo = repo[:-4]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}',repo) or repo.split('/')[-1] in ('.','..'):
        raise HTTPException(422,'Enter a repository as owner/repository, for example razaele0003/iz_time.')
    root = value.root.strip().strip('/')
    if len(root)>200 or (root and any(not re.fullmatch(r'[A-Za-z0-9_. -]+',part) or part in ('.','..') for part in root.split('/'))):
        raise HTTPException(422,'Use a relative folder such as projects or learning/python. Leave blank for the repository root.')
    return {'repository':repo.lower(),'root':root}


def persist_snapshot(db, connection, sha, files, source, delivery=None):
    key = binding_key(connection)
    timestamp = now()
    for p in catalog(connection):
        status, checks = analyze(p,files)
        db.execute('INSERT OR REPLACE INTO bound_progress VALUES(?,?,?,?,?,?)',(key,p['id'],status,json.dumps(checks),sha,timestamp))
    db.execute('INSERT INTO bound_syncs(binding,sha,source,created_at) VALUES(?,?,?,?)',(key,sha,source,timestamp))
    if delivery:
        db.execute('INSERT INTO bound_deliveries VALUES(?,?,?)',(key,delivery,timestamp))
    return {'sha':sha,'synced_at':timestamp}


def sync(source='manual', delivery=None, expected_repository=None):
    with LOCK:
        connection = binding()
        if expected_repository and connection['repository'].lower()!=expected_repository.lower():
            raise HTTPException(409,'Repository binding changed; this event was not applied.')
        key = binding_key(connection)
        with database() as db:
            if delivery and db.execute('SELECT 1 FROM bound_deliveries WHERE binding=? AND id=?',(key,delivery)).fetchone():
                return {'duplicate':True}
        sha, files = snapshot(connection)
        with database() as db:
            return persist_snapshot(db, connection, sha, files, source, delivery)


def require_local(request):
    if request.headers.get('x-episteme-client') != 'dashboard':
        raise HTTPException(403,'Use the dashboard for this action.')
    if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
        raise HTTPException(403,'This action is local only.')


@app.put('/api/connection')
def connect(value: ConnectionInput, request: Request):
    require_local(request)
    connection = normalize_connection(value)
    with LOCK:
        # Verify access and analyze before committing the new selection.
        sha, files = snapshot(connection)
        with database() as db:
            result = persist_snapshot(db, connection, sha, files, 'connection')
            db.execute("UPDATE settings SET value=? WHERE key='binding'",(json.dumps(connection),))
    return {**connection,**result}


@app.get('/api/progress')
def progress():
    with database() as db:
        connection = json.loads(db.execute("SELECT value FROM settings WHERE key='binding'").fetchone()[0])
        key = binding_key(connection)
        records = {r['id']:dict(r) for r in db.execute('SELECT * FROM bound_progress WHERE binding=?',(key,))}
        activity = [dict(r) for r in db.execute('SELECT * FROM bound_syncs WHERE binding=? ORDER BY id DESC LIMIT 8',(key,))]
    projects = []
    for p in catalog(connection):
        saved = records.get(p['id'])
        status, checks = analyze(p,{})
        projects.append({**p,'status':saved['status'] if saved else status,'checks':json.loads(saved['checks']) if saved else checks})
    completed = sum(p['status']=='completed' for p in projects)
    return {**connection,'projects':projects,'completed':completed,'total':len(projects),'percent':round(completed/len(projects)*100) if projects else 0,'activity':activity,'last_sync':activity[0] if activity else None,'webhook_configured':bool(os.environ.get('GITHUB_WEBHOOK_SECRET'))}

@app.post('/api/sync')
def manual_sync(request: Request):
    require_local(request)
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
    if not isinstance(repository,dict) or str(repository.get('full_name','')).lower()!=binding()['repository'].lower():
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
    return await run_in_threadpool(sync,'webhook',delivery,repository['full_name'])

if (ROOT / 'dist/assets').exists():
    app.mount('/assets',StaticFiles(directory=ROOT / 'dist/assets'),name='assets')

@app.get('/')
def index():
    if not (ROOT / 'dist/index.html').exists():
        raise HTTPException(503,'Build the frontend with npm run build first.')
    return FileResponse(ROOT / 'dist/index.html')

