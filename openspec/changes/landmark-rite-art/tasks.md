# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Never commit a placeholder, reused or copied image.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-panel` and `landmark-rite-content-completion` are merged: `uv run --locked python -c "from web.webclient.presentation.rite import rite_presenter; from world.lore.rites import load_published"` exits 0, and `ls world/lore/rites/content/landmark_rites.yaml` lists the file. If not, stop and report.
- [ ] 1.2 Confirm the image generation service the existing scene packs were produced with is reachable (the configuration `world.art.sd_worker.SDWebUIClient` reads). If it is not, stop and report with `Needs: the maintainer's image generation service`.

## 2. Subjects and illustrations

- [ ] 2.1 Generate and commit the ten illustrations and provenance records per design D2. Verify: `ls web/static/art/scenes/rite_*.webp` lists ten files and `ls web/static/art/scenes/rite_*.provenance.json` lists ten files.
- [ ] 2.2 Apply design D1 to `world/lore/scene_archetypes.py` and `world/art/scene_definitions.py`. Create `world/art/tests/test_bundled_rite_art.py` and update `world/art/tests/test_bundled_scenes.py` per design D6; register the new module in `.github/evennia-shards.json` and `tools/test_data_freeze.json`. Verify: the test prefix passes for each of `world.art.tests.test_bundled_rite_art`, `world.art.tests.test_bundled_scenes`, `world.lore.tests.test_scene_archetypes`, `world.lore.tests.test_registry_index_contract`, `world.maps.tests.test_static_map_references` (five commands).
- [ ] 2.3 Regenerate `content/map-reference-context.json` per design D5. Verify: `grep -c rite_spring content/map-reference-context.json` prints at least 1, and the contract test that checks the file's freshness (find it with `grep -ln map-reference-context tests/*.py`) passes when run with `uv run --locked python -m unittest <module>`.

## 3. Adoption and panel

- [ ] 3.1 Apply design D3 with its tests of design D6. Verify: the test prefix passes for `world.lore.tests.test_rite_content` and for `world.lore.tests.test_rite_content_document` (two commands).
- [ ] 3.2 Apply design D4 with its tests of design D6. Verify: the test prefix with `web.webclient.presentation.tests.test_rite_panel` passes.

## 4. Existing flows and gates

- [ ] 4.1 Run the test prefix with `world.art.tests.test_scene_resolution`, and the test prefix with `commands.tests.test_art` (two commands). Verify: each passes.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-art` and `openspec validate landmark-rite-art --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
