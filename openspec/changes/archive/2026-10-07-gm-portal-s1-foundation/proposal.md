## Why

Operators need a Developer-only, out-of-character interface without exposing game internals through the immersive webclient. S1 establishes the isolated backend and frontend contracts that later GM capabilities can use safely.

## What Changes

- Add `web/gm/` with protected SPA routes, session and skeleton-health GET APIs, plain-Django JSON envelopes, and facade request/denial events.
- Add a separate Vue 3 application in `web/admin-app/`, history routing under `/gm/`, a shared fetch boundary, an operator home view, and eight token-based `Gm*` components.
- Build stable GM assets through `vite.gm.config.js` and `build:gm`; include that build in CI and the container image without changing the game Vite entry.
- Enforce the game-tree import allowlist with a dependency-free Node test; add Evennia, Vitest, and Storybook coverage and register backend modules in `.github/evennia-shards.json`.
- Define pagination and POST/CSRF conventions without adding a paginated or write endpoint.

## Capabilities

### New Capabilities
- `gm-portal-access-api`: Protected GM routing, session/health payloads, JSON transport conventions, and observability.
- `gm-portal-spa`: Isolated GM build, token boundary, navigation/component layer, API client, and coverage gates.

### Modified Capabilities
None. Existing player-facing contracts, OOB, Django admin, and game build behavior remain unchanged.

## Impact

Implementation touches `web/urls.py`, new `web/gm/`, `web/admin-app/`, `web/templates/gm/index.html`, frontend package/lock/configuration files, showcase coverage configuration, CI/container build integration, and `.github/evennia-shards.json`. Generated assets go to `web/static/gm/dist/`. Add `vue-router`; reuse existing Vue, Pinia, Vitest, Storybook, Django sessions/CSRF, and observability facade. Keep `REST_API_ENABLED=False`; add no model, migration, REST framework, audit store, or compatibility layer.

Scope is only §§3–5 of `docs/superpowers/specs/2026-10-06-gm-portal-design.md`. No dashboard/service probes, runtime inspection, authored-data browser, prompt reload, saves, or console APIs from S2–S6. Future sections are disabled navigation, not placeholder pages. This is one cohesive foundation change; implementation tasks do not create additional sub-projects.
