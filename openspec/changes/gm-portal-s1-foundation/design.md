## Context

See `proposal.md` for motivation and the two delta specs for behavior. The approved source is `docs/superpowers/specs/2026-10-06-gm-portal-design.md` §§3–5. The game SPA has a single-entry stylesheet build and frozen player contracts; Evennia supplies Django session authentication and its account permission API. The existing `world.observability` facade supplies `log_info(event, context=...)` and `log_warn(event, context=...)`. S1 introduces no domain model.

## Goals / Non-Goals

**Goals:** Establish one protected URL namespace, one JSON/fetch contract, and a separate reusable operator component layer. Make omissions in permission coverage and game-tree isolation fail automated gates.

**Non-Goals:** No S2–S6 feature API, mutation, authored-data editing, service probing, pagination consumer, audit storage, compatibility path, or migration. Do not modify player components, OOB, `.elosern-root`, or Django admin. Define transport extension points without implementing later consumers.

## Decisions

### 1. Plain Django app with centralized route protection

Mount `path("gm/", include("web.gm.urls"))` in `web/urls.py`; register every GM view through `gm_path()` in `web/gm/urls.py`. It applies `gm_required` from `web/gm/access.py` and exposes a marker preserved through wrapping for the recursive URL-resolver contract test. The account is Django's authenticated Evennia account; authorize with `check_permstring("Developer")`, retaining superuser admission, not `is_staff` as a substitute.

Order concrete API routes before a protected API-not-found fallback; handle both the exact API root and its descendants before the protected page-history catch-all. A path beginning `api/` must never reach the shell. Page denials use redirect/403 HTML; API denials use envelopes. This avoids scattering decorators and avoids a REST framework dependency.

### 2. Small envelope helper and bounded read-only endpoints

Use `web/gm/responses.py` for success/error JSON and matching statuses. Session returns `account_name`, `permission_level` (Developer or superuser), `server_time` (timezone-aware ISO 8601), and `game_version` from the existing project version source. Health performs a minimal database read and returns `django: "ok"` and `database: "readable"`; a database failure uses a non-2xx error envelope, not an invented healthy value. It does not inspect external services or persistent game resources.

Define cursor/limit and POST-only write conventions in the contract; there is no generic pagination implementation without a consumer. GET endpoints are read-only and reject unsupported methods using an error envelope. Shell delivery ensures the Django CSRF cookie exists. Test-only URL configuration can host a protected POST view to verify real CSRF rejection/admission without adding any production mutation endpoint. Missing/invalid tokens on authenticated permitted API POSTs return a 403 `csrf_failed` envelope, including middleware-originated rejections. A narrowly scoped GM access gate before CSRF view processing gives anonymous API requests their required 401 and unauthorized accounts their required 403; retain `gm_required` on every registered view and reuse the same access decision rather than duplicating permission policy. Adapt CSRF failure handling only for the GM API namespace, preserving the existing non-GM behavior. Keep REST API enablement false.

### 3. Request logging covers early denials and API fallback

Use facade calls from the GM boundary: `gm_denied` on all access refusals and `gm_request` once per API request after the final response status is known. Wrap access handling within the request logging boundary so early 401/403 responses and API misses are included. Ensure middleware-originated responses relevant to GM APIs are covered by a narrowly scoped response-logging hook if needed; do not log cookie/token contents. Account context is the account name or `anonymous`; route is the request path. No freeze-file entry and no audit model are needed.

### 4. Independent Vite output and shared tooling, not a shared runtime

Add `vite.gm.config.js` and `build:gm` in the existing frontend package. Use an independent root/entry in `web/admin-app/` and GM static base/output, stable entry `index.js` and stylesheet `index.css`; any additional chunks remain under the GM output. The output-cleaning boundary is only `web/static/gm/dist/`, never the game directory. `web/templates/gm/index.html` uses Django static URLs for the stable entries and supplies the configured login destination to the SPA, avoiding a hard-coded login URL.

Extend existing CI/container frontend build steps to run both builds and include both outputs. Reuse existing Vitest/Storybook tooling with GM include patterns and coverage registration, preserving game gates. Adding a second entry to the game Vite configuration is rejected because it violates its single-stylesheet invariant and runtime isolation.

### 5. Token-only components with a resolved-path import gate

Implement the eight `Gm*` components under `web/admin-app/components/`; use GM-local styles and the allowed `tokens.css`/`fonts*.css` imports. `GmShell` composes navigation, page header, and route content; `GmTable` presents rows, `GmEmpty` and `GmError` represent actual empty/error states, and `GmStatusBadge` wraps `.status-marker`. These are real reusable presentational components, not later-feature placeholders. Keep identifiers verbatim and monospace; neutral actions must not borrow destructive colors.

A dependency-free Node test recursively inspects JS/Vue/CSS import references in the GM tree, resolves relative and configured alias paths before applying the exact token/font allowlist, and includes positive/negative fixtures for alternate paths, Vue style sources, CSS imports, re-exports, and literal dynamic imports. Do not reuse the game component layer or its UI-scale assumptions. Wire GM story discovery and showcase coverage to all eight components rather than relying on game-only discovery globs.

### 6. Router and fetch ownership

Add `vue-router` and create history with base `/gm/`; reuse Pinia only if state genuinely needs it. The home route consumes session/health through the sole fetch boundary. Future navigation labels follow the approved layout and render disabled with `尚未開放`; no routes or placeholder pages are created for them. A real permission-denied route is an error state, not a future feature. Provide account/logout through the existing project's logout flow without creating a GM write endpoint.

`lib/api.js` owns same-origin credentials, CSRF header attachment on POST, envelope validation, and code-based failures. Router integration handles 403 `forbidden` without recursively fetching the session on the permission-denied route (a 403 `csrf_failed` is surfaced by code, not treated as a permission failure); 401 uses the server-supplied login destination and an encoded same-origin GM return path. Test 404, malformed JSON/envelope, and network failure separately. No retries, offline cache, or domain stores are added. S1 home is explicitly temporary: S2 will replace it and remove the skeleton health endpoint in its own change.

## Risks / Trade-offs

- API catch-all accidentally renders privileged HTML or misses protection → order API fallback before history and walk every resolved pattern in the coverage test.
- Early rejection bypasses request events → test 200, 401, 403, and 404 statuses and the final-response boundary.
- Shared tooling silently omits GM tests/stories → explicitly extend discovery and gate inventories; retain game coverage.
- Separate Vite cleaning removes the game bundle → assert output-directory separation and build both outputs together.
- A textual import scanner misses a dependency spelling → resolve paths and test JS, Vue, CSS, aliases, and alternative-relative-path fixtures; keep configuration explicit and dependency-free.
- The foundation spans backend/frontend/build files → keep implementation limited to the two GET APIs, eight presentational components, and a functioning overview; do not expand into roadmap features.

## Deployment and rollback

Build and ship GM sources and both asset bundles together; enable the mounted namespace only with its shell assets available. No database migration or data conversion is required in this pre-release project. Rollback removes the GM mount/application and build integration as one unit without altering player assets or persistent game state.
