# Deployment and operations

## Free Vercel browser workspace (September 2026)

The owner selected the full dashboard with browser-local progress instead of paid Render storage. `vercel.json` uses Vite, `npm run build:vercel`, and `dist`. IndexedDB holds repository bindings, commit snapshots, source evidence and progress. Coach links and self-review remain in localStorage. Data is scoped to the device, browser profile and website origin. Clearing site data removes it; the download button exports IndexedDB records as JSON. Local SQLite data and secrets are never uploaded automatically.

`api/index.py` is a stateless Python function for bootstrap curriculum and public-repository checks. It does not expose the local API, SQLite or OAuth session. Enter a public GitHub URL without login. Private repositories and background webhooks are unavailable in this release. Repository visibility is verified anonymously before using an optional server-only `GITHUB_TOKEN`. Code is inspected at a commit SHA and never executed; file checks are not proof of correctness or mastery. Failed network, validation, quota or storage operations preserve the previous browser snapshot.

No paid service or required secret is used. Vercel's system URL supplies the canonical origin for public information pages. Optional `GITHUB_TOKEN` belongs only in Vercel's server environment, never a `VITE_` variable. GitHub and Vercel free quotas apply. For development, run `python -m uvicorn api.index:app --port 8793` and `npx vite --mode browser --port 8792`. Run `npx playwright test -c playwright.browser.config.js` for persistence and isolation checks.

The following sections describe the separate local/public-container modes. The Windows launcher now loads an ignored `.env` when present; direct Python launches require explicit environment configuration.

## Supported release boundary

Public mode serves curriculum information only. Local mode preserves the personal learning workspace. This release does **not** implement hosted multi-user accounts. Never expose local mode through a public reverse proxy, tunnel, LAN bind or forwarded client headers. Do not deploy the personal SQLite database or GitHub secrets with the public site.

The same FastAPI service serves the public HTML, assets and health endpoint. A container host is a better fit for this existing architecture than splitting Vercel and a separate backend. PostgreSQL is not needed for a read-only public curriculum. A future hosted workspace needs user identity, tenant-scoped storage and authorization before database migration.

## Public container

```sh
docker build -t episteme:release .
docker run --rm -p 8080:8080 -e PUBLIC_SITE_URL=https://YOUR-OWNED-DOMAIN episteme:release
```

Replace the domain before running. No domain is assumed owned. The image sets `EPISTEME_MODE=public` and refuses to start without a valid HTTPS origin. Place behind the hosting provider's HTTPS termination. Set the provider's internal port to 8080; health path `/healthz`. One worker is sufficient. No persistent volume, OAuth secrets or learner data belong in this public container.

Use the same origin for HTML and assets. Do not add wildcard CORS. The server accepts the configured hostname and loopback health probes; ensure the proxy preserves the incoming Host header. Uvicorn proxy-header trust is disabled intentionally. HTTP-to-HTTPS redirection belongs at the edge. Test HTTPS, certificate renewal, custom domain redirects and canonical origin on the real host before launch. HSTS is sent in public mode, without automatic preload/subdomain enrollment.

## Environment contract

| Variable | Default | Purpose |
|---|---|---|
| `EPISTEME_MODE` | `local` (container: `public`) | Public mode denies all learner APIs, including OAuth and webhooks. |
| `PUBLIC_SITE_URL` | unset | Required HTTPS origin in public mode; canonical, schema, sitemap and social links. |
| `EPISTEME_DB` | `data/progress.sqlite3` | Local workspace database only. |
| `GITHUB_TOKEN` | unset | Optional local backend token, minimal read-only Contents permission for selected repositories. |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | unset | Optional local OAuth app; callback `http://127.0.0.1:8766/api/github/callback`. |
| `GITHUB_WEBHOOK_SECRET` | unset | Local webhook receiver HMAC secret; merely setting it does not connect deliveries. Public mode disables this route. |

`.env.example` is documentation. Environment files are not automatically loaded. Set variables in your shell or host settings. Never use `VITE_` prefixes for secrets. No credentials enter browser storage or public metadata. OAuth session remains single-user, in memory, expires and disappears on restart; this is not hosted authentication.

## Local backup, migration and rollback

Before upgrading, make a consistent backup:

```powershell
.\.venv\Scripts\python.exe scripts/backup.py data/progress.sqlite3 backups/before-release.sqlite3
```

Keep backups outside the repository, encrypted where appropriate. Do not publish them as CI artifacts. The script refuses to overwrite an existing backup and checks SQLite integrity. Verify restore to a separate temporary path, launch with `EPISTEME_DB` pointing there, and inspect your known repository and evidence before replacing live data. Stop the workspace before replacing its database. Copy the old database and previous application release together for rollback.

The additive migration creates `evidence_history`. New syncs preserve content and checks by binding and commit; the last available pre-upgrade snapshot is preserved before replacement. Earlier events with only a SHA cannot be reconstructed automatically. Explicit workspace reset also deletes archived evidence. Browser conversation links/self-review are separate localStorage entries and require separate browser-profile backup/deletion.

## Release checks and rollback

Run the README checks, then deploy an immutable image tag to staging. Verify all 25 sitemap URLs, true 404s, favicon/social PNG and private API denials using the actual domain. Submit sitemap to Search Console only after ownership and indexability checks. Keep the previous image tag; public rollback is replacing the image, without a data migration. Do not enable automatic publishing from CI until the owner selects a host and reviews rights/policies.

Public mode has no user actions to rate-limit. Local mutation endpoints have a 60/minute process-wide guard and request body limits; GitHub evidence has per-file and aggregate limits. Configure edge connection/request timeouts and abuse protection for the chosen host. The local sync lock and in-memory limiter require one worker. The health endpoint reports process availability, not GitHub availability or database backup health.

## Monitoring and privacy

No analytics SDK is installed. Prefer aggregate uptime/error counts without repository names, source text, query strings or tokens. Uvicorn access logs are disabled by default in the supplied commands. Choose and document hosting log retention, access, deletion/contact process and jurisdiction before publishing a final privacy policy. Field LCP, INP and CLS, real social previews, TLS and crawler indexing remain deployment checks, not guarantees from local tests.
