import hashlib
import json
from html.parser import HTMLParser
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from backend import main as m, public_site as site


@pytest.fixture
def public(monkeypatch, tmp_path):
    monkeypatch.setenv('EPISTEME_MODE', 'public')
    monkeypatch.setenv('PUBLIC_SITE_URL', 'https://example.org')
    monkeypatch.setattr(m, 'DB_PATH', tmp_path / 'must-not-exist.sqlite3')
    return TestClient(m.app)


@pytest.mark.parametrize('path', ['/api/progress','/api/projects/P1','/api/github/status','/workspace','/api/reset','/api/connection','/api/webhooks/github'])
def test_public_never_opens_personal_state(public, path):
    for method in ('get','post','put'):
        response = getattr(public,method)(path, headers={'X-Episteme-Client':'dashboard'})
        assert response.status_code == 404
        assert response.headers['cache-control'] == 'no-store'
        assert 'noindex' in response.headers['x-robots-tag']
    assert not m.DB_PATH.exists()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href',''))


def test_crawl_public_html_and_sitemap(public):
    xml=ET.fromstring(public.get('/sitemap.xml').text)
    urls=[node.text for node in xml.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert len(urls)==25 and len(set(urls))==25
    for url in urls:
        response=public.get(urlsplit(url).path)
        assert response.status_code==200
        assert '<h1>' in response.text and 'rel="canonical"' in response.text
        assert 'https://example.org' in response.text
        assert '<meta name="robots" content="index,follow">' in response.text
        assert 'source-code' not in response.text and 'razaele0003' not in response.text
        encoded=response.text.split('<script type="application/ld+json">')[1].split('</script>')[0]
        schema=json.loads(encoded)
        assert schema['@graph'][0]['@type']=='WebSite'
        parser=Links();parser.feed(response.text)
        for link in parser.links:
            if link.startswith('/'):
                assert public.get(link).status_code==200
    assert not m.DB_PATH.exists()


def test_public_errors_headers_and_robots(public):
    for path in ('/missing','/curriculum/phase-99','/.env','/data/progress.sqlite3','/openapi.json'):
        r=public.get(path)
        assert r.status_code==404 and 'noindex' in r.headers['x-robots-tag']
    r=public.get('/')
    assert r.headers['x-frame-options']=='DENY'
    assert 'frame-ancestors' in r.headers['content-security-policy']
    assert 'nosniff' in r.headers['x-content-type-options']
    assert 'Disallow: /api/' in public.get('/robots.txt').text


def test_local_reads_require_loopback_and_same_origin(monkeypatch):
    monkeypatch.setenv('EPISTEME_MODE','local')
    remote=TestClient(m.app,client=('192.0.2.1',1234))
    assert remote.get('/api/progress').status_code==403
    local=TestClient(m.app)
    assert local.get('/api/progress',headers={'Origin':'https://evil.example'}).status_code==403
    assert local.get('/api/progress',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert local.post('/api/connection',content='x'*9000).status_code==413


def test_curriculum_is_unchanged():
    assert hashlib.sha256((m.ROOT/'backend/course_curriculum.json').read_bytes()).hexdigest()=='36a5c42f700d328868c387593532bae165215874a9491c67affc04850d44586c'


def test_mapping_only_uses_packaged_curriculum():
    projects=m.catalog({'repository':'learner/practice','root':''},{'.episteme/projects.json':json.dumps({'projects':[{'project_id':'P1','project_folder':'projects/P1'}]})})
    assert len(projects)==211
    assert next(p for p in projects if p['id']=='P1')['source_path']=='projects/P1/main.py'


@pytest.mark.parametrize('raw',['broken','[]','{"projects":false}'])
def test_bad_manifest_rejected(raw):
    with pytest.raises(m.HTTPException) as exc:
        m.catalog({'repository':'learner/practice','root':''},{'.episteme/projects.json':raw})
    assert exc.value.status_code==422


def test_new_commit_preserves_old_content(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'DB_PATH',tmp_path/'history.sqlite3')
    c={'repository':'learner/practice','root':''}
    with m.database() as db:
        m.persist_snapshot(db,c,'a'*40,{'README.md':'old reflection'},'manual')
        m.persist_snapshot(db,c,'b'*40,{'README.md':'new reflection'},'manual')
        rows=db.execute('SELECT * FROM evidence_history ORDER BY sha').fetchall()
        assert len(rows)==2
        assert json.loads(rows[0]['payload'])['files']['README.md']=='old reflection'


@pytest.mark.parametrize('value',['http://example.org','https://user:secret@example.org','https://example.org/path','https://example.org?x=1'])
def test_invalid_public_origin(value,monkeypatch):
    monkeypatch.setenv('PUBLIC_SITE_URL',value)
    with pytest.raises(ValueError):
        site.site_origin()
