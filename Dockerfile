FROM node:24-bookworm-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home episteme
COPY backend ./backend
COPY public ./public
COPY --from=frontend /app/dist ./dist
ENV EPISTEME_MODE=public
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["python","-m","uvicorn","backend.main:app","--host","0.0.0.0","--port","8080","--workers","1","--no-proxy-headers","--no-access-log"]
