"""Fail-closed deployment boundary; public mode never opens the personal API."""
import time
from collections import deque

from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.public_site import public_mode


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.actions = deque()

    async def dispatch(self, request, call_next):
        path = request.url.path
        private = path.startswith('/api/') or path == '/workspace'
        response = None
        if public_mode() and private:
            response = JSONResponse({'detail': 'The personal workspace is available locally only.'}, status_code=404)
        elif not public_mode() and path != '/api/webhooks/github':
            if not request.client or request.client.host not in ('127.0.0.1', '::1', 'testclient'):
                response = JSONResponse({'detail': 'This workspace is local only.'}, status_code=403)
        if private and response is None and path != '/api/webhooks/github':
            origin = request.headers.get('origin')
            # Callback is a top-level OAuth navigation, not a cross-site API fetch.
            callback = path == '/api/github/callback' and request.method == 'GET'
            if not callback and (request.headers.get('sec-fetch-site') == 'cross-site' or (
                origin and origin not in (str(request.base_url).rstrip('/'), 'http://127.0.0.1:5173', 'http://localhost:5173')
            )):
                response = JSONResponse({'detail': 'Cross-origin workspace access is not allowed.'}, status_code=403)
        if response is None and private and request.method in ('POST', 'PUT', 'PATCH'):
            limit = 2_000_000 if path == '/api/webhooks/github' else 8192
            chunks = bytearray()
            async for chunk in request.stream():
                chunks.extend(chunk)
                if len(chunks) > limit:
                    response = JSONResponse({'detail': 'Request is too large.'}, status_code=413)
                    break
            if response is None:
                request._body = bytes(chunks)
                current = time.monotonic()
                while self.actions and self.actions[0] < current - 60:
                    self.actions.popleft()
                if len(self.actions) >= 60:
                    response = JSONResponse({'detail': 'Too many actions. Try again in one minute.'}, status_code=429, headers={'Retry-After': '60'})
                else:
                    self.actions.append(current)
        if response is None:
            response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if private or not public_mode() or response.status_code >= 400:
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        if path.startswith('/assets/') and response.status_code == 200:
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        if public_mode():
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response
