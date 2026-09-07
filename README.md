# Project Episteme

Episteme is a personal learning dashboard that reads project evidence from a GitHub repository. It combines the AI Automation course curriculum with each repository's mapped source files and README notes, then saves the exact synced commit in local SQLite storage.

The current workspace is connected to `razaele0003/python-practice`. Repository names are arbitrary; `.episteme/projects.json` controls which files belong to each project.

## Run on Windows

Requires Python 3.11+ and Node 22.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
npm run build
.\Start-Episteme.cmd
```

Open http://127.0.0.1:8766. Use **Connect and load** to bind a public GitHub repository, or configure GitHub sign-in to choose one from an account. Use **Sync repository** after pushing changes.

## Project pages

The packaged course catalog contains all 202 curriculum rows across Phases 0–20. Phase 0 is shown on the dashboard. The repository's original ten Python projects remain available as individual Practice archive pages alongside the curriculum's combined P1–P10 baseline assessment.

Every project page can show:

- the curriculum instructions and prerequisites;
- deterministic example input and expected output;
- the solution source saved from the connected GitHub commit;
- the project's README section or mapped README file;
- the evidence checks used for the progress state.

The learning interface separates six jobs: Dashboard shows what to do now, Roadmap explains the phase journey, Projects contains the build catalog, Skills summarizes repository evidence without claiming mastery, Portfolio shows only complete project evidence, and Sync history records technical snapshots. Project pages follow Mission → Why → Prerequisites → Build → Test → Review → Readiness.

Course content is stored in `backend/course_curriculum.json`. It can be regenerated from the source curriculum PDF with `scripts/import_curriculum_pdf.py` using the bundled PDF dependencies.

## Repository mapping

Add `.episteme/projects.json` to the connected repository. Every project must map one folder containing the same three required files: `BRIEF.md`, `main.py`, and `README.md`. Loose files and sections from the repository-level README do not count as project evidence.

```json
{
  "schema_version": 1,
  "projects": [
    {
      "project_id": "P0.1",
      "project_folder": "projects/P0.1"
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

This does not require a webhook. Manual sync is the intended local workflow. A webhook can automate the same operation only after the backend is hosted at a trusted HTTPS address; GitHub cannot deliver internet events to a loopback address such as `127.0.0.1`.

## Progress meaning

Progress records visible repository evidence. It does not claim code correctness or independent mastery. Historical Python files count as present when their source exists and parses. New curriculum projects remain not started until their source path is mapped and synced. Removing evidence removes that state on the next successful sync.

## GitHub sign-in

Manual public repository input works without credentials. For the repository picker, register a GitHub OAuth app with homepage `http://127.0.0.1:8766` and callback `http://127.0.0.1:8766/api/github/callback`, then set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in the backend environment and restart Episteme.

The OAuth flow requests `read:user`; it does not request repository write access. Tokens stay in backend memory for the local session. Keep secrets out of Git and out of the browser form.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run build
```

Tests cover repository binding, snapshot persistence, project detail content, curriculum loading, webhook validation, replay protection, failure recovery, and evidence removal.
