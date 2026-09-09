"""Stateless public-repository checks. Progress is persisted only in the browser."""
import json
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

if os.getenv('VERCEL'):
    os.environ['EPISTEME_MODE'] = 'public'
    os.environ['PUBLIC_SITE_URL'] = 'https://' + (os.getenv('VERCEL_PROJECT_PRODUCTION_URL') or os.environ['VERCEL_URL'])

from backend.main import ConnectionInput, analyze, catalog, normalize_connection, now, snapshot
from backend import public_site

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(public_site.router)


@app.middleware('http')
async def boundary(request: Request, call_next):
    if request.method == 'POST':
        if request.headers.get('x-episteme-client') != 'dashboard':
            return JSONResponse({'detail': 'Use the Episteme dashboard.'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Cross-site requests are not allowed.'}, status_code=403)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 8192:
                return JSONResponse({'detail': 'Request is too large.'}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    if request.url.path.startswith('/api/'):
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def presentation(connection, files, sha=''):
    projects = []
    for project in catalog(connection, files):
        status, checks = analyze(project, files)
        content = {name: files.get(project.get(name + '_path', ''), '') for name in ('brief', 'source', 'readme')}
        ready = bool(project.get('project_folder') and all(value.strip() for value in content.values()))
        if not ready:
            status = 'in_progress' if any(value.strip() for value in content.values()) else 'not_started'
        projects.append({**project, 'status': status, 'checks': checks, 'structure_ready': ready,
                         **{name: value if ready else '' for name, value in content.items()},
                         'repository': connection['repository'], 'sha': sha,
                         'missing_structure': [filename for name, filename in [('brief', 'BRIEF.md'), ('source', 'main.py'), ('readme', 'README.md')] if not content[name].strip()],
                         'example': {'input': project.get('example_input', ''), 'output': project.get('example_output', '')}})
    learning = [p for p in projects if not p.get('historical') and p.get('phase') != 0]
    completed = sum(p['status'] == 'completed' for p in learning)
    event = {'id': sha, 'sha': sha, 'source': 'manual', 'created_at': now()} if sha else None
    return {**connection, 'projects': projects, 'completed': completed, 'total': len(learning),
            'percent': round(completed / len(learning) * 100) if learning else 0,
            'activity': [event] if event else [], 'last_sync': event, 'webhook_configured': False}


@app.get('/api/browser-bootstrap')
def bootstrap():
    return presentation({'repository': '', 'root': ''}, {})


@app.post('/api/browser-sync')
def sync_public(value: ConnectionInput):
    connection = normalize_connection(value)
    base = 'https://api.github.com/repos/' + connection['repository']
    started = time.monotonic()
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Episteme-Public-Checks'}
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            # Anonymous check first: the operator's token must never expose a private repository.
            public = client.get(base, headers=headers)
            if public.status_code in (403, 429):
                raise HTTPException(429, 'GitHub rate limit reached. Try again later. Your saved progress was kept.')
            if public.status_code != 200 or public.json().get('private') is not False:
                raise HTTPException(404, 'Public repository not found. Check the owner and repository name.')
            token = os.getenv('GITHUB_TOKEN', '')
            if token:
                headers['Authorization'] = 'Bearer ' + token

            def read(path):
                if time.monotonic() - started > 230:
                    raise HTTPException(422, 'This repository took too long to check. Saved progress was kept.')
                if not path:
                    return public.json()
                response = client.get(base + '/' + path, headers=headers)
                if response.status_code in (403, 429):
                    raise HTTPException(429, 'GitHub rate limit reached. Try again later. Your saved progress was kept.')
                if response.status_code == 404:
                    raise HTTPException(404, 'Repository branch or evidence was not found. Push your initial commit, then retry.')
                response.raise_for_status()
                return response.json()

            sha, files = snapshot(connection, reader=read)
            result = presentation(connection, files, sha)
            if len(json.dumps(result).encode()) > 3_500_000:
                raise HTTPException(422, 'The snapshot is too large for this free release. Saved progress was kept.')
            return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, 'GitHub could not be read. Your saved progress was kept.') from exc
