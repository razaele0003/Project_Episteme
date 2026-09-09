import json
from fastapi.testclient import TestClient
from api import index as api
from backend import main


def test_bootstrap_never_opens_database(monkeypatch):
    def forbidden():
        raise AssertionError('Stateless API must not access SQLite')
    monkeypatch.setattr(main, 'database', forbidden)
    client = TestClient(api.app)
    result = client.get('/api/browser-bootstrap')
    assert result.status_code == 200
    assert result.json()['repository'] == ''
    assert result.json()['total'] == 206
    assert len(result.json()['projects']) == 211
    assert client.get('/api/progress').status_code == 404
    assert client.get('/api/github/status').status_code == 404


def test_stateless_structure_and_syntax_checks():
    mapping = {'.episteme/projects.json': json.dumps({'projects':[{'project_id':'P1', 'project_folder':'projects/P1'}]})}
    data = api.presentation({'repository':'owner/repo','root':''}, mapping)
    assert data['completed'] == 0
    mapping.update({'projects/P1/BRIEF.md':'The project brief', 'projects/P1/main.py':'print(2 + 2)', 'projects/P1/README.md':'I add two numbers.'})
    data = api.presentation({'repository':'owner/repo','root':''}, mapping, 'a'*40)
    project = next(p for p in data['projects'] if p['id'] == 'P1')
    assert data['completed'] == 1 and project['structure_ready']
    mapping['projects/P1/main.py'] = 'def broken(:'
    assert api.presentation({'repository':'owner/repo','root':''}, mapping)['completed'] == 0
    del mapping['projects/P1/README.md']
    project = next(p for p in api.presentation({'repository':'owner/repo','root':''}, mapping)['projects'] if p['id']=='P1')
    assert not project['structure_ready'] and project['source'] == ''


def test_stateless_request_boundary():
    client = TestClient(api.app)
    assert client.post('/api/browser-sync', json={}).status_code == 403
    headers = {'x-episteme-client':'dashboard'}
    assert client.post('/api/browser-sync', headers=headers, json={'repository':'http://localhost/private'}).status_code == 422
    assert client.post('/api/browser-sync', headers=headers, content='x'*8193).status_code == 413
    assert client.post('/api/browser-sync', headers={**headers,'sec-fetch-site':'cross-site'}, json={}).status_code == 403


def test_private_repository_is_never_read_with_operator_token(monkeypatch):
    import httpx
    calls = []
    real_client = httpx.Client
    def transport(request):
        calls.append(request)
        return httpx.Response(404, json={'message':'Not Found'})
    monkeypatch.setenv('GITHUB_TOKEN', 'test-only-token')
    monkeypatch.setattr(api.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(transport), **kwargs))
    result = TestClient(api.app).post('/api/browser-sync', headers={'x-episteme-client':'dashboard'}, json={'repository':'owner/private'})
    assert result.status_code == 404
    assert len(calls) == 1 and 'authorization' not in calls[0].headers
