## Why

Presentation tests hardcode item/skill/preset keys and CJK labels, and five files pin data-derived quantities (presets == 8, profiles == 15, stock == 12, categories == 8, affordance vocabulary == 300) that break on any content change.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 18 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; webclient presentation behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 18 flagged test files under web/webclient/presentation/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (7 assertion-literal files, 6 setup-literal files, 5 quantity-pinned files).
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
  closure test in `tests/test_data_independence_webclient_presentation.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `web/webclient/presentation/tests/test_affordances.py` | A |
| `web/webclient/presentation/tests/test_art_panel.py` | A |
| `web/webclient/presentation/tests/test_art_push.py` | B |
| `web/webclient/presentation/tests/test_character_panel.py` | A |
| `web/webclient/presentation/tests/test_combat_panel.py` | S |
| `web/webclient/presentation/tests/test_creation_panel.py` | S |
| `web/webclient/presentation/tests/test_dialogue_panel.py` | B |
| `web/webclient/presentation/tests/test_exploration_panel.py` | A |
| `web/webclient/presentation/tests/test_lineage_panel.py` | B |
| `web/webclient/presentation/tests/test_local_map.py` | S |
| `web/webclient/presentation/tests/test_lore_codex_panel.py` | S |
| `web/webclient/presentation/tests/test_objectives_panel.py` | B |
| `web/webclient/presentation/tests/test_party_panel.py` | B |
| `web/webclient/presentation/tests/test_possession_presentation.py` | A |
| `web/webclient/presentation/tests/test_presentation_context.py` | A |
| `web/webclient/presentation/tests/test_quest_log_panel.py` | B |
| `web/webclient/presentation/tests/test_services_panel.py` | A |
| `web/webclient/presentation/tests/test_title_codex_panel.py` | S |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Webclient presentation closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under web/webclient/presentation/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 18 listed test files plus the new closure test file `tests/test_data_independence_webclient_presentation.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
