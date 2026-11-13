# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Source and projection

- [x] 1.1 Implement design D1 in `web/webclient/presentation/gallery_categories.py` and update the existing category-order test for the modified scenario. Verify `<prefix> web.webclient.presentation.tests.test_gallery_categories` passes with new tests for the four ADDED people scenarios (synthetic named NPCs written through `world.rules.met_people.record_person_interaction`), decorated with the requirement IDs. The four ADDED tests stay unannotated until archive sync indexes their requirement IDs; the modified requirement keeps its existing annotation.
- [x] 1.2 Implement design D2–D3 in `gallery_selection.py` and `gallery.py`. Verify the presenter test module (`rg -ln "def test" web/webclient/presentation/tests | rg gallery`) gains passing tests for the three `webclient-gallery-panel` scenarios, each built payload passing `validate_gallery`.

## 2. Gates

- [x] 2.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change gallery-people-category`; all pass.
- [x] 2.2 Run `openspec validate gallery-people-category --strict`; it passes.
