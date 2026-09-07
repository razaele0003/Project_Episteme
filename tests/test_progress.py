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
    return {p['path']+'/main.py':'def celsius_to_fahrenheit(c):\n    return c * 9 / 5 + 32\n',p['path']+'/README.md':'Explanation of inputs outputs and edge cases. '*8,p['path']+'/BRIEF.md':'Convert Celsius to Fahrenheit.'}

def test_empty_and_stub_are_not_complete():
    p=m.CATALOG[0]
    assert m.analyze(p,{})[0]=='not_started'
    files=source()
    files[p['path']+'/main.py']='def celsius_to_fahrenheit(c):\n    pass\n'
    assert m.analyze(p,files)[0]=='in_progress'
    files[p['path']+'/main.py']='def celsius_to_fahrenheit(:\n'
    assert m.analyze(p,files)[0]=='in_progress'

def test_sync_persists_and_deletion_recalculates(client,monkeypatch):
    monkeypatch.setattr(m,'snapshot',lambda *args:('a'*40,source()))
    assert client.post('/api/sync',headers={'x-episteme-client':'dashboard'}).status_code==200
    data=client.get('/api/progress').json()
    assert data['completed']==1 and data['percent']==33
    assert data['projects'][0]['status']=='completed'
    # A fresh connection reads persisted results, not a UI-only count.
    with m.database() as db:
        assert db.execute('SELECT status FROM bound_progress WHERE id="PY01"').fetchone()[0]=='completed'
    monkeypatch.setattr(m,'snapshot',lambda *args:('b'*40,{}))
    m.sync()
    assert client.get('/api/progress').json()['completed']==0

def signed(payload,delivery='test-delivery'):
    body=json.dumps(payload).encode()
    return body,{'x-hub-signature-256':'sha256='+hmac.new(b'test-only-secret',body,hashlib.sha256).hexdigest(),'x-github-event':'push','x-github-delivery':delivery,'content-type':'application/json'}

def test_signature_repo_branch_and_duplicate(client,monkeypatch):
    calls=[]
    def read(*args):
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
    monkeypatch.setattr(m,'snapshot',lambda *args:('a'*40,source()))
    m.sync()
    def fail(*args):
        raise m.HTTPException(502,'GitHub unavailable')
    monkeypatch.setattr(m,'snapshot',fail)
    body,headers=signed({'repository':{'full_name':m.REPO,'default_branch':'main'},'ref':'refs/heads/main'})
    assert client.post('/api/webhooks/github',content=body,headers=headers).status_code==502
    assert client.get('/api/progress').json()['completed']==1
    monkeypatch.setattr(m,'snapshot',lambda *args:('b'*40,{}))
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
    m.github('',m.REPO)
    assert seen==['https://api.github.com/repos/'+m.REPO]

def test_incomplete_tree_does_not_zero_progress(monkeypatch):
    def get(path,*args):
        if not path:
            return {'default_branch':'main'}
        if path.startswith('commits/'):
            return {'sha':'c'*40}
        return {'truncated':True,'tree':[]}
    monkeypatch.setattr(m,'github',get)
    with pytest.raises(m.HTTPException) as error:
        m.snapshot()
    assert error.value.status_code==502

def test_connection_switch_and_failed_access_preserve_progress(client,monkeypatch):
    monkeypatch.setattr(m,'snapshot',lambda *args:('a'*40,source()))
    m.sync()
    headers={'x-episteme-client':'dashboard'}
    monkeypatch.setattr(m,'snapshot',lambda *args:('b'*40,{}))
    assert client.put('/api/connection',json={'repository':'https://github.com/someone/another-name','root':'learning'},headers=headers).status_code==200
    data=client.get('/api/progress').json()
    assert data['completed']==0 and data['repository']=='someone/another-name'
    assert data['projects'][0]['path']=='learning/01-temperature'
    def fail(*args):
        raise m.HTTPException(502,'Unavailable')
    monkeypatch.setattr(m,'snapshot',fail)
    assert client.put('/api/connection',json={'repository':m.REPO},headers=headers).status_code==502
    assert m.binding()['repository']=='someone/another-name'
    with m.database() as db:
        assert db.execute('SELECT status FROM bound_progress WHERE binding=? AND id=?',(m.REPO+':projects','PY01')).fetchone()[0]=='completed'
    monkeypatch.setattr(m,'snapshot',lambda *args:('c'*40,source()))
    assert client.put('/api/connection',json={'repository':m.REPO},headers=headers).status_code==200
    assert client.get('/api/progress').json()['completed']==1

@pytest.mark.parametrize('repo,root',[('https://evil.example/x/y','projects'),('a/b/c','projects'),('a/b','../secrets'),('a/b','x//y')])
def test_bad_bindings_rejected(client,repo,root):
    assert client.put('/api/connection',json={'repository':repo,'root':root},headers={'x-episteme-client':'dashboard'}).status_code==422

def test_legacy_completion_without_project_structure_is_retired(client):
    import sqlite3
    with sqlite3.connect(m.DB_PATH) as db:
        db.execute('CREATE TABLE progress(id TEXT PRIMARY KEY,status TEXT,checks TEXT,sha TEXT,updated_at TEXT)')
        db.execute('INSERT INTO progress VALUES(?,?,?,?,?)',('PY01','completed','[]','a'*40,'2026-09-06'))
    assert client.get('/api/progress').json()['completed']==0
    assert client.get('/api/progress').json()['completed']==0

def test_root_folder_mapping():
    assert m.catalog({'repository':'a/any-name','root':''})[0]['path']=='01-temperature'

def test_wrong_parent_reports_actual_folder(monkeypatch):
    def get(path,*args):
        if not path:
            return {'default_branch':'main'}
        if path.startswith('commits/'):
            return {'sha':'c'*40}
        return {'tree':[{'path':'projects/01-temperature','type':'tree'}]}
    monkeypatch.setattr(m,'github',get)
    with pytest.raises(m.HTTPException) as error:
        m.snapshot({'repository':'any/repo','root':''})
    assert error.value.status_code==422 and 'under projects' in error.value.detail


def test_repository_curriculum_adds_course_and_project_detail(client,monkeypatch):
    files={
      '.episteme/curriculum.json':json.dumps({'projects':[{
        'id':'P001','title':'Ohm archive','ordinal':1,'historical':True,
        'source_path':'projects/one/main.py','criteria':[]
      }]}),
      '.episteme/projects.json':json.dumps({'projects':[{'project_id':'P001','project_folder':'projects/one'}]}),
      'README.md':'### 1. Ohm archive\n\nExplain the first solution.\n',
      'projects/one/BRIEF.md':'Build the first solution.\n',
      'projects/one/README.md':'Explain the first solution.\n',
      'projects/one/main.py':'print(42)\n'
    }
    monkeypatch.setattr(m,'snapshot',lambda *args:('d'*40,files))
    response=client.post('/api/sync',headers={'x-episteme-client':'dashboard'})
    assert response.status_code==200
    progress=client.get('/api/progress').json()
    assert len(progress['projects'])==203
    assert progress['projects'][0]['title']=='Ohm archive'
    phase_zero=next(p for p in progress['projects'] if p['id']=='P0.1')
    assert phase_zero['title']=='Professional Development Environment'
    detail=client.get('/api/projects/P001').json()
    assert detail['source']=='print(42)\n'
    assert detail['readme']=='Explain the first solution.\n'
    assert detail['brief']=='Build the first solution.\n'
    assert detail['structure_ready'] is True
    course_detail=client.get('/api/projects/P0.1').json()
    assert course_detail['example']['input']
    assert course_detail['example']['output']=='True'
    assert course_detail['next_project']['id']=='P0.2'
    assert course_detail['previous_project'] is None


def test_flat_historical_file_is_not_project_evidence(client,monkeypatch):
    files={
      '.episteme/curriculum.json':json.dumps({'projects':[{'id':'P001','title':'Old flat file','ordinal':1,'historical':True,'source_path':'one.py'}]}),
      '.episteme/projects.json':json.dumps({'projects':[{'project_id':'P001','source_paths':['one.py']}]}),
      'README.md':'### 1. Old flat file\n\nNotes.\n',
      'one.py':'print(42)\n'
    }
    monkeypatch.setattr(m,'snapshot',lambda *args:('e'*40,files))
    assert client.post('/api/sync',headers={'x-episteme-client':'dashboard'}).status_code==200
    project=client.get('/api/projects/P001').json()
    assert project['status']=='not_started'
    assert project['structure_ready'] is False
    assert project['source']=='' and project['readme']==''
