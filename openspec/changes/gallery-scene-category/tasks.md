# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Server

- [ ] 1.1 Apply design decisions 1, 2, 4 and the Python half of 3 and 5. Verify tests for the two category scenarios and three panel scenarios (synthetic archetypes, entries written through `world.rules.scene_visits.record_scene_entry`) pass in `test_gallery_categories.py` and the gallery presenter test module, decorated with their requirement IDs.
- [ ] 1.2 Apply design decision 6. Verify tests for the three management-actions scenarios pass in the gallery action test module.

## 2. Client mirror

- [ ] 2.1 Apply the JS half of decisions 3 and 5 in `web/static/webclient/js/elosern/protocol/panels/gallery.js` and add parity cases to `test_gallery_panel.py`. Verify `node --test web/static/webclient/js/tests/*.test.js` and `<prefix> web.webclient.presentation.tests.test_gallery_panel` pass.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change gallery-scene-category`; all pass.
- [ ] 3.2 Run `openspec validate gallery-scene-category --strict`; it passes.
