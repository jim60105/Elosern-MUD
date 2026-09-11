## Why

Director/narrator/service tests embed capital_altoria, guild_branch_altoria, basic_attack, fionnen, and CJK persona labels inside prompt/proposal fixtures; a few top-level contract tests compare docs against data literals.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 17 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; ai, server, and top-level behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 17 flagged test files under world/ai/, server/conf/tests/, world/observability/, tests/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (9 assertion-literal files, 8 setup-literal files).
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
  closure test in `tests/test_data_independence_ai_server.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `server/conf/tests/test_ai_director_service.py` | B |
| `server/conf/tests/test_option_proposal_service.py` | B |
| `server/conf/tests/test_scene_flavor_service.py` | B |
| `server/conf/tests/test_ui_action_integration.py` | B |
| `tests/test_creation_parity_contract.py` | A |
| `tests/test_quality_gate_contract.py` | A |
| `world/ai/tests/_director_helpers.py` | B |
| `world/ai/tests/test_action_options_layer.py` | A |
| `world/ai/tests/test_action_options_schema.py` | B |
| `world/ai/tests/test_character_creation.py` | A |
| `world/ai/tests/test_narrator.py` | A |
| `world/ai/tests/test_npc_dialogue_retry.py` | B |
| `world/ai/tests/test_scenario_director_prompts.py` | A |
| `world/ai/tests/test_scenario_director_proposals.py` | A |
| `world/ai/tests/test_scenario_director_registration.py` | A |
| `world/ai/tests/test_scenario_director_validation.py` | A |
| `world/ai/tests/test_title_nomination.py` | B |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the AI, server, and top-level closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under world/ai/, server/conf/tests/, world/observability/, tests/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 17 listed test files plus the new closure test file `tests/test_data_independence_ai_server.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
