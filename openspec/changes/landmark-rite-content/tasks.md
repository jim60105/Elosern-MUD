# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
No test may assert authored prose, an archetype count, an option count or any authored value.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-content-model` is merged: `uv run --locked python -c "from world.lore.rites import install, CONTENT_PATH; from world.lore.rites.loader import load_rites"` exits 0. If not, stop and report.

## 2. Adoption

- [ ] 2.1 Add `load_published` to `world/lore/rites/__init__.py` per design D1 and its tests per design D6 (first bullet). Verify: the test prefix with `world.lore.tests.test_rite_content` passes.

## 3. Content

- [ ] 3.1 Create `world/lore/rites/content/landmark_rites.yaml` with the archetypes `spring`, `statue` and `megalith` per design D3 and D4 (two options each, `self` scenes, `watch: null`) and an empty `districts` mapping. Verify: `uv run --locked python -c "import yaml; d=yaml.safe_load(open('world/lore/rites/content/landmark_rites.yaml', encoding='utf-8')); assert all(len(a['options']) == 2 for a in d['archetypes'].values())"` exits 0.
- [ ] 3.2 Add the archetypes `tower` and `tree` the same way. Verify: the command of 3.1 exits 0.
- [ ] 3.3 Fill `districts` per design D3 for every shipped district. Create `world/lore/tests/test_rite_content_document.py` per design D6 (second bullet) and register it in `.github/evennia-shards.json` and `tools/test_data_freeze.json`. Verify: the test prefix with `world.lore.tests.test_rite_content_document` passes.
- [ ] 3.4 Write `docs/lore/landmark-rites-review.md` per design D5, reviewing every scene against design D4 and correcting the document where a rule fails. Verify: the document has one section per archetype and every option row is marked pass; the test of 3.3 still passes.

## 4. Startup

- [ ] 4.1 Add the `landmark_rites_adoption` startup step, its `STARTUP_STEP_ORDER` entry and the `_BODY_TARGETS` entry per design D2. Verify: the test prefix with `server.conf.tests.test_startup_observability` passes, and the test prefix with `tests.test_map_runtime_contract` passes (two commands).

## 5. Gates

- [ ] 5.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-content` and `openspec validate landmark-rite-content --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the ADDED requirement with the identifier printed by `uv run --locked python -m tools.spec_traceability list`.
