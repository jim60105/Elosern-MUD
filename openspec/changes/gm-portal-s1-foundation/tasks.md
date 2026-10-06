## 1. Protected Django foundation

- [x] 1.1 Add `web/gm/`, mount it in `web/urls.py`, implement `gm_required` and `gm_path`, and register protected page/API fallback routes in safe order; verify resolver coverage and anonymous/player/Developer/superuser access tests for root, history paths, both endpoints, and unknown APIs.
- [x] 1.2 Add JSON response helpers and read-only session/health GET views using actual account/version/time and database reads; verify success payloads, 401/403/404 envelopes, database failure, unsupported-method rejection, and absence of production write/domain endpoints.
- [x] 1.3 Establish the shell CSRF cookie and Django POST convention without a production write endpoint, including narrowly scoped pre-CSRF access and GM API failure-envelope handling; verify a CSRF-enforced test-only POST returns anonymous 401 and unauthorized-account 403 before token validation, returns permitted-account 403 `csrf_failed` for missing/invalid tokens, emits one final-status request event per outcome, and accepts a valid token.
- [x] 1.4 Emit facade `gm_request` and `gm_denied` events at the final-response/access boundaries; verify successful, denied, not-found, and relevant middleware rejection outcomes have account/route/final-status context and no GM freeze-file entries.
- [x] 1.5 Add all GM backend test modules under `web/gm/tests/` using `EvenniaTest` and register each in `.github/evennia-shards.json`; verify shard registration covers every new module and the full account matrix.

## 2. Separate frontend build and dependency boundary

- [x] 2.1 Add Vue SPA entry sources in `web/admin-app/`, `vue-router` in the existing package/lock, `vite.gm.config.js`, and `build:gm`; verify the GM build produces stable `web/static/gm/dist/index.js` and `index.css` without changing the game Vite entry or deleting game output.
- [x] 2.2 Add `web/templates/gm/index.html` referencing Django static GM assets and supplying the configured login destination; verify protected shell responses reference the real built entries and issue a CSRF cookie.
- [x] 2.3 Add the dependency-free Node import-boundary test with path normalization and allowlisted token/font CSS; verify allowed fixtures pass and prohibited JS/Vue/CSS, re-export, dynamic literal, alias, and alternate-relative-path fixtures fail with source/dependency diagnostics.
- [x] 2.4 Integrate `build:gm` into existing CI/container frontend build steps and include GM output in image delivery; verify both bundles are source-built and served independently, preserving existing game build checks.

## 3. Operator components and functional overview

- [x] 3.1 Implement `GmShell`, `GmNav`, and `GmPageHeader` with account/logout, Traditional Chinese navigation, disabled future sections, and desktop-first usable narrow layout; verify shell Vitest tests cover active/disabled state and keyboard/pointer non-navigation, and logout uses the existing project flow.
- [x] 3.2 Implement `GmPanel`, `GmTable`, `GmEmpty`, `GmError`, and `GmStatusBadge` using tokens only; verify stories demonstrate content/empty/error/status states, status badges wrap `.status-marker`, identifiers remain monospace/verbatim, and neutral controls do not use destructive styling.
- [x] 3.3 Add `lib/api.js` as the sole same-origin fetch boundary with session credentials, POST CSRF headers, envelope validation, configured-login 401 handling, permission-route 403 handling, and code-based failures; verify Vitest covers success, CSRF, 401, 403, 404, network failure, and malformed JSON/envelope without a production write endpoint.
- [x] 3.4 Configure history routing with base `/gm/`, a real overview consuming both S1 APIs, and a permission-denied error view; verify router guards/history tests avoid redirect loops and undelivered sections have no placeholder routes/pages.
- [x] 3.5 Add stories for all eight `Gm*` components and extend Vitest/Storybook discovery and showcase coverage inventories; verify all GM coverage gates include them while preserving existing game stories/tests.

## 4. End-to-end acceptance and documentation

- [x] 4.1 Run registered GM Evennia tests, GM Vitest tests, dependency-boundary Node tests, and the showcase coverage gate after implementation integration; verify all delta-spec scenarios are covered and report actual results.
- [x] 4.2 Build both frontends and the container delivery path, then exercise authenticated shell/history loading, overview data, unauthorized API envelopes, and service-offline loading; verify stable asset delivery and that `/admin/`, game bundle behavior, and player/OOB contracts remain unchanged.
- [x] 4.3 Update existing project build/test/operator documentation or changelog with GM access, dual-build commands, coverage registration, and the S1-only boundary; verify documented commands match delivered scripts and no S2–S6 feature is represented as available.

> Archive follow-up (not an implementation task): when the delta specs sync into `openspec/specs/`, attach `@covers_requirement` annotations for the new `gm-portal-access-api` and `gm-portal-spa` requirement IDs to the `web/gm/tests/` tests and the `test_spa_evidence` bridge, following the precedent of earlier Vue evidence bridges.
