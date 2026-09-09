# Project Episteme

Episteme is a personal learning dashboard that reads project evidence from a GitHub repository. It combines the AI Automation course curriculum with each repository's mapped source files and README notes, then saves the exact synced commit in local SQLite storage.

Repository names are arbitrary; `.episteme/projects.json` controls which files belong to each project. A fresh workspace starts disconnected. The public deployment mode serves curriculum information only and denies personal APIs; this is not a hosted multi-user account system. See [deployment instructions](docs/DEPLOYMENT.md) and the [production readiness report](docs/PRODUCTION-READINESS-REPORT.md).

## Run on Windows

Requires Python 3.11+ and Node 24 LTS for the complete build/quality toolchain.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
npm run build
.\Start-Episteme.cmd
```

Open http://127.0.0.1:8766. Use **Connect and load** to bind a public GitHub repository, or configure GitHub sign-in to choose one from an account. Use **Sync repository** after pushing changes.

## Project pages

The packaged course catalog contains all 211 curriculum rows. Phase 0 is presented as a repository and tool setup guide, so its five preparation items are not treated as projects. The progress bar covers the 206 learning projects in Phases 1–20. The first ten Python foundation projects are listed separately as P1 through P10.

Every project page can show:

- the curriculum instructions and prerequisites;
- deterministic example input and expected output;
- the solution source saved from the connected GitHub commit;
- the project's mapped README file;
- the evidence checks used for the progress state.

The learning interface separates six jobs: Dashboard shows what to do now, Roadmap explains the phase journey, Projects contains the build catalog, Skills summarizes repository evidence without claiming mastery, Portfolio shows only complete project evidence, and Sync history records technical snapshots. Project pages follow Mission → Why → Prerequisites → Build → Test → Review → Readiness.

Phase 0 links to the configured Episteme Coach. Access and GitHub capabilities depend on the learner's ChatGPT account; availability to other users has not been verified. The configured instructions request hints, authorized evidence inspection and honest test verification. Episteme cannot guarantee the model's response or automatically import its verdict. Conversation links are saved manually in this browser per repository/project. Prompts are editable, and sending remains the learner's action.

Course content is stored in `backend/course_curriculum.json`. The optional import script requires `pdfplumber` separately; regenerating it requires curriculum-owner review and must not overwrite the curated catalog casually.

## Repository mapping

Add `.episteme/projects.json` to the connected repository. Every project must map one folder containing the same three required files: `BRIEF.md`, `main.py`, and `README.md`. Loose files and sections from the repository-level README do not count as project evidence.

```json
{
  "schema_version": 1,
  "projects": [
    {
      "project_id": "P1",
      "project_folder": "projects/P1"
    }
  ]
}
```

Episteme also reads `.episteme/curriculum.json` when present. Rows marked `historical: true` are kept as Practice archive entries, but they remain not started until they are moved into the required folder structure and mapped with `project_folder`.

## How synchronization works

The local flow is:

```text
GitHub repository → FastAPI snapshot reader → evidence checks → SQLite → React dashboard
```

A manual sync reads the repository's default branch, resolves one commit SHA, downloads the curriculum manifest and mapped text files at that commit, and stores the catalog, source, README, checks, and sync history locally. The dashboard never writes to the connected repository and never executes downloaded learner code.

This does not require a webhook. Manual sync is the intended local workflow. The signed receiver exists for testing, but GitHub cannot deliver to loopback. Do not expose the local personal API merely to enable webhooks. Public deployment mode disables webhooks and all learner endpoints; hosted learner integration needs a separate authenticated architecture.

## Progress meaning

Progress records visible repository evidence for Phases 1–20. It does not claim code correctness or independent mastery. Phase 0 preparation and historical archive entries never change the percentage. Incomplete evidence never completes a project. Removing evidence recalculates the current state on the next successful sync, while earlier snapshots remain stored by commit. A failed sync keeps the saved state. Reset explicitly removes all stored snapshots. Older pre-upgrade events may have only commit links. Legacy three-exercise repositories retain their original checks when their actual folders are detected; they are not the 206-project curriculum.

## GitHub sign-in

Manual public repository input works without credentials. For the repository picker, register a GitHub OAuth app with homepage `http://127.0.0.1:8766` and callback `http://127.0.0.1:8766/api/github/callback`, then set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in the backend environment and restart Episteme.

The OAuth flow requests `read:user`; it does not request repository write access. Tokens stay in backend memory for the local session. Keep secrets out of Git and out of the browser form.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install ruff==0.16.6 pip-audit==2.10.1
npm run lint
npm run typecheck
.\.venv\Scripts\python.exe -m ruff check backend tests scripts
.\.venv\Scripts\python.exe -m pytest -q
npm run build
npm run check:budget
npm audit --audit-level=high
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
npx playwright install chromium
npm run test:browser
```

If the Playwright browser download is unavailable and Chrome is installed, set `$env:PLAYWRIGHT_CHANNEL='chrome'` before browser tests. Tests use isolated temporary data on ports 8790/8791. They never sign into ChatGPT or alter the learner's real repository.

Checks cover public API denial, crawlable HTML, sitemap links, curriculum integrity, repository binding, retained snapshots, malformed manifests, webhook signatures/replay, OAuth state/PKCE, failure retention, keyboard interactions, mobile overflow and automated accessibility. Type checking covers JavaScript/JSX with `checkJs`; strict TypeScript migration is not complete. Automated accessibility and dependency scans do not replace manual verification.

## Publication, rights and privacy

Public pages include the curriculum, phase challenges, learning method and about information; learner data never supplies public metadata. `PUBLIC_SITE_URL` sets canonical, sitemap and social URLs. No analytics is configured. Domain ownership, TLS, provider logs, final privacy/terms, curriculum/artwork rights and application licensing remain owner decisions. No application license has been chosen on your behalf. See [rights checklist](docs/LICENSING-AND-LEGAL.md), [notices](NOTICE.md), [audit](docs/REPOSITORY-AUDIT.md) and [deployment/backup procedures](docs/DEPLOYMENT.md).
