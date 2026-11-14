# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Tests use synthetic documents only. Do not create `world/lore/rites/content/`.

## 1. Model and loader

- [ ] 1.1 Create `world/lore/rites/shape.py` per design D1 and `world/lore/rites/__init__.py` per design D4. Verify: `uv run --locked python -c "from world.lore.rites import current, install, installed, RitesNotLoaded, CONTENT_PATH; from world.lore.rites.shape import RiteSnapshot, art_subject_key; assert art_subject_key('spring') == 'rite_spring'"` exits 0.
- [ ] 1.2 Create `world/lore/rites/loader.py` per design D2 and D3. Create `world/lore/tests/test_rite_content.py` per design D5 and register it in `.github/evennia-shards.json` in the shard that holds `world.lore.tests.test_map_districts`. Verify: the test prefix with `world.lore.tests.test_rite_content` passes.

## 2. Gates

- [ ] 2.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-content-model` and `openspec validate landmark-rite-content-model --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
