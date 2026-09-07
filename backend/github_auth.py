"""Local single-user OAuth session. Secrets never go to browser storage or SQL."""
import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix='/api/github')
CALLBACK = 'http://127.0.0.1:8766/api/github/callback'
guard = threading.Lock()
pending = {}
session = {}


def local(request, header=True):
    if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
        raise HTTPException(403,'GitHub sign-in is available on this computer only.')
    if header and request.headers.get('x-episteme-client') != 'dashboard':
        raise HTTPException(403,'Use the dashboard for this action.')


def configured():
    return bool(os.environ.get('GITHUB_CLIENT_ID') and os.environ.get('GITHUB_CLIENT_SECRET'))


def token():
    with guard:
        if session.get('expires',0) <= time.time():
            session.clear()
        return session.get('token')


def clear_session():
    with guard:
        session.clear()
        pending.clear()


@router.get('/status')
def status(request: Request):
    local(request)
    active = bool(token())
    with guard:
        user = session.get('login') if active else None
    return {'configured':configured(),'signed_in':active,'login':user,'callback':CALLBACK}


@router.post('/login')
def login(request: Request):
    local(request)
    if not configured():
        raise HTTPException(503,'GitHub sign-in needs one-time OAuth app setup. See README → GitHub sign-in.')
    state = secrets.token_urlsafe(32)
    browser_key = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    with guard:
        for key in list(pending):
            if pending[key]['expires'] < time.time():
                del pending[key]
        if len(pending)>=32:
            raise HTTPException(429,'Too many pending sign-ins. Try again in ten minutes.')
        pending[state] = {'browser':browser_key,'verifier':verifier,'expires':time.time()+600}
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    from fastapi.responses import JSONResponse
    # read:user lists identity + public repositories without requesting repository write access.
    response = JSONResponse({'url':'https://github.com/login/oauth/authorize?' + urlencode({
        'client_id':os.environ['GITHUB_CLIENT_ID'],'redirect_uri':CALLBACK,'state':state,
        'scope':'read:user','code_challenge':challenge,'code_challenge_method':'S256','prompt':'select_account'})})
    response.set_cookie('episteme_oauth',browser_key,httponly=True,samesite='lax',max_age=600,path='/api/github')
    response.headers['Cache-Control']='no-store'
    return response


@router.get('/callback')
def callback(request: Request, state: str='', code: str='', error: str=''):
    local(request,False)
    with guard:
        flow = pending.pop(state,None)
    if not flow or flow['expires']<time.time() or not hmac.compare_digest(flow['browser'],request.cookies.get('episteme_oauth','')):
        raise HTTPException(400,'Sign-in expired or did not originate in this browser. Start again from the dashboard.')
    result = 'cancelled'
    if not error and code:
        try:
            response = httpx.post('https://github.com/login/oauth/access_token',json={
                'client_id':os.environ['GITHUB_CLIENT_ID'],'client_secret':os.environ['GITHUB_CLIENT_SECRET'],
                'code':code,'redirect_uri':CALLBACK,'code_verifier':flow['verifier']},
                headers={'Accept':'application/json'},timeout=20)
            response.raise_for_status()
            body = response.json()
            access = body.get('access_token')
            if not isinstance(access,str) or not access:
                raise ValueError('Missing access token')
            user = httpx.get('https://api.github.com/user',headers={'Authorization':'Bearer '+access,'Accept':'application/vnd.github+json'},timeout=20)
            user.raise_for_status()
            name = user.json()['login']
            if not isinstance(name,str):
                raise ValueError('Missing login')
            with guard:
                session.clear()
                session.update(token=access,login=name,expires=time.time()+min(int(body.get('expires_in',28800)),28800))
            result='connected'
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            result='failed'
    response = RedirectResponse('/?github='+result,status_code=303)
    response.delete_cookie('episteme_oauth',path='/api/github')
    response.headers['Cache-Control']='no-store'
    response.headers['Referrer-Policy']='no-referrer'
    return response


@router.get('/repositories')
def repositories(request: Request, page: int=1):
    local(request)
    if page<1 or page>100:
        raise HTTPException(422,'Invalid repository page.')
    access = token()
    if not access:
        raise HTTPException(401,'Sign in to GitHub first.')
    try:
        response = httpx.get('https://api.github.com/user/repos',params={'visibility':'public','sort':'updated','per_page':50,'page':page},headers={'Authorization':'Bearer '+access,'Accept':'application/vnd.github+json'},timeout=20)
        response.raise_for_status()
        rows = response.json()
        items = [{'full_name':r['full_name'],'description':r.get('description') or ''} for r in rows if not r.get('private')]
        return {'items':items,'has_more':'rel="next"' in response.headers.get('link','')}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        raise HTTPException(502,'Could not load repositories. Try signing in again or entering a public repository URL.')


@router.post('/logout')
def logout(request: Request):
    local(request)
    clear_session()
    return {'signed_in':False}
