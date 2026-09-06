import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from backend import main as m

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(m,'DB_PATH',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GITHUB_WEBHOOK_SECRET','test-only-secret')
    return TestClient(m.app)

def source():
    p=m.CATALOG[0]
    return {p['path']+'/main.py':'def celsius_to_fahrenheit(c):\n    return c * 9 / 5 + 32\n',p['path']+'/README.md':'Explanation of inputs outputs and edge cases. '*8}

def test_empty_and_stub_are_not_complete():
    p=m.CATALOG[0]
    assert m.analyze(p,{})[0]=='not_started'
    files=source()
    files[p['path']+'/main.py']='def celsius_to_fahrenheit(c):\n    pass\n'
    assert m.analyze(p,files)[0]=='in_progress'
    files[p['path']+'/main.py']='def celsius_to_fahrenheit(:\n'
    assert m.analyze(p,files)[0]=='in_progress'

def test_sync_persists_and_deletion_recalculates(client,monkeypatch):
    monkeypatch.setattr(m,'snapshot',lambda:('a'*40,source()))
    assert client.post('/api/sync',headers={'x-episteme-client':'dashboard'}).status_code==200
    data=client.get('/api/progress').json()
    assert data['completed']==1 and data['percent']==33
    assert data['projects'][0]['status']=='completed'
    # A fresh connection reads persisted results, not a UI-only count.
    with m.database() as db:
        assert db.execute('SELECT status FROM progress WHERE id="PY01"').fetchone()[0]=='completed'
    monkeypatch.setattr(m,'snapshot',lambda:('b'*40,{}))
    m.sync()
    assert client.get('/api/progress').json()['completed']==0

def signed(payload,delivery='test-delivery'):
    body=json.dumps(payload).encode()
    return body,{'x-hub-signature-256':'sha256='+hmac.new(b'test-only-secret',body,hashlib.sha256).hexdigest(),'x-github-event':'push','x-github-delivery':delivery,'content-type':'application/json'}

def test_signature_repo_branch_and_duplicate(client,monkeypatch):
    calls=[]
    def read():
        calls.append(1)
        return 'a'*40,source()
    monkeypatch.setattr(m,'snapshot',read)
    payload={'repository':{'full_name':m.REPO,'default_branch':'main'},'ref':'refs/heads/main'}
    body,headers=signed(payload)
    assert client.post('/api/webhooks/github',content=body).status_code==403
    assert client.post('/api/webhooks/github',content=body,headers=headers).status_code==200
    assert client.post('/api/webhooks/github',content=body,headers=headers).json()['duplicate']
    assert len(calls)==1
    payload['ref']='refs/heads/feature'
    body,headers=signed(payload,'other')
    assert client.post('/api/webhooks/github',content=body,headers=headers).json()['ignored']
    payload['repository']['full_name']='other/repository'
    body,headers=signed(payload,'third')
    assert client.post('/api/webhooks/github',content=body,headers=headers).status_code==403
    assert len(calls)==1

def test_failed_sync_retains_data_and_can_retry(client,monkeypatch):
    monkeypatch.setattr(m,'snapshot',lambda:('a'*40,source()))
    m.sync()
    def fail():
        raise m.HTTPException(502,'GitHub unavailable')
    monkeypatch.setattr(m,'snapshot',fail)
    body,headers=signed({'repository':{'full_name':m.REPO,'default_branch':'main'},'ref':'refs/heads/main'})
    assert client.post('/api/webhooks/github',content=body,headers=headers).status_code==502
    assert client.get('/api/progress').json()['completed']==1
    monkeypatch.setattr(m,'snapshot',lambda:('b'*40,{}))
    assert client.post('/api/webhooks/github',content=body,headers=headers).status_code==200

def test_manual_sync_requires_header(client):
    assert client.post('/api/sync').status_code==403

def test_webhook_without_secret_disabled(client,monkeypatch):
    monkeypatch.delenv('GITHUB_WEBHOOK_SECRET')
    assert client.post('/api/webhooks/github').status_code==503

def test_repository_url_has_no_trailing_slash(monkeypatch):
    seen=[]
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'default_branch':'main'}
    def get(url,**kwargs):
        seen.append(url)
        return Response()
    monkeypatch.setattr(m.httpx,'get',get)
    m.github('')
    assert seen==['https://api.github.com/repos/'+m.REPO]

def test_incomplete_tree_does_not_zero_progress(monkeypatch):
    def get(path):
        if not path:
            return {'default_branch':'main'}
        if path.startswith('commits/'):
            return {'sha':'c'*40}
        return {'truncated':True,'tree':[]}
    monkeypatch.setattr(m,'github',get)
    with pytest.raises(m.HTTPException) as error:
        m.snapshot()
    assert error.value.status_code==502
