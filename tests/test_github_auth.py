import time
from urllib.parse import parse_qs, urlparse
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import github_auth as auth

H={'x-episteme-client':'dashboard'}

@pytest.fixture
def client(monkeypatch):
    auth.pending.clear()
    auth.session.clear()
    monkeypatch.setenv('GITHUB_CLIENT_ID','test-client')
    monkeypatch.setenv('GITHUB_CLIENT_SECRET','test-secret')
    yield TestClient(app)
    auth.pending.clear()
    auth.session.clear()

def test_setup_and_header_required(client,monkeypatch):
    assert client.post('/api/github/login').status_code==403
    monkeypatch.delenv('GITHUB_CLIENT_SECRET')
    assert client.get('/api/github/status',headers=H).json()['configured'] is False
    assert client.post('/api/github/login',headers=H).status_code==503

def test_oauth_state_pkce_and_replay(client):
    response=client.post('/api/github/login',headers=H)
    params=parse_qs(urlparse(response.json()['url']).query)
    assert params['scope']==['read:user']
    assert params['code_challenge_method']==['S256']
    assert 'HttpOnly' in response.headers['set-cookie']
    state=params['state'][0]
    result=client.get('/api/github/callback',params={'state':state,'error':'access_denied'},follow_redirects=False)
    assert result.status_code==303 and 'cancelled' in result.headers['location']
    assert client.get('/api/github/callback',params={'state':state}).status_code==400

def test_callback_rejects_different_browser(client):
    url=client.post('/api/github/login',headers=H).json()['url']
    state=parse_qs(urlparse(url).query)['state'][0]
    other=TestClient(app)
    assert other.get('/api/github/callback',params={'state':state,'code':'bad'}).status_code==400

def test_login_success_repositories_and_logout(client,monkeypatch):
    class Response:
        headers={}
        def __init__(self,body):self.body=body
        def raise_for_status(self):pass
        def json(self):return self.body
    monkeypatch.setattr(auth.httpx,'post',lambda *a,**k:Response({'access_token':'test-token','expires_in':3600}))
    monkeypatch.setattr(auth.httpx,'get',lambda *a,**k:Response({'login':'learner'}))
    state=parse_qs(urlparse(client.post('/api/github/login',headers=H).json()['url']).query)['state'][0]
    assert client.get('/api/github/callback',params={'state':state,'code':'test-code'},follow_redirects=False).status_code==303
    result=client.get('/api/github/status',headers=H).json()
    assert result['login']=='learner' and 'test-token' not in str(result)
    monkeypatch.setattr(auth.httpx,'get',lambda *a,**k:Response([{'full_name':'learner/one','private':False},{'full_name':'learner/private','private':True}]))
    assert client.get('/api/github/repositories',headers=H).json()['items']==[{'full_name':'learner/one','description':''}]
    assert client.post('/api/github/logout',headers=H).status_code==200
    assert auth.token() is None

def test_expired_token_is_cleared(client):
    auth.session.update(token='expired',login='learner',expires=time.time()-1)
    assert auth.token() is None
    assert client.get('/api/github/repositories',headers=H).status_code==401
