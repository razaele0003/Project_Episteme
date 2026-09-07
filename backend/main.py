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
from backend import github_auth

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / 'backend/catalog.json').read_text())
COURSE = json.loads((ROOT / 'backend/course_curriculum.json').read_text())
REPO = 'razaele0003/iz_time'
DB_PATH = Path(os.environ.get('EPISTEME_DB', ROOT / 'data/progress.sqlite3'))
LOCK = threading.Lock()
app = FastAPI(title='Project Episteme')
app.include_router(github_auth.router)
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
      CREATE TABLE IF NOT EXISTS bound_catalog(binding TEXT PRIMARY KEY, catalog TEXT NOT NULL, sha TEXT NOT NULL, updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS bound_content(binding TEXT, id TEXT, source_path TEXT, source TEXT, readme_path TEXT, readme TEXT, expected_output TEXT, PRIMARY KEY(binding,id));
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
    token = os.environ.get('GITHUB_TOKEN') or github_auth.token()
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
    entries = {entry['path']:entry for entry in tree['tree'] if entry.get('mode') in ('100644','100755')}
    files = {}

    def read_file(path, limit=100000):
        entry = entries.get(path)
        if not entry:
            return
        if entry.get('size',0) > limit:
            raise HTTPException(422, f'{path} exceeds the analysis size limit.')
        blob = read('git/blobs/' + entry['sha'])
        if blob.get('encoding') != 'base64':
            raise HTTPException(502, 'GitHub returned an unsupported file encoding.')
        try:
            files[path] = base64.b64decode(blob['content']).decode('utf-8-sig')
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, f'{path} must use UTF-8 text.') from exc

    for path in ('.episteme/curriculum.json','.episteme/projects.json','README.md'):
        read_file(path, 500000)

    projects = catalog(connection, files)
    folders = {p['path'] for p in projects if p.get('path')}
    actual_folders = {e['path'] for e in tree['tree'] if e.get('type')=='tree'}
    if not files.get('.episteme/curriculum.json') and folders and not folders.intersection(actual_folders):
        names = {p['path'].split('/')[-1] for p in CATALOG}
        alternatives = sorted({p.rsplit('/',1)[0] if '/' in p else '' for p in actual_folders if p.split('/')[-1] in names})
        if alternatives:
            suggested = ', '.join(p or '(repository root)' for p in alternatives[:3])
            raise HTTPException(422, f'Project folders were found under {suggested}. Update Projects parent folder. Saved progress was kept.')
    wanted = {path for p in projects for path in (p.get('source_path'),p.get('readme_path')) if path and path != 'README.md'}
    for path in wanted:
        if safe_repo_path(path):
            read_file(path)
    return sha, files


def safe_repo_path(path):
    return bool(path and len(path)<=300 and not path.startswith('/') and all(part not in ('','.','..') for part in path.split('/')))


def readme_section(readme, ordinal):
    if not readme or not ordinal:
        return ''
    match = re.search(rf'(?ms)^###\s+{ordinal}\.\s+.*?(?=^###\s+\d+\.|^---\s*$|\Z)',readme)
    return match.group(0).strip() if match else ''


def course_project(course_row, mapping=None, ordinal=None):
    mapping = mapping or {}
    paths = mapping.get('source_paths') or []
    source_path = next((str(path) for path in paths if safe_repo_path(str(path)) and not str(path).lower().endswith('.md')), '')
    readme_path = str(mapping.get('readme_path') or '')
    if not readme_path:
        readme_path = next((str(path) for path in paths if safe_repo_path(str(path)) and str(path).lower().endswith('.md')), '')
    if not safe_repo_path(readme_path):
        readme_path = ''
    project_id = str(course_row['id'])
    phase = course_row.get('phase')
    return {
        'id':project_id,'alias':project_id,'title':str(course_row['title']),
        'ordinal':ordinal or int(course_row.get('ordinal') or 0),'historical':False,
        'phase':phase,'phase_title':str(course_row.get('phase_title') or f'Phase {phase}'),
        'category':f"Phase {phase}", 'concept':str(course_row.get('concept') or ''),
        'prerequisites':str(course_row.get('prerequisites') or ''),
        'description':str(course_row.get('concept') or course_row.get('instructions') or ''),
        'instructions':[str(course_row.get('instructions') or '')],
        'example_input':str(course_row.get('example_input') or ''),
        'example_output':str(course_row.get('example_output') or ''),
        'expected_output':[str(course_row.get('example_output') or '')] if course_row.get('example_output') else [],
        'source_page':course_row.get('source_page'),'source_path':source_path,'readme_path':readme_path,
        'path':source_path or f"projects/{project_id}"
    }


def complete_saved_catalog(projects):
    if not any(project.get('historical') for project in projects):
        return projects
    existing = {project['id'] for project in projects}
    archive_count = sum(bool(project.get('historical')) for project in projects)
    additions = [course_project(row, ordinal=archive_count + int(row.get('ordinal') or 0)) for row in COURSE.get('projects',[]) if row.get('id') not in existing]
    return sorted(projects + additions,key=lambda project:int(project.get('ordinal') or 0))


def dynamic_catalog(connection, files):
    try:
        curriculum = json.loads(files.get('.episteme/curriculum.json',''))
        mappings = json.loads(files.get('.episteme/projects.json','{}'))
        rows = curriculum['projects']
        mapped = {item['project_id']:item for item in mappings.get('projects',[]) if isinstance(item,dict) and item.get('project_id')}
        if not isinstance(rows,list) or not rows:
            return None
    except (ValueError,TypeError,KeyError):
        return None
    projects = []
    # Preserve the learner's first ten projects as individual archive entries.
    for row in rows[:500]:
        if not isinstance(row,dict) or not row.get('id') or not row.get('title'):
            continue
        if not row.get('historical'):
            continue
        mapping = mapped.get(row['id'],{})
        paths = mapping.get('source_paths') or ([row.get('source_path')] if row.get('source_path') else [])
        source_path = next((str(path) for path in paths if safe_repo_path(str(path))), '')
        readme_path = str(mapping.get('readme_path') or 'README.md')
        if not safe_repo_path(readme_path):
            readme_path = 'README.md'
        criteria = row.get('criteria') if isinstance(row.get('criteria'),list) else []
        expected = [str(item.get('text')) for item in criteria if isinstance(item,dict) and item.get('text')]
        instructions = [str(item) for item in row.get('instructions',[]) if isinstance(item,str)]
        phase = row.get('phase') if isinstance(row.get('phase'),int) else None
        projects.append({
            'id':str(row['id']),'alias':str(row.get('alias') or row['id']),'title':str(row['title']),
            'ordinal':int(row.get('ordinal') or len(projects)+1),'historical':bool(row.get('historical')),
            'phase':phase,'category':'Practice archive' if row.get('historical') else f"Phase {phase}" if phase is not None else 'Curriculum',
            'description':instructions[0] if instructions else 'A mapped project from the repository curriculum.',
            'instructions':instructions,'expected_output':expected,'source_path':source_path,'readme_path':readme_path,
            'path':source_path or f".episteme/projects/{row['id']}"
        })
    offset = len(projects)
    for course_row in COURSE.get('projects',[]):
        mapping = mapped.get(str(course_row.get('id')), {})
        projects.append(course_project(course_row,mapping,offset + int(course_row.get('ordinal') or len(projects)+1)))
    return projects or None

def analyze(project, files):
    source_path = project.get('source_path') or project['path'] + '/main.py'
    readme_path = project.get('readme_path') or project['path'] + '/README.md'
    code = files.get(source_path, '')
    notes = files.get(readme_path, '')
    if project.get('historical') or 'function' not in project:
        tree = None
        if source_path.endswith('.py') and code.strip():
            try:
                tree = ast.parse(code)
            except (SyntaxError,ValueError,RecursionError):
                pass
        valid = bool(code.strip()) and (tree is not None if source_path.endswith('.py') else True)
        checks = [
          {'label':'Solution file is mapped in the repository', 'passed':bool(source_path)},
          {'label':'Solution source exists at the synced commit', 'passed':bool(code.strip())},
          {'label':'Python source parses successfully' if source_path.endswith('.py') else 'Source file is readable', 'passed':valid},
          {'label':'Project instructions are available', 'passed':bool(project.get('instructions') or notes.strip())}
        ]
        if project.get('historical'):
            status = 'completed' if valid else 'in_progress' if code.strip() else 'not_started'
        else:
            status = 'in_progress' if code.strip() else 'not_started'
        return status, checks
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


def catalog(connection, files=None):
    if files:
        dynamic = dynamic_catalog(connection, files)
        if dynamic:
            return dynamic
    root = connection['root']
    return [{**p,'path':'/'.join(filter(None,[root,p['path'].split('/')[-1]])),
             'source_path':'/'.join(filter(None,[root,p['path'].split('/')[-1],'main.py'])),
             'readme_path':'/'.join(filter(None,[root,p['path'].split('/')[-1],'README.md'])),
             'instructions':[p['description']],'expected_output':[],'phase':None,'historical':False,
             'alias':p['id'],'ordinal':index+1} for index,p in enumerate(CATALOG)]


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
    projects = catalog(connection, files)
    db.execute('INSERT OR REPLACE INTO bound_catalog VALUES(?,?,?,?)',(key,json.dumps(projects),sha,timestamp))
    db.execute('DELETE FROM bound_content WHERE binding=?',(key,))
    for p in projects:
        status, checks = analyze(p,files)
        db.execute('INSERT OR REPLACE INTO bound_progress VALUES(?,?,?,?,?,?)',(key,p['id'],status,json.dumps(checks),sha,timestamp))
        source_path = p.get('source_path') or ''
        readme_path = p.get('readme_path') or ''
        source_text = files.get(source_path,'') if source_path else ''
        readme_text = files.get(readme_path,'') if readme_path else ''
        if p.get('historical'):
            readme_path = 'README.md'
            readme_text = readme_section(files.get('README.md',''),p.get('ordinal'))
        example = {'input':p.get('example_input',''),'output':p.get('example_output','')}
        db.execute('INSERT INTO bound_content VALUES(?,?,?,?,?,?,?)',(
            key,p['id'],source_path,source_text,readme_path,readme_text,json.dumps(example)
        ))
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
        saved_catalog = db.execute('SELECT catalog FROM bound_catalog WHERE binding=?',(key,)).fetchone()
    project_catalog = complete_saved_catalog(json.loads(saved_catalog['catalog'])) if saved_catalog else catalog(connection)
    projects = []
    for p in project_catalog:
        saved = records.get(p['id'])
        status, checks = analyze(p,{})
        projects.append({**p,'status':saved['status'] if saved else status,'checks':json.loads(saved['checks']) if saved else checks})
    completed = sum(p['status']=='completed' for p in projects)
    return {**connection,'projects':projects,'completed':completed,'total':len(projects),'percent':round(completed/len(projects)*100) if projects else 0,'activity':activity,'last_sync':activity[0] if activity else None,'webhook_configured':bool(os.environ.get('GITHUB_WEBHOOK_SECRET'))}


@app.get('/api/projects/{project_id}')
def project_detail(project_id: str):
    with database() as db:
        connection = json.loads(db.execute("SELECT value FROM settings WHERE key='binding'").fetchone()[0])
        key = binding_key(connection)
        saved_catalog = db.execute('SELECT catalog,sha FROM bound_catalog WHERE binding=?',(key,)).fetchone()
        records = {r['id']:dict(r) for r in db.execute('SELECT * FROM bound_progress WHERE binding=?',(key,))}
        content = db.execute('SELECT * FROM bound_content WHERE binding=? AND id=?',(key,project_id)).fetchone()
    project_catalog = complete_saved_catalog(json.loads(saved_catalog['catalog'])) if saved_catalog else catalog(connection)
    project = next((p for p in project_catalog if p['id'] == project_id),None)
    if not project:
        raise HTTPException(404,'Project not found in the connected repository curriculum.')
    saved = records.get(project_id)
    status, checks = analyze(project,{})
    detail = {**project,'status':saved['status'] if saved else status,'checks':json.loads(saved['checks']) if saved else checks}
    if content:
        detail.update({
            'source_path':content['source_path'],'source':content['source'],
            'readme_path':content['readme_path'],'readme':content['readme'],
            'example':json.loads(content['expected_output'])
        })
    else:
        detail.update({'source':'','readme':'','example':{'input':project.get('example_input',''),'output':project.get('example_output','')}})
    detail['repository'] = connection['repository']
    detail['sha'] = saved_catalog['sha'] if saved_catalog else ''
    return detail

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

