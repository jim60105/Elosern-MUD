## Why

The suite-wide seed.py poisons every browser test with real ids/presets, and individual browser tests assert CJK labels and ids derived from shipped data.

The browser suite is process-isolated: the managed seed (`python -m
web.tests.browser.seed`) and the managed Evennia server are separate processes that
mirror shipped catalogs into a private SQLite DB at bootstrap, so the in-process
`synthetic_registries()` patch cannot reach them. This change owns the process-level
seam: it activates the kit's `install_synthetic_catalogs()` bootstrap (kit design D2b)
from `web/tests/browser/browser_settings.py` under the kit's opt-in flag, so the seed,
the server, and their startup mirroring resolve synthetic catalogs end to end.

The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 19 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; managed-browser behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 19 flagged test files under web/tests/browser/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (9 assertion-literal files, 8 setup-literal files, 2 quantity-pinned files).
- Replace every shipped-identifier literal and shipped display-prose literal in the
  migrated files with kit constants or locally built synthetic definitions; replace
  pinned data quantities with values derived from the patched synthetic catalogs.
- Where a shared helper is part of this area's debt, rewrite its builders on kit data so
  every borrower stops inheriting shipped ids.
- Wire the kit's process-scoped install into the browser settings module and add a seed
  smoke test proving one journey resolves a `t_`-prefixed key through the running
  server.
- Restate converted assertions as the mechanics the owning OpenSpec requirement
  describes. A test that only echoes synthetic-fixture content is deepened or deleted;
  a deleted test's `@covers_requirement` annotation moves onto the replacement test.
  A deleted test MUST name the test that exercises the same production branch; a test
  that is the only evidence for a branch is retained, never deleted for gate
  cleanliness (the aggregate coverage gate stays the CI-owned floor).
- Remove this area's debt entries from `tools/test_data_freeze.json` and add the area
  closure test in `tests/test_data_independence_browser.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `web/tests/browser/browser_helpers.py` | B |
| `web/tests/browser/browser_settings.py` | B |
| `web/tests/browser/seed.py` | B |
| `web/tests/browser/test_browser_art.py` | A |
| `web/tests/browser/test_browser_combat.py` | A |
| `web/tests/browser/test_browser_combat_rejection.py` | B |
| `web/tests/browser/test_browser_contextual_hud.py` | A |
| `web/tests/browser/test_browser_creation.py` | S |
| `web/tests/browser/test_browser_exploration.py` | S |
| `web/tests/browser/test_browser_input_narrative.py` | B |
| `web/tests/browser/test_browser_inventory_actions.py` | A |
| `web/tests/browser/test_browser_inventory_grid.py` | A |
| `web/tests/browser/test_browser_lineage.py` | B |
| `web/tests/browser/test_browser_local_map.py` | A |
| `web/tests/browser/test_browser_pointer.py` | B |
| `web/tests/browser/test_browser_services.py` | A |
| `web/tests/browser/test_browser_shell.py` | A |
| `web/tests/browser/test_browser_title_codex.py` | A |
| `web/tests/browser/test_vue_foundation.py` | B |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Managed-browser closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under web/tests/browser/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 19 listed test files plus the new closure test file `tests/test_data_independence_browser.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
