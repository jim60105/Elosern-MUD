## 1. Relocate the freeform-scale helper into `world/rules/progression.py`

- [ ] 1.1 `grep -rn _freeform_scales_for_skill` to find every reference (definition + call site + tests) — confirm the only definition and call site are both in `world/rules/combat_view.py`
- [ ] 1.2 In `world/rules/progression.py`, add `from world.skills.cost_tiers import is_freeform_eligible` to its existing `from world.skills.cost_tiers import spell_tier_for` import line, then add a new public function `freeform_scale_entries_for(actor, skill)` with the exact body of the old `_freeform_scales_for_skill` (unchanged logic — a pure relocation + rename)
- [ ] 1.3 In `world/rules/combat_view.py`: remove the local `_freeform_scales_for_skill` definition and its four now-unused imports (`FREEFORM_CAST_SCALES`, `freeform_scales_for`, `scaled_mp_cost` from `.progression`, and `is_freeform_eligible` from `world.skills.cost_tiers`); import `freeform_scale_entries_for` from `world.rules.progression` instead; update `_build_skills`'s one call site to the new name
- [ ] 1.4 Run `world/rules/tests/` (the combat/skills-family modules) to confirm the move is behavior-preserving; add one test case for `freeform_scale_entries_for` in its new home if the moved function has no direct unit test today (only indirect coverage via `_build_skills`)

## 2. Make `combat_panel.py`'s skill-descriptor validators public and shared

- [ ] 2.1 Rename `combat_panel.py`'s `_validate_freeform_scales` to public `validate_freeform_scales` (no behavior change); update its one internal call site in `_validate_skill`
- [ ] 2.2 Confirm `TARGET_SPECS` and `MAX_COST_KEYS` are already public (no leading underscore) — no rename needed, just import them from `character.py`
- [ ] 2.3 `grep -rn _validate_freeform_scales` to confirm no other caller is missed by the rename

## 3. Split the character-panel skill row validators

- [ ] 3.1 In `web/webclient/presentation/character.py`, import `TARGET_SPECS`, `MAX_COST_KEYS`, and `validate_freeform_scales` from `web.webclient.presentation.combat_panel`
- [ ] 3.2 Add `_validate_active_skill_row(value)`: `_require_exact_fields(value, "active skill row", {"key","label"}, {"cost":"optional","target_spec":"optional","usable_out_of_combat":"optional","freeform_scales":"optional"})`; validate `cost` with the same bounded-identifier-key/non-negative-int check `combat_panel.py`'s `_validate_skill` uses (bounded by `MAX_COST_KEYS`); validate `target_spec` against `TARGET_SPECS` when present; validate `usable_out_of_combat` with `_require_bool` when present; validate `freeform_scales` via the imported `validate_freeform_scales(value.get("freeform_scales"), cost.get("mp"))` when present (require `cost` present with an `mp` entry if `freeform_scales` is present, mirroring `combat_panel.py`'s "a skill without an mp cost cannot carry freeform_scales" rule)
- [ ] 3.3 Leave `_validate_passive_row` unchanged (`{key, label}` only)
- [ ] 3.4 Update `_validate_character_skill_group` to take a `row_validator` parameter (defaulting to none of the callers changing behavior for passives); update `_validate_character_category_group` to accept and thread the same parameter; update BOTH call sites in `validate_character` (the `actives` list comprehension and the `passives` list comprehension) to pass `_validate_active_skill_row` and `_validate_passive_row` respectively
- [ ] 3.5 Confirm `_flattened_skill_count` and the `MAX_ACTIVE_ROWS`/`MAX_PASSIVE_ROWS` bounds checks in `validate_character` are unaffected (they count rows, not fields)

## 4. Serialize the enriched active rows

- [ ] 4.1 Rename `_serialize_skill_groups` to `_serialize_passive_skill_groups` (unchanged body) for the `passives` field
- [ ] 4.2 Add `_serialize_active_skill_groups(keys, actor)`: same `group_skill_keys` traversal, but for each row look up `SKILL_REGISTRY.get(row.key)`; when found, attach `cost` (`dict(skill.cost)`), `target_spec` (`skill.target_spec.value`), `usable_out_of_combat` (`skill.usable_out_of_combat`), and `freeform_scales` (from `freeform_scale_entries_for(actor, skill)` as `[{"scale": s, "label": l, "mp_cost": c} for s, l, c in ...]`, included only when non-empty); when not found, emit `{key, label}` only
- [ ] 4.3 Update `_serialize` to call `_serialize_active_skill_groups(model.active_keys, actor)` for `"actives"` and `_serialize_passive_skill_groups(model.passive_keys)` for `"passives"`; thread `actor` through from `character_presenter` (already in scope there) into `_serialize`

## 4a. Update the client-side JS schema mirror (`protocol.js`) — required, not optional

- [ ] 4a.1 In `web/static/webclient/js/elosern/protocol.js`, add `validateCharacterActiveSkillRow(value)` mirroring `_validate_active_skill_row`: same required (`key`,`label`) and optional (`cost`,`target_spec`,`usable_out_of_combat`,`freeform_scales`) fields, reusing this file's existing `freeform_scales entry` validator (line ~750, `["scale","label","mp_cost"]`) if its shape matches, or extending it to the same strict-ascending/canonical-label/scaled-mp-cost checks `combat_panel.py`'s `validate_freeform_scales` performs — check whether protocol.js already has a combat-skill cost/target_spec validator to reuse the same way the Python side reuses `combat_panel.py`'s
- [ ] 4a.2 Update `validateCharacterSkillGroup` to take a row-validator argument (or split into `validateCharacterActiveSkillGroup`/`validateCharacterPassiveSkillGroup`); update `validateCharacterCategoryGroup` the same way; update `validateCharacterPanel`'s two call sites (`payload.actives.forEach(...)` and `payload.passives.forEach(...)`) to pass the correct validator, mirroring `character.py`'s two `validate_character` call sites exactly
- [ ] 4a.3 Confirm `web/webclient-app/lib/protocol.js` (the ESM re-export consumed by `stores/elosern.js`) picks up the change with no separate edit (it should be a thin re-export — verify, don't assume)

## 5. Render the new field in SkillBook

- [ ] 5.1 In `web/webclient-app/components/SkillBook.vue`, add a `usable_out_of_combat` check and render a `combat` pill (`data-testid="skill-book__ooc"`) beside the skill name when `row.usable_out_of_combat === true`; style it as a small bordered pill consistent with the existing cost/target/cast cell tokens (no new color token needed — reuse `--paper-500`/`var(--line)`)
- [ ] 5.2 Update the file's header comment to state the character payload's active rows are now enriched with cost/target/OOC/freeform data by the presenter whenever the registry resolves the key (no longer purely speculative optionality)

## 6. Fixtures, stories, and tests

- [ ] 6.1 Add an explicit `usable_out_of_combat: true` field to at least one row in `web/webclient-app/stories/fixtures.js`'s `SKILLS_SLICE_SAMPLE` (e.g. `firebolt`, matching the design draft's own `火矢 combat` example) so `Data/SkillBook`'s `ActiveTab` story proves the pill renders offline
- [ ] 6.2 Add/extend `web/webclient-app/tests/data/skill_book.test.js` to assert the `combat` pill renders exactly when `usable_out_of_combat` is `true` and is absent otherwise (including the unregistered-key fallback row, which has neither the field nor the pill)
- [ ] 6.3 Add `web/webclient/presentation/tests/test_character_panel.py` cases: an active row with a registered key gets `cost`/`target_spec`/`usable_out_of_combat` (and `freeform_scales` when eligible); a passive row stays `{key, label}`; an active row with an unregistered key stays `{key, label}`; a worst-case 32-active-row payload (every row carrying cost + target_spec + usable_out_of_combat + a full freeform_scales set) stays under `MAX_CANONICAL_JSON_BYTES`
- [ ] 6.4 Add a JS test (Node, alongside `protocol.js`'s existing test suite) that feeds a Python-`_serialize_active_skill_groups`-shaped row (hand-written to match) through `validateCharacterActiveSkillRow` and confirms it passes, and that a bare `{key,label}` row (the unregistered-key fallback shape) also still passes
- [ ] 6.5 Add a `world/rules/tests/` case in the relocated function's new home confirming `freeform_scale_entries_for` behaves identically to the old `_freeform_scales_for_skill` for the same inputs (same test data, same expected output)

## 7. Spec sync and gates

- [ ] 7.1 Confirm `openspec/changes/fix-webclient-skillbook-descriptor-data/specs/webclient-component-showcase/spec.md`'s MODIFIED requirement matches the implemented behavior exactly (field names, optionality, the two new scenarios)
- [ ] 7.2 Run `openspec validate fix-webclient-skillbook-descriptor-data --strict`
- [ ] 7.3 Run the Python test suite slice covering `web/webclient/presentation/tests/` and `world/rules/tests/`'s combat/skills-family modules
- [ ] 7.4 Run `npm test` (Vitest) for the affected component/story tests, plus the JS protocol test suite covering `protocol.js`
- [ ] 7.5 Run `tools.spec_traceability check` to confirm the amended requirement's new scenarios have matching tests
