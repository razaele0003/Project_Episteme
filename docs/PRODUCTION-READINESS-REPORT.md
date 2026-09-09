# Episteme Production Readiness Report

Assessment date: 8 September 2026. Starting commit: `656071d`. Changes are local and reviewable; no domain, hosting account or public deployment was created.

## Overall result: NOT READY for a public hosted learning service

The existing single-user workspace is preserved and hardened. A separate **public curriculum-only mode** is implemented and locally validated. It deliberately denies learner APIs, OAuth and webhooks. This is useful deployment preparation, but does not fulfill hosted multi-user learning accounts. Legal/rights review, real hosting and operational validation remain launch blockers. Do not treat this report as a certification of security, accessibility, learning mastery or legal compliance.

## Architecture

**Implemented and tested:** existing React/Vite + FastAPI + SQLite retained. `backend/public_site.py` adds server-rendered public information without a frontend rebuild or learner-data dependency. `backend/security.py` denies every personal API in public mode, even when the caller is loopback behind a proxy. Local reads now require a local client and reject cross-origin browser access. `Dockerfile` defaults to public mode. Public mode requires an explicit HTTPS `PUBLIC_SITE_URL` and does not need SQLite or GitHub secrets.

Validation: public endpoint tests prove GET/POST/PUT cannot open private progress, project, connection, reset, OAuth or webhook routes, and that no database is created while crawling public pages. Existing workspace browser tests pass. Multi-user identity/tenant authorization: **NOT IMPLEMENTED**; do not deploy local mode publicly.

## Curriculum integrity

`backend/course_curriculum.json` is byte-for-byte unchanged. SHA-256: `36a5c42f700d328868c387593532bae165215874a9491c67affc04850d44586c`. All 211 rows, 5 preparation items, 206 learning projects, phases 0–20, IDs, order, concepts, instructions, examples and prerequisites are preserved. Existing skill mappings and evidence definitions remain in place. No thin replacement curriculum or invented SEO projects were added.

`backend/main.py` now accepts a projects-only mapping and keeps the packaged curriculum when a new empty repository is connected. Actual legacy three-exercise folders retain their prior checks. Invalid manifests fail explicitly instead of silently replacing the curriculum. Public phase pages render individual projects as anchors with their actual instructions and examples, including prerequisite links.

Validation: checksum, mapping-only and legacy tests pass. **Manual curriculum issue:** P75 lists P75 as its own prerequisite. This was not silently corrected. PDF provenance/authoritative source comparison beyond the committed curriculum is **NOT VERIFIED**.

## SEO

`backend/public_site.py` centralizes titles, descriptions, canonicals, robots, sitemap and social metadata. Public routes: homepage, curriculum index, 21 phase pages, learning method and about (25 URLs). Each returns complete HTML without JavaScript. The existing private hash workspace has `noindex,nofollow` in `index.html`, no public canonical, and no-store/noindex response headers. Private endpoints are access-denied, not merely hidden by robots.txt.

Validation: all sitemap URLs crawl successfully, unique paths, real HTTP 404s, public internal links resolve, canonical domain injection works, private database/API paths fail. Unknown phase paths do not become successful empty pages. Production-domain redirects, Search Console ownership, actual indexing and robots fetched by search engines: **NOT VERIFIED**.

## AEO

Public homepage and `/learning-method` provide direct visible answers: what Episteme does, how to complete a project, what sync checks, what Coach is, and why evidence differs from mastery. Content is grounded in implemented behavior. No fabricated testimonials, outcomes or FAQs were added. Validation: rendered HTML and browser navigation checks pass. Search answer inclusion: **NOT VERIFIED** and not guaranteed.

## GEO

Public descriptions consistently identify Episteme as an engineering learning platform and explain the public curriculum/local workspace distinction. Course, phase, project, evidence, runtime verification and mastery remain distinct. Curriculum relationships are linked through phase navigation and original prerequisite references. Model citation/discovery outcomes: **NOT VERIFIED** and not guaranteed.

## Structured data

Public documents include `WebSite`, `WebPage`, `BreadcrumbList`; curriculum has a `Course`, and phase pages have `LearningResource` relationships. Schema comes only from visible packaged content. No organization, instructor, price, rating, accreditation or certificate was invented. JSON is escaped and allowed by a per-document CSP hash.

Validation: JSON parses, expected entity types/URLs exist, HTML metadata and links pass automated checks. External rich-result/schema validator and eligibility for special search presentation: **NOT VERIFIED**. Schema presence does not guarantee rich results.

## Accessibility

`src/main.jsx`, `src/LearningPages.jsx`, `src/style.css` add named progress bars, current navigation state, form/error announcements, mobile navigation wrapping, readable small helper text, dark-panel contrast, storage failure handling, cancellation of stale project fetches and removal of invented example fallbacks. Coach focus/escape behavior is preserved. Public CSS supplies visible focus, skip link, responsive layout and meaningful heading hierarchy.

Validation: Playwright + axe-core found **zero violations in the selected WCAG A/AA rules** on five public views at 1280/375/320px, five local views, and the opened Coach panel. Keyboard opening/focus/Escape and mobile overflow checks pass. Screenshots were inspected for public desktop, public mobile phase and local mobile project. Full WCAG 2.2 AA conformance, screen-reader sessions, every route/state and every browser: **NOT VERIFIED**.

## Performance

Existing sidebar artwork remains the source; a 600px WebP derivative reduces the delivered logo from 936,591 to 11,352 bytes. Poppins imports use Latin subsets rather than every language subset. Public curriculum HTML uses no client JavaScript. Gzip middleware and immutable hashed-asset caching are configured. `scripts/check-budget.mjs` enforces JS/CSS/image budgets.

Validated final local build: JavaScript gzip **77,738 bytes**, CSS gzip **7,941 bytes**; budgets pass. `npm ci` and production build pass. Field LCP/INP/CLS, network-load tests, CDN caching and Lighthouse scores: **NOT VERIFIED**. Build size is not a Core Web Vitals measurement.

## Security

Changes: public/private mode gate; local Origin/Sec-Fetch-Site checks; TrustedHost; CSP/frame denial/nosniff/referrer/permissions headers; public HSTS; no exposed API docs; 8 KB local action bodies and 2 MB webhook bodies; process-wide 60-actions/minute guard; strict relative folder checks; bounded file count and 10 MB aggregate evidence; invalid-manifest rejection; safe conversation-link validation; popup opener cleared; environment/data excluded from container context. JSX and public HTML escape repository/content text. Learner code is never executed.

Validation: private endpoint denial, cross-origin and remote-client rejection, body limit, malformed manifest, path checks, HMAC/state/replay tests pass. `npm audit` and `pip-audit -r requirements.txt` found **no known vulnerabilities** at this run. This does not establish absence of vulnerabilities. Dedicated penetration testing, slow-client/edge protection, container vulnerability scan and real TLS configuration: **NOT VERIFIED**.

## GitHub integration

Existing read-only REST reader, local OAuth state/PKCE, public repository picker and webhook HMAC are retained. Mapping-only repositories now work with the packaged curriculum. Failed reads preserve saved progress. Tokens are backend-only and not included in public HTML or database evidence.

Validation: mocked OAuth state/PKCE/cookie/replay/token-expiry and repository-picker tests pass. A live read-only snapshot of `razaele0003/Project_Episteme` succeeded at commit `656071dfc0b41db10094e1d554fb5a0117d9a630`; it did not bind/sync or change the real workspace. Actual account login, private-repository scope, revocation, GitHub webhook delivery, custom GPT sharing and authenticated Coach review: **NOT VERIFIED**. Public-mode hosted login is deliberately unavailable.

## Data integrity

`evidence_history` stores immutable snapshots per repository binding and commit. Before replacing current content, the last available older snapshot is preserved. Failure remains retryable and cannot zero saved progress. Current completion continues to reflect current evidence; old evidence does not falsely complete a newer revision. The local `/api/history/{sha}` endpoint can retrieve retained content. Explicit reset also clears history.

Validation: new-commit preservation, failed-sync retention, connection switching and deletion recalculation tests pass. A copy of the actual SQLite database was backed up, integrity-checked, migrated and reopened using a temporary path; no live progress was reset. Earlier pre-upgrade SHA-only events cannot be reconstructed. Remote backup storage, scheduled retention and full disaster recovery: **NOT VERIFIED**.

## Licensing

`NOTICE.md` and `docs/LICENSING-AND-LEGAL.md` distinguish application, curriculum, learner files, evidence, dependencies/fonts and generated branding. Installed Poppins and Lucide license headers were inspected. No MIT or other application license was selected automatically. Owner confirmation of application licensing, curriculum redistribution rights and visual reference rights is still required. Full transitive distribution/license review: **NOT VERIFIED**.

## Legal

Public about content describes current privacy behavior and limitations; detailed policy/terms drafting inputs are in `docs/LICENSING-AND-LEGAL.md`. No fictitious operator, address, jurisdiction or provider is supplied. Final operator-specific privacy policy, terms, retention/contact process and legal review: **NOT COMPLETE**. No analytics was added.

## Deployment

`Dockerfile`, `.dockerignore`, `.env.example`, `docs/DEPLOYMENT.md` provide a single-service public deployment, explicit origin/host handling, health endpoint, HTTPS edge requirements, environment contract, backup/restore and rollback procedures. Existing local startup is preserved. No forced Vercel/PostgreSQL migration was made because the public read-only mode does not need it.

Container build/run: **NOT VERIFIED** (Docker unavailable on this machine). Real provider, domain ownership/DNS/TLS, cache behavior, host health probes and rollback: **NOT VERIFIED**. The container must be built and staging-tested before publishing.

## CI/CD

`.github/workflows/ci.yml` installs pinned/locked dependencies and runs frontend lint/checkJs, Python lint/tests, build, size budgets, vulnerability scans and browser tests, with read-only repository permissions and failure-only browser artifacts. It does not deploy automatically. `eslint.config.js`, `tsconfig.json`, `pyproject.toml` and `playwright.config.js` make checks reproducible.

Validation: corresponding local checks pass. Hosted GitHub Actions execution: **NOT VERIFIED** (changes have not been pushed). Strict TypeScript conversion is not complete; checkJs is enabled across the existing frontend with non-strict inference. Playwright Chromium download timed out locally; installed Chrome was used successfully via `PLAYWRIGHT_CHANNEL=chrome`.

## Testing

| Check | Result |
|---|---|
| Baseline Python tests | 25 passed before changes |
| Expanded Python tests | 45 passed |
| Frontend lint + checkJs | Passed |
| Python Ruff F/E9 checks | Passed |
| Reproducible npm install / production build | Passed |
| Asset budgets | Passed |
| npm/pip vulnerability scans | No known vulnerabilities reported |
| Browser suites | 4 passed, using installed Chrome |
| Public HTML without JavaScript | Passed |
| Sitemap / internal links / private boundaries | Passed |
| Database copy migration / integrity / reopen | Passed |
| Live public GitHub read | Passed, no workspace mutation |
| Docker / actual host / authenticated integrations | NOT VERIFIED |

Two upstream Python test-client deprecation warnings remain (httpx transition and AnyIO alias). They do not fail the tests; dependency upgrades should be assessed separately rather than suppressing them.

## Remaining P0 / P1 / P2 issues

**P0 — blockers:** hosted learning accounts require identity and tenant isolation; application/curriculum/artwork rights need owner decisions; actual deployment/container/domain/TLS and operator-specific legal policies require verification before public launch.

**P1 — before launch:** run CI on GitHub and staging container smoke; verify OAuth/private repository/revocation and Coach access for the intended audience if offered; resolve P75 prerequisite with the curriculum author; confirm provider log retention/contact/deletion policy; verify external social previews and schema against the real domain.

**P2 — recommended:** independent security review, manual assistive-technology testing across all workspace states, strict API/frontend typing, field performance measurement and backup retention automation after a host is selected. A public learner portfolio needs explicit consent and separate public/private data design; it is not enabled here.

## Manual actions

1. Decide whether the first release is the public curriculum plus local workspace, or a hosted multi-user service. The latter still requires implementation work.
2. Confirm curriculum/reference-artwork rights and select separate software/content/brand terms.
3. Select the actual domain/provider; set `PUBLIC_SITE_URL`, complete operator-specific policies, build the container and verify staging.
4. Run the supplied CI and domain checks, then verify real account integrations only where they will be offered.
5. Submit the sitemap after domain verification and measure real performance after launch. No ranking or mastery guarantee is implied.

## Reference guidance

- [Google Search Central: developer SEO](https://developers.google.com/search/docs/fundamentals/get-started-developers) and [robots metadata](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag): crawlable public HTML and private indexing restrictions.
- [OWASP CSP guidance](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html) and [HTTP headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html): defense-in-depth response headers.
- [W3C focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum): keyboard visibility verification.
- [Choose a License: no license](https://choosealicense.com/no-permission/): do not infer a reuse grant from a public repository.
