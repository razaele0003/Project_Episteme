"""Public HTML is built exclusively from the packaged curriculum, never learner data."""
import hashlib
import json
import os
import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

ROOT = Path(__file__).resolve().parent.parent
COURSE = json.loads((ROOT / 'backend/course_curriculum.json').read_text(encoding='utf-8'))
router = APIRouter()


def site_origin():
    value = os.getenv('PUBLIC_SITE_URL', '').rstrip('/')
    if not value:
        return ''
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or re.search(r'[\s<>"\x00-\x1f]', value) or value != 'https://' + parsed.netloc
            or parsed.path or parsed.query or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError('PUBLIC_SITE_URL must be an HTTPS origin without a path or credentials.')
    return value


def public_mode():
    mode = os.getenv('EPISTEME_MODE', 'local')
    if mode not in ('local', 'public'):
        raise ValueError('EPISTEME_MODE must be local or public.')
    return mode == 'public'


def phases():
    return sorted({row['phase'] for row in COURSE['projects']})


def page_paths():
    return ['/', '/curriculum', '/learning-method', '/about'] + [f'/curriculum/phase-{n}' for n in phases()]


def prerequisite_links(text):
    rows = {r['id']: r for r in COURSE['projects']}
    parts = []
    previous = 0
    for match in re.finditer(r'\bP(?:0\.\d+|\d+)\b', text):
        parts.append(escape(text[previous:match.start()]))
        row = rows.get(match.group())
        parts.append(f'<a href="/curriculum/phase-{row["phase"]}#{row["id"]}">{match.group()}</a>' if row else escape(match.group()))
        previous = match.end()
    return ''.join(parts) + escape(text[previous:])


def document(path, title, description, content, status=200):
    origin = site_origin()
    indexable = public_mode() and bool(origin) and status == 200
    url = origin + path
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebSite', '@id': origin + '/#website', 'name': 'Episteme', 'url': origin + '/'},
        {'@type': 'WebPage', '@id': url + '#page', 'url': url, 'name': title,
         'description': description, 'isPartOf': {'@id': origin + '/#website'}, 'inLanguage': 'en'}]}
    if path != '/':
        items = [{'@type': 'ListItem', 'position': 1, 'name': 'Episteme', 'item': origin + '/'}]
        if path.startswith('/curriculum/phase-'):
            items.append({'@type':'ListItem','position':2,'name':'Curriculum','item':origin+'/curriculum'})
        items.append({'@type':'ListItem','position':len(items)+1,'name':title,'item':url})
        schema['@graph'].append({'@type': 'BreadcrumbList', 'itemListElement': items})
    if path == '/curriculum':
        schema['@graph'].append({'@type':'Course','@id':origin+'/curriculum#course',
            'name':COURSE['source_title'],'description':description,'url':url,'inLanguage':'en'})
    elif path.startswith('/curriculum/phase-'):
        schema['@graph'].append({'@type':'LearningResource','name':title,'url':url,
            'learningResourceType':'Project briefs','isPartOf':{'@id':origin+'/curriculum#course'}})
    encoded = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
    digest = __import__('base64').b64encode(hashlib.sha256(encoded.encode()).digest()).decode()
    canonical = f'<link rel="canonical" href="{escape(url, quote=True)}">' if origin else ''
    social = (f'<meta property="og:url" content="{escape(url, quote=True)}">'
              f'<meta property="og:image" content="{escape(origin, quote=True)}/social-card.png">'
              '<meta property="og:image:alt" content="Episteme — build, test, explain">') if origin else ''
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · Episteme</title>
<meta name="description" content="{escape(description, quote=True)}">
<meta name="robots" content="{'index,follow' if indexable else 'noindex,nofollow'}">
<meta name="theme-color" content="#193d2f">{canonical}
<meta property="og:type" content="website"><meta property="og:site_name" content="Episteme">
<meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}">{social}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.png" type="image/png"><link rel="stylesheet" href="/public-site.css">
<script type="application/ld+json">{encoded}</script></head><body>
<a class="skip" href="#content">Skip to content</a><header><a class="brand" href="/"><img src="/favicon.png" alt="" width="40" height="40">Episteme</a>
<nav aria-label="Main navigation"><a href="/curriculum">Curriculum</a><a href="/learning-method">Learning method</a><a href="/about">About</a></nav></header>
<main id="content" tabindex="-1"><h1>{escape(title)}</h1>{content}</main>
<footer><p>Episteme · Engineering learning through inspectable evidence.</p><p>Repository checks are not proof of runtime correctness or independent mastery.</p><a href="/about#privacy">Privacy and use</a></footer></body></html>'''
    return HTMLResponse(html, status_code=status, headers={
        'Cache-Control': 'public, max-age=300' if indexable else 'no-store',
        'Content-Security-Policy': "default-src 'self'; script-src 'sha256-" + digest + "'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        'X-Robots-Tag': 'index, follow' if indexable else 'noindex, nofollow'})


def home():
    count = sum(r['phase'] != 0 for r in COURSE['projects'])
    return document('/', 'Learn to build dependable AI automation',
        'Explore the Episteme engineering curriculum: programming, APIs, data, workflows, AI systems, testing and client delivery.',
        f'<p class="lead">A structured engineering learning platform, from programming fundamentals to AI automation and solutions architecture.</p><p>{count} learning projects across 20 phases, preceded by a preparation guide. Work through the existing sequence at your own pace.</p><p><a class="button" href="/curriculum">Explore the curriculum</a></p>'
        '<section><h2>What does Episteme help you do?</h2><p>Find a project brief, build a solution in your practice repository, test it, explain your decisions, and track the repository evidence. The local workspace connects those files to the roadmap.</p></section>'
        '<section><h2>How is progress different from mastery?</h2><p>Progress records required repository files and source checks. Runtime testing, explanation and independent demonstration remain separate. A green bar does not certify expertise.</p><a href="/learning-method">Read the learning method</a></section>')


@router.get('/curriculum', include_in_schema=False)
def curriculum():
    cards = []
    for number in phases():
        rows = [r for r in COURSE['projects'] if r['phase'] == number]
        cards.append(f'<li><a href="/curriculum/phase-{number}">Phase {number}: {escape(rows[0]["phase_title"])}</a><p>{len(rows)} {"preparation items" if number == 0 else "projects"} · {escape(rows[0]["id"])} to {escape(rows[-1]["id"])}</p></li>')
    return document('/curriculum', 'AI automation curriculum',
        'Follow Episteme’s existing phase sequence, prerequisites, project briefs and examples from setup through engineering delivery.',
        '<p class="lead">Start with preparation, then use the prerequisites in each project to guide your next step.</p><p>The curriculum covers programming, software engineering, data, HTTP, APIs, databases, workflow automation, CRM, AI, retrieval, agents, security, deployment and delivery.</p><ol class="cards">' + ''.join(cards) + '</ol>')


@router.get('/curriculum/phase-{number:int}', include_in_schema=False)
def phase(number: int):
    rows = [r for r in COURSE['projects'] if r['phase'] == number]
    if not rows:
        return not_found()
    title = f'Phase {number}: {rows[0]["phase_title"]}'
    body = '<p><a href="/curriculum">All phases</a></p><p>These are curriculum challenges and examples. Learner solutions and progress are private to the local workspace.</p>'
    body += '<nav aria-label="Projects in this phase">' + ''.join(f'<a href="#{escape(r["id"])}">{escape(r["id"])}</a>' for r in rows) + '</nav>'
    for r in rows:
        body += f'<article id="{escape(r["id"])}"><h2>{escape(r["id"])} · {escape(r["title"])}</h2>'
        for label, key in [('Prerequisites','prerequisites'),('Concept','concept'),('Instructions','instructions'),('Example input','example_input'),('Expected output','example_output')]:
            value = prerequisite_links(r[key]) if key == 'prerequisites' else escape(r[key])
            body += f'<h3>{label}</h3><p class="preserve">{value}</p>'
        body += '</article>'
    body += '<nav aria-label="Phase navigation">'
    if number > 0:
        body += f'<a href="/curriculum/phase-{number-1}">Previous phase</a> · '
    if number < max(phases()):
        body += f'<a href="/curriculum/phase-{number+1}">Next phase</a>'
    body += '</nav>'
    return document(f'/curriculum/phase-{number}', title, f'Explore {len(rows)} curriculum items in {rows[0]["phase_title"]}, with prerequisites, instructions and expected examples.', body)


@router.get('/learning-method', include_in_schema=False)
def method():
    return document('/learning-method', 'Build, test and explain your work',
        'Understand the Episteme learning loop and the difference between repository evidence, runtime verification and independent mastery.',
        '<h2>How do I complete a project?</h2><ol><li>Read the brief and prerequisites.</li><li>Build your own solution in the mapped project folder.</li><li>Run tests with normal, invalid and boundary inputs; keep real output.</li><li>Ask for review, revise and explain how it works and one limitation.</li><li>Update README.md, push to GitHub and sync the local workspace.</li></ol>'
        '<h2>What does a repository sync verify?</h2><p>The local workspace reads a commit and checks mapped BRIEF.md, main.py and README.md files. It parses Python source; it does not execute learner code. A successful sync means the repository was read, not that the answer is correct.</p>'
        '<h2>What is Episteme Coach?</h2><p>An optional external ChatGPT learning companion for hints and evidence review. Access depends on the learner’s ChatGPT account and authorized repository tools. It cannot silently read your editor or update Episteme progress.</p>'
        '<h2>Does completion certify mastery?</h2><p>No. Explain the solution and demonstrate the skill independently. Self-review checkboxes are personal reflection, not an automatic credential.</p><p><a href="/curriculum/phase-0">Begin with preparation</a></p>')


@router.get('/about', include_in_schema=False)
def about():
    return document('/about', 'About Episteme', 'Episteme is an engineering learning platform with a public curriculum and a separate local evidence workspace.',
        '<p class="lead">Episteme connects a structured engineering curriculum to work a learner can inspect, test and explain.</p><p>The public site presents the packaged curriculum. The personal workspace runs locally and stores repository evidence in SQLite. This public edition does not provide hosted learner accounts.</p>'
        '<h2 id="privacy">Privacy and use</h2><p>The application includes no analytics, advertising or tracking cookies on these public pages. Your hosting provider may process request logs. This public edition does not accept repository connections, solutions or learner progress.</p><p>The separate local workspace stores repository snapshots on its computer and optional conversation links in its browser. GitHub and ChatGPT are external services with their own terms. Do not put credentials or private information in a public repository.</p>'
        '<h2>Learning limitations</h2><p>Examples are educational. No employment, certification, security or mastery outcome is guaranteed. Review dependencies, costs and safety before connecting real systems.</p><h2>Content and reuse</h2><p>Public availability does not grant a blanket reuse license. Application code, curriculum, learner work, fonts and artwork have separate rights. Consult the repository licensing notes before reuse.</p><p><a href="/learning-method">How evidence works</a></p>')


def not_found():
    return document('/404', 'Page not found', 'This page is not available.', '<p>Check the address or <a href="/curriculum">browse the curriculum</a>.</p>', 404)


@router.get('/robots.txt', include_in_schema=False)
def robots():
    origin = site_origin()
    text = ('User-agent: *\nDisallow: /api/\nDisallow: /workspace\nSitemap: ' + origin + '/sitemap.xml\n') if public_mode() and origin else 'User-agent: *\nDisallow: /\n'
    return Response(text, media_type='text/plain')


@router.get('/sitemap.xml', include_in_schema=False)
def sitemap():
    origin = site_origin()
    urls = page_paths() if public_mode() and origin else []
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{escape(origin+p)}</loc></url>' for p in urls) + '</urlset>', media_type='application/xml')
