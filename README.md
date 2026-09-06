# Project Episteme

A personal learning dashboard connected to [iz_time](https://github.com/razaele0003/iz_time). React presents a real progress bar; Python reads GitHub evidence and stores the results in SQLite. Designed with UI/UX Pro Max guidance.

## Run on Windows

Requires Python 3.11+ and Node 22.12+ (tested with Node 24).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
npm run build
.\Start-Episteme.cmd
```

Open http://127.0.0.1:8766. Select **Sync GitHub** to read the current default-branch commit in `razaele0003/iz_time`. No token is required for this public repository. The UI reads saved progress every 30 seconds; this refresh does not itself call GitHub. Manual sync and webhook processing share the same analyzer.

For frontend development, run the backend with `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8766 --no-proxy-headers`, then `npm run dev` in another terminal.

## What progress means

The initial, editable starter path contains three Python milestones. It is not a full curriculum or imported historical credit. Requirements are defined in `backend/catalog.json` and shown in the dashboard. Each milestone needs valid Python, a named non-stub function, the specified AST construct, and a README of at least 40 words. All four source checks must pass for the milestone to count.

These are **static source checks, not proof of correctness, passing execution tests, or mastery**. The analyzer never executes code from GitHub. A semantically wrong implementation may pass these checks; review and executable sandboxed tests are future work. Commit counts never grant completion. Deleting evidence removes the corresponding completion on the next sync. Markdown briefs alone grant no progress.

The pipeline is GitHub → backend analyzer → SQL → dashboard.

## GitHub webhooks

`POST /api/webhooks/github` accepts signed push events only for the currently bound repository on its default branch. It validates the raw-body HMAC-SHA256 signature before reading source, ignores other branches/deletions, deduplicates successful delivery IDs and preserves previous progress on GitHub failures. It resolves the latest default-branch SHA and reads all source at that SHA, so delayed deliveries cannot restore stale commits.

**Automatic GitHub delivery is not provisioned.** A loopback server cannot receive internet webhooks. To enable it, host this backend with persistent disk and expose only `/api/webhooks/github` through a trusted HTTPS proxy, keeping the dashboard/manual-sync routes private. Set `GITHUB_WEBHOOK_SECRET` to a randomly generated secret in the server environment and `EPISTEME_HOSTS` to the allowed hostname. Never commit secrets. In iz_time → Settings → Webhooks, add that HTTPS endpoint, use `application/json`, the same secret, and push events only. Verify GitHub's ping and a real push delivery. Keep Uvicorn `--no-proxy-headers`; never expose `/api/sync` through a proxy. This starter is a single-user, single-process local service, not a multiuser hosted platform.

The receiver acknowledges after sync succeeds; it has no durable queue. GitHub/API slowness may cause a delivery timeout. Use GitHub's redelivery UI after failures (automatic retry is not assumed), or Sync GitHub locally. For production use, add a durable background queue, bounded retries, authentication, rate limiting and deployment-specific tests first.

Signature implementation follows [GitHub's webhook validation documentation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries). Source snapshots use the [Git tree API](https://docs.github.com/en/rest/git/trees). Public unauthenticated API limits apply; optional `GITHUB_TOKEN` is read only from the backend environment.

## Data and checks

`data/progress.sqlite3` stores milestone checks, commit SHAs, sync history and webhook delivery IDs. This directory is ignored by Git. Stop the app before backing it up. `EPISTEME_DB` can select a different SQLite file. Nothing modifies the existing private `episteme` repository or the unrelated Python practice repository.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run build
```

Tests cover signature rejection, repository/branch filtering, replay deduplication, persistence, evidence removal, failed-sync recovery and unconfigured webhook handling. Synthetic fixtures run only in temporary databases.

## Repository connections

Use the dashboard connection form with owner/repository or an HTTPS GitHub URL. The parent folder defaults to projects; leave it blank for the repository root. Connect & sync verifies access and saves a source snapshot before changing the selection. Failed connections preserve the previous selection.

Repository names are arbitrary. The exact milestone folder names (01-temperature, 02-expenses, 03-file-reader) determine which checks apply. Each repository and parent folder keeps separate progress and history. Existing iz_time records are migrated without deleting the original tables.

This binds a repository for reading; it does not create a webhook. Public repositories work without tokens. Private repositories require a read-only GITHUB_TOKEN in the backend environment. Never enter a token in this form. After switching repositories, any future webhook must be configured on the selected repository.
