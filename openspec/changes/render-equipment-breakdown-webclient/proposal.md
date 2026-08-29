# Proposal: render-equipment-breakdown-webclient

## Why

P6 shipped the breakdown into the version-5 character payload, but the
player still cannot SEE why a number moved: the Vue `CharacterStatusDrawer`
renders only totals, the legacy v4 branch is still alive, and equipment rows
say nothing about what they do. This is P7, the final change of the
equipment-effects design (parent design §11): the breakdown UI — layer
chips per stat, adjustment text on equipment rows, effective exposure in
the intimate view — plus the v5 migration of stories, component tests, and
payload validators, and removal of the transitional v4 tolerance.

## What Changes

- `CharacterStatusDrawer` stat rows render `effective（分項）`: base line
  plus deterministic layer chips from the payload's `layers` (source-tinted
  skill／狀況／裝備 kinds, registry names only, server ordering preserved —
  the renderer never re-sorts or recomputes); gauge rows decompose the
  maximum; rows without layers render exactly as today.
- `EquipmentDoll` and `InventoryPanel` equipment rows render the payload's
  server-formatted `adjustment` text; intimate view shows the (already
  effective, P4) exposure value with its 聖袍 tooltip semantics untouched.
- Storybook fixtures/stories move to the v5 character payload (frozen
  component manifest unchanged — breakdown renders inside existing
  components, no new manifest entries); Vitest component suites cover
  chip rendering/ordering (ALL layers, no truncation), adjustment rows
  (inventory joins the server's character equipment rows on `item_key`),
  empty-layer equivalence, direct-render fallback defense, and the
  16-layer bound; `npm run build-storybook` + `npm run showcase-coverage`
  green.
- Traceability lands in the shipped evidence-test pattern: Python
  `run_npm` evidence tests (annotated with canonical IDs after sync)
  execute the new Vitest suites and the Storybook/coverage gates, mirroring
  `test_vue_showcase_data_evidence.py`.
- v4 retirement: the Vue app, the legacy client, AND the Python panel
  validator accept ONLY schema version 5 (P6's dual-version tolerance
  window closes); v4 fixtures and every v4 validator branch are deleted
  (unreleased, no compat).

No backward compatibility or migration work; no Python changes beyond the
v4-branch deletion in the `character` panel validator and its tests; no new
commands (command docs untouched, `tests/test_command_docs.py` green).

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `webclient-component-showcase`: ADDED requirement — v5 fixtures and
  breakdown-state stories for the manifest components that render character
  payload rows, coverage gate unchanged.
- `webclient-vue-application`: ADDED requirement — the character drawer
  renders payload-provided breakdown layers and equipment adjustment text
  exactly as ordered/formatted server-side, the intimate view shows the
  effective exposure value, and only schema version 5 is accepted.
- `webclient-exploration-menu`: REMOVED requirement — 「The legacy client
  tolerates the version-5 character payload」 was transitional ("until the
  Vue breakdown renderer lands"); this change IS that renderer, so the v4
  tolerance window closes and schema version 5 becomes the only accepted
  character payload version at every wire validator.

## Impact

- `web/webclient-app/components/CharacterStatusDrawer.vue` (layer chips),
  `EquipmentDoll.vue` + `InventoryPanel.vue` (adjustment rows), intimate
  section (exposure value already present — contract test pins it).
- `web/webclient-app/stories/fixtures.js` (v5 character payload fixture
  with layers + adjustments), breakdown-state stories for the three
  components; `component-manifest.json` UNCHANGED.
- `web/webclient-app/tests/`: Vitest cases (chip rendering/ordering/
  direct-render defense, adjustment text, no-layers equivalence, v5-only
  validation); deletion of v4 fixtures/validator branch (app + legacy
  `protocol.js`); legacy dependency-free Node-gate tests rewritten to
  v5-only (accept 5, reject 4) and run through
  `node --test web/static/webclient/js/tests/*.test.js`.
- `web/webclient/tests/`: new Python evidence tests (canonical-ID
  annotated) running the new Vitest family and the showcase gates as CI
  evidence.
- `web/webclient/presentation/character.py`: the transitional v4
  acceptance branch deleted (v5-only exact validator); its contract tests
  and `web/tests/browser/browser_helpers.py`'s v4 snapshot helper migrate
  to v5.
- `web/static/webclient/js/tests/protocol.test.js` +
  `character_menu.test.js`: P6 v4/5 tolerance tests rewritten v5-only.
- Gates: `npm test`, `npm run build-storybook`, `npm run showcase-coverage`;
  Python suites regression-run (plus the v4-deletion focused tests).
- Not affected: any `world/` code, payloads (P6 shipped them), commands.
