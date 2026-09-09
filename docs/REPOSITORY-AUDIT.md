# Repository audit — 8 September 2026

Baseline: commit 656071d. Audit performed before implementation. All tracked source, configuration, tests, curriculum records, branding documentation and setup documentation were inspected. Generated dependencies/build output are dependency artifacts, not application source. Baseline: 25 Python tests pass; no frontend test/lint/typecheck or CI commands exist.

| Area | Existing state | Priority / finding |
|---|---|---|
| Architecture | Implemented: React/Vite, same-origin FastAPI, single-user SQLite, hash routes | P0 risky: global repository and OAuth session are not tenant isolated. Do not host the personal API for anonymous visitors. |
| Curriculum | Implemented: 211 rows, 5 preparation rows, 206 learning projects, phases 0–20, individual P1–P10, prerequisites and examples | P1 manual: P75 lists itself as prerequisite. Preserve source pending author correction. |
| Curriculum loading | Partially implemented: repository manifest + packaged course; legacy three-project fallback | P1 broken: connecting a repository without curriculum manifest hides packaged course. Legacy compatibility must remain explicit, not silently replace curriculum. |
| Evidence | Implemented: exact commit, mapped BRIEF/main/README, AST checks, no code execution | P1 risky: current content overwritten on sync; only SHA events survive. Checks met is not runtime verification or mastery. |
| GitHub | Implemented: read-only requests, PKCE/state/cookie, signed webhook, duplicate delivery checks, failed sync retention | P0 public use: shared in-memory token and loopback trust are local-only. Real OAuth and webhook delivery need manual verification. |
| Public information | Missing: crawlable public landing, phase pages, learning method, entity description | P1: render packaged curriculum only, never progress/evidence or repository manifests. Avoid 211 thin duplicate pages. |
| SEO/social | Missing: canonical/descriptions/sitemap/robots/schema/OG; favicon implemented | P1: configurable production origin, server-rendered text, truthful schema, noindex private pages. |
| AEO/GEO | Partial: clear evidence philosophy, skill/roadmap UI | P2: direct visible answers and consistent learning-platform terminology; no ranking guarantees. |
| Security | Partial: TrustedHost, escaped React text, HMAC, path checks, local writes | P0: anonymous reads reveal personal state if exposed. P1: headers, request limits, origin defense, malformed manifest errors, bounded sync. |
| Accessibility | Partial: skip link, focus styling, labels, reduced motion | P1: unnamed progress, tiny text, navigation overflow, async stale responses, storage failures, overlay focus obscuring. Full assistive-technology audit not yet verified. |
| Performance | Partial: hashed assets/local fonts | P2: 936 KB sidebar logo; all font subsets; no budgets. Field CWV not available before launch. |
| Licensing/legal | Missing application license, NOTICE, deployment-specific policies | P0 manual: owner must confirm curriculum/reference artwork rights and select license. No license grant inferred. |
| Deployment | Local startup implemented | P0: no safe public mode. P1: container, environment contract, health, backup/restore, rollback and CI absent. |
| Content quality | Partial: grounded curriculum and Coach guide | P1: stale connected-repository README claim, invented fallback examples, missing setup manifest commands. Coach sharing and live access not verified. |
| Analytics | Absent | Keep absent; document a consent/retention decision before adding tracking. |

## Implementation boundary

Preserve the personal workspace and its curriculum. Add an explicit public curriculum-only mode; personal API stays local. This is preparation for a public information site, **not a claim that the current application is a secure multi-user hosted learning service**. Multi-user hosting still needs identity, per-user authorization, isolated persistence and a separate reviewed migration. No domain is assumed owned; no hosting, purchases, account changes or publication are performed by this audit.

Curriculum integrity baseline SHA-256: `36a5c42f700d328868c387593532bae165215874a9491c67affc04850d44586c`.

Public pages use source IDs, titles, order, prerequisites, concepts, instructions and examples unchanged. Preparation remains excluded from progress. Historical evidence remains separate. No curriculum edits are authorized solely to improve SEO.
