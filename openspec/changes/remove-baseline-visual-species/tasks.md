# Tasks

Test env file: `/tmp/mud-test.env` containing `MUD_TEST_SETTINGS=1`. Test
command prefix below: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Registry projection

- [x] 1.1 In `world/lore/monster_visuals.py` delete `BASELINE_VISUAL_ROWS`, the `is_baseline_art_only` field, its assignment in `adapt_combat_species`, and the baseline loop in `build_monster_visual_registry`; keep the reserved-key and duplicate checks over combat species. Verify `rg -n "BASELINE_VISUAL_ROWS|is_baseline_art_only" --type py` returns nothing outside `openspec/`.
- [x] 1.2 Rewrite `world/lore/tests/test_monster_visuals.py` baseline tests to assert, on a synthetic registry, that the visual registry equals the combat projection and that a non-species key is unregistered; retarget their `covers_requirement` decorators to the two ADDED `monster-visual-identity` requirement IDs (obtain IDs with `uv run --locked python -m tools.spec_traceability list` after a local sync or by slugging per `docs/development/spec-test-traceability.md`). Verify with `<prefix> world.lore.tests.test_monster_visuals`.

## 2. Provenance

- [x] 2.1 Remove `art_species_key` from `typeclasses/monsters.py`; make `world/art/presenter.py::_portrait_subject` read `species_key` only; delete `ART_SPECIES_PROVENANCE_ATTRIBUTE`, its `__all__` entry and elif arm in `world/art/official_refs.py`. Verify `rg -n "art_species_key|ART_SPECIES_PROVENANCE" --type py` returns nothing.
- [x] 2.2 Switch `world/art/tests/test_presenter.py`, `world/art/tests/test_species_portrait_identity.py`, `world/art/tests/test_official_refs.py`, `world/art/tests/test_gallery_seed.py` and `web/webclient/presentation/tests/test_art_panel.py` to synthetic species with `species_key`; replace the tier-built scenario test with "no species provenance → no reference, monster_anon", and retarget decorators of the removed `species-portrait-identity` requirement to its ADDED replacement. Verify with `<prefix> world.art.tests.test_presenter world.art.tests.test_species_portrait_identity world.art.tests.test_official_refs world.art.tests.test_gallery_seed web.webclient.presentation.tests.test_art_panel`.

## 3. Startup prune

- [x] 3.1 Add `delete_unregistered_monster_records()` to `world/art/gallery.py` (sole writer, under `gallery_lock`, returns count) and call it first in `world/art/service.py::prune_gallery_orphans`; extend `_gallery_job_is_unclaimable` for unregistered monster keys; add the classic-record phase that deletes unregistered monster classic records and unlinks their confined `output_identity`/`prior_output_identity` files (design D3). Verify the function exists and the order matches design D3 by reading the diff.
- [x] 3.2 Add prune tests in the existing prune test module (find it with `rg -ln "prune_gallery_orphans" world/art/tests`) covering the three ADDED scenarios with a synthetic registry, annotated with the requirement ID from `uv run --locked python -m tools.spec_traceability list`. Verify the module passes with `<prefix> <module label>`.

## 4. Gates

- [x] 4.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.observability_lint check` and `uv run --locked python -m tools.contract_gate --change remove-baseline-visual-species`; all pass.
- [x] 4.2 Run `openspec validate remove-baseline-visual-species --strict`; it passes.

## Workflow follow-up

- At archive sync, edit the Purpose of `openspec/specs/monster-visual-identity/spec.md` to drop "baseline wilderness monsters" wording.
