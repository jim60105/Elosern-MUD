## Why

Vitest and Node-gate tests hardcode fire_ball, basic_attack, healing_potion, elysa_snow, g_f_rank, and CJK labels as inline payload fixtures.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 22 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; webclient javascript behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 22 flagged test files under web/webclient-app/ and web/static/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (14 assertion-literal files, 8 setup-literal files).
- Replace every shipped-identifier literal and shipped display-prose literal in the
  migrated files with kit constants or locally built synthetic definitions; replace
  pinned data quantities with values derived from the patched synthetic catalogs.
- Where a shared helper is part of this area's debt, rewrite its builders on kit data so
  every borrower stops inheriting shipped ids.

- Restate converted assertions as the mechanics the owning OpenSpec requirement
  describes. A test that only echoes synthetic-fixture content is deepened or deleted;
  a deleted test's `@covers_requirement` annotation moves onto the replacement test.
  A deleted test MUST name the test that exercises the same production branch; a test
  that is the only evidence for a branch is retained, never deleted for gate
  cleanliness (the aggregate coverage gate stays the CI-owned floor).
- Remove this area's debt entries from `tools/test_data_freeze.json` and add the area
  closure test in `tests/test_data_independence_js_webclient.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `web/static/webclient/js/tests/art_panel.test.js` | B |
| `web/static/webclient/js/tests/character_menu.test.js` | B |
| `web/static/webclient/js/tests/combat_menu.test.js` | A |
| `web/static/webclient/js/tests/command_echo.test.js` | B |
| `web/static/webclient/js/tests/creation_menu.test.js` | A |
| `web/static/webclient/js/tests/exploration_menu.test.js` | A |
| `web/static/webclient/js/tests/hud_dock_menus.test.js` | A |
| `web/static/webclient/js/tests/protocol.test.js` | A |
| `web/static/webclient/js/tests/service_menu.test.js` | A |
| `web/webclient-app/tests/data/breakdown_rendering.test.js` | B |
| `web/webclient-app/tests/data/equipment_doll.test.js` | A |
| `web/webclient-app/tests/data/skill_book.test.js` | B |
| `web/webclient-app/tests/frame-resolvers.test.js` | A |
| `web/webclient-app/tests/overlays/creation_overlay.test.js` | A |
| `web/webclient-app/tests/overlays/lineage_panel.test.js` | B |
| `web/webclient-app/tests/overlays/title_codex_panel.test.js` | A |
| `web/webclient-app/tests/preserved_contract.test.js` | B |
| `web/webclient-app/tests/store/command_echo_surfaces.test.js` | A |
| `web/webclient-app/tests/store/declarative_surfaces.test.js` | A |
| `web/webclient-app/tests/store/store_dispatch_focus.test.js` | A |
| `web/webclient-app/tests/world/inventory_panel.test.js` | B |
| `web/webclient-app/tests/world/item_icons.test.js` | A |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Webclient JavaScript closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under web/webclient-app/ and web/static/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 22 listed test files plus the new closure test file `tests/test_data_independence_js_webclient.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
