# Tasks

Every task below was implemented and verified on `master` in commit `63993c5b`
(`feat(art): render persona appearance as label-free visual prose`); the boxes record that state.

## 1. Race label resolution

- [x] 1.1 Resolve the prompt-facing race label to the parent RACE display name in `world/art/subjects.py::_race_label` (subrace → `SUBRACE_REGISTRY[key].race_key` → `RACE_REGISTRY[...].display_name_zh`; bare race key resolves directly; unregistered key falls back to the stored string as before), verified by the re-pinned `world/art/tests/test_subjects.py` composition tests whose synthetic race label is sourced via `SYNTH_RACES[SYNTH_SUBRACES[k].race_key].display_name_zh` with `synthetic_registries` scopes widened with `"races"`
- [x] 1.2 Re-pin the degrade and verbatim-shipment expectations to the parent-race label in `world/prompts/tests/test_degrade.py` and `world/prompts/tests/test_verbatim_shipment.py`, verified by both modules passing with the `"races"` registry scope

## 2. Label-free visual-only appearance fragment

- [x] 2.1 Filter the persona `appearance` contribution to `APPEARANCE_PROMPT_SUBKEYS = ("style", "overview")` in declared `_SUBKEY_ORDER` order in `world/art/subjects.py::_appearance_fragment` — whole-string compact NPC-card appearance passes through, other shapes contribute nothing — verified by `test_full_persona_contributes_only_image_usable_appearance_subkeys` (kept values present; `height`/`weight`/`measurement`/`attire`/`feature` values absent) and `test_body_measure_and_attire_subkeys_never_reach_the_prompt` (body/attire-only appearance yields exactly the bare base sentence) in `world/art/tests/test_subjects.py`
- [x] 2.2 Strip the `外觀` section label (imported `_FIELD_LABELS["appearance"]`) and every sub-key label while keeping the store's shipped per-field cap (each kept value flattened through `PersonaStore` and prefix-stripped), verified by the byte-exact determinism test (`base sentence\nstyle value\noverview value`, no labels) and by `world/art/tests/test_gallery_prompt.py` composition asserting `quiet eyes` (no `外觀：`/`feature：` framing) renders before the equipment and custom slots

## 3. Integration verification

- [x] 3.1 Run the focused suites green: `world.art.tests.test_subjects`, `world.art.tests.test_gallery_prompt`, `world.prompts.tests.test_degrade`, `world.prompts.tests.test_verbatim_shipment` — 78 tests pass
- [x] 3.2 Run `tools.contract_gate` green: traceability (2132/2132 requirements covered), observability freeze, test-data, manifests, and contracts all pass; rubber-duck review raised 0 findings; no docs change needed (`docs/gm/prompts.md` slot description remains accurate, no player command surface change)

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied; sync the `art-subject-model` delta into the main spec.
