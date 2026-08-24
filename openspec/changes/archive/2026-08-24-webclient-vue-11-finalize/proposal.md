## Why

This is change **D1**, the finalize step, of the Vue SPA WebClient migration (see the migration roadmap at
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`; depends on **C4**). After
C4 the client is fully Vue/store-bound but the retired legacy view files and their dead CSS still exist,
the docs and AGENTS still describe the old shell, and the source-of-truth design docs still say
"GoldenLayout." This change removes the dead code, updates the guidance, applies the D13 implementation
amendment to the source-of-truth design docs, finalizes the doc links, and locks the complete quality gate.

## What Changes

- **Delete the retired legacy view files** (the jQuery dock plugins, the goldenlayout plugin,
  `elosern_ui.js`) and their dead CSS; confirm nothing imports them. Keep the preserved `js/elosern/*`
  logic and `evennia.js`.
- **`AGENTS.md`:** add the frontend build/dev/test/Storybook commands, the Python-vs-npm split, and which
  JS gates (Node/Vitest/Storybook) apply.
- **Amend the source-of-truth design docs:** engine design doc D13 / webclient row and
  `webclient-ui-design.md` move the implementation from the GoldenLayout shell to a Vue 3 SPA on the same
  Evennia extension points (Telnet unchanged).
- **Finalize `docs/`:** link the 設計稿, the component showcase, and the frontend developer/architecture
  guide (the entries A1/A2 authored but left unlinked).
- **Lock the final quality gate** (the `webclient-browser-verification` mandatory-gate requirement at its
  final form: all Vue gates, the offline-degradation regression in the browser suite, exact-root and
  aggregate ≥ 80% branch, Codecov).

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-browser-verification`: the mandatory quality-gate requirement is set to its final, complete
  form for the Vue client.

## Impact

- **Removed:** the retired legacy view + dead CSS files.
- **Modified:** `AGENTS.md`, the engine design doc webclient row + `webclient-ui-design.md`,
  `docs/` links, `.github/workflows/quality-gate.yml` (final gate).
- **Preserved:** the preserved `js/elosern/*` logic, `evennia.js`, all protocol/dispatch requirements, and
  every existing gate (none are weakened).
