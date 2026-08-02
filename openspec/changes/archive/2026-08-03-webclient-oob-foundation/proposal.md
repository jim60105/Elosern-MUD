## Why

The project has a fully playable command path but no project-authored graphical state channel or desktop shell, so later combat, exploration, service, creation, and art panels have no secure foundation to build on. This change establishes that foundation now, independently of LLM and image services, while preserving normal WebClient text and Telnet play.

## What Changes

- Add a versioned WebSocket OOB protocol for full snapshots, panel replacements, action results, and safe recovery across reconnects and puppet changes.
- Add authenticated `ui_sync` and `ui_action` ingress with bounded exact envelopes, session-derived actor identity, stale-state rejection, request deduplication, and one mutation in flight per session.
- Add read-only presenter and allowlisted action-adapter registries, with a snapshot coordinator that isolates panel failures and a test-only adapter that proves dispatch without inventing a production game action.
- Add a server-authored compact status payload using canonical HP, MP, SP, condition, and combat-session state while never substituting display-only disguise values.
- Replace the stock browser arrangement with the approved desktop GoldenLayout shell, ink-night/vermilion theme, validated client state store, keyboard router, command drawer, required placeholders, and versioned local layout migration.
- Keep narrative output and ordinary commands on Evennia's existing text path; text remains usable when OOB initialization or an individual renderer fails, and Telnet behavior remains unchanged.
- Add locked Playwright development tooling, DOM-independent Node tests, an isolated Evennia browser harness, and mandatory quality-gate steps for Chromium, Node, and browser acceptance tests.
- Add no backward-compatibility adapter or persisted game-data migration; the project is unreleased and browser layout storage may reset when no known layout migration applies.

## Capabilities

### New Capabilities

- `webclient-oob-protocol`: Versioned snapshot/update envelopes, epoch and revision ordering, authenticated synchronization, presenter isolation, and degraded text-mode recovery.
- `webclient-action-dispatch`: Exact bounded UI action validation, allowlisted adapters, session identity, stale and duplicate handling, in-flight serialization, and deterministic-core mutation boundaries.
- `webclient-desktop-shell`: The desktop GoldenLayout surfaces, client state reduction, keyboard focus model, command drawer, layout migration, theme, accessibility, and text fallback.
- `webclient-status-presentation`: Read-only compact character status derived from canonical resources, active conditions, disguise state, and persistent combat-session metadata.
- `webclient-browser-verification`: Required Node and Playwright entry points, isolated deterministic server fixtures, supported viewport acceptance, and CI integration.

### Modified Capabilities

- `world-clock`: Add deterministic startup assurance and a no-create read accessor so presentation can display time without creating persistent state.

## Impact

- Adds server code under `server/conf/inputfuncs.py`, `web/webclient/presentation/`, and `web/webclient/actions/`, plus their package-local tests.
- Adds project-authored WebClient JavaScript, CSS, GoldenLayout configuration, templates or plugin hooks, local pinned browser runtime assets with license records, and DOM-independent JavaScript tests under `web/static/webclient/` and `web/templates/webclient/` as required by Evennia's extension points.
- Adds browser integration infrastructure under `web/tests/browser/` and extends `.github/workflows/quality-gate.yml` with mandatory Node and Playwright checks.
- Adds Playwright to the locked development dependency group through `uv add --dev playwright`, updating both `pyproject.toml` and `uv.lock`.
- Adds deterministic no-create read queries for status, per-rule combat-modifier matches, and the existing world clock without changing ownership or mutation contracts for traits, buffs, sexual state, creation state, combat sessions, or time.
- Establishes protocol and registry interfaces consumed by every later WebClient delivery unit; combat, map knowledge, exploration, services, creation forms, and art remain outside this change.
