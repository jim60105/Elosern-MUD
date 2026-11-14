# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Tests use synthetic districts, a synthetic rite snapshot and synthetic text only.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-content-model` is merged: `uv run --locked python -c "from world.lore.rites import current, installed; from world.lore.rites.shape import RiteSnapshot, RiteArchetype, RiteOption"` exits 0. If not, stop and report.

## 2. Record

- [x] 2.1 Create `world/rules/landmark_rite_record.py` per design D2 and `world/rules/tests/test_landmark_rite_record.py` per design D5; register the test module in `.github/evennia-shards.json`. Verify: the test prefix with `world.rules.tests.test_landmark_rite_record` passes.

## 3. Settlement

- [x] 3.1 Add `node_id_for` to `world/rules/map_knowledge.py` per design D1. Verify: `uv run --locked python -c "from world.rules.map_knowledge import node_id_for; assert node_id_for(None) is None"` exits 0.
- [x] 3.2 Create `world/rules/landmark_rites.py` with `RiteRefused`, `REFUSAL_MESSAGES`, the three dataclasses, `record_owner_for`, `rite_site_for`, `eligible_performers` and `preflight` per design D3. Create `world/rules/tests/test_landmark_rites.py` with its fixture and the site, performer and refusal tests of design D5; register it in `.github/evennia-shards.json`. Verify: the test prefix with `world.rules.tests.test_landmark_rites` passes.
- [x] 3.3 Add `perform_rite` per design D3 with the committed, repeat, companion, rollback, replay and event tests of design D5. Verify: the same test label passes. If the committed-rite test shows the climax does not end within 120 seconds, apply the last Non-Goal of the design and report.
- [x] 3.4 Add the three catalog rows per design D4. Verify: `grep -c landmark_rite_ docs/superpowers/specs/2026-09-02-observability-logging-design.md` prints at least 3.

## 4. Existing flows and gates

- [x] 4.1 Run, one command per label: `world.rules.tests.test_party_time_settlement`, `world.rules.tests.test_skip_commands`, `typeclasses.tests.test_map_discovery`. Verify: each passes.
- [x] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-settlement` and `openspec validate landmark-rite-settlement --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the nine ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
