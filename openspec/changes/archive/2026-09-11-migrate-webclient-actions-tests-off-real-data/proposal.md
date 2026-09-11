## Why

Action-layer tests hardcode fire_ball, healing_potion, elysa_snow, and introductory_hunt in dispatched payloads and asserted results.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 12 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; webclient action behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 12 flagged test files under web/webclient/actions/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (7 assertion-literal files, 5 setup-literal files).
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
  closure test in `tests/test_data_independence_webclient_actions.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `web/webclient/actions/tests/test_character_actions.py` | B |
| `web/webclient/actions/tests/test_combat_actions.py` | A |
| `web/webclient/actions/tests/test_combat_dispatcher.py` | B |
| `web/webclient/actions/tests/test_creation_actions.py` | A |
| `web/webclient/actions/tests/test_exploration_actions.py` | A |
| `web/webclient/actions/tests/test_inventory_actions.py` | A |
| `web/webclient/actions/tests/test_node_ids.py` | B |
| `web/webclient/actions/tests/test_service_actions.py` | A |
| `web/webclient/actions/tests/test_service_validators.py` | A |
| `web/webclient/actions/tests/test_title_actions.py` | A |
| `web/webclient/tests/test_art_media.py` | B |
| `web/webclient/tests/test_webclient_contract.py` | B |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Webclient action closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under web/webclient/actions/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 12 listed test files plus the new closure test file `tests/test_data_independence_webclient_actions.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
