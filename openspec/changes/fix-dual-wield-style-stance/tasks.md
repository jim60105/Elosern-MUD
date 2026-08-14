## 1. Registry reclassification

- [ ] 1.1 In `world/skills/registry.py` (lines 572-580), change `dual_wield_style` to
      `SkillKind.PASSIVE`, `TargetSpec.NONE`, and drop `cost={"sp": 8}`; keep
      `effects=["weapon_style:dual_wield"]`, the label 雙持劍術, and the description unchanged
- [ ] 1.2 In `world/skills/tests/test_registry.py`, move the `dual_wield_style` shape assertions
      out of `test_dual_blade_mastery_is_a_higher_tier_sibling` (lines 447-450) into a new test
      method `test_dual_wield_style_is_a_passive_stance` asserting `PASSIVE`, `TargetSpec.NONE`,
      empty `cost`, and unchanged `effects` (no `covers_requirement` annotation yet — see 4.4)
- [ ] 1.3 In the same file, update `test_dual_wield_style_ownership_has_no_bearing_on_cost`
      (lines 493-503): grant `dual_wield_style` in the `passive` bucket (`{"active":
      ["dual_blade_mastery"], "passive": ["dual_wield_style"]}`) and keep asserting the
      `dual_blade_mastery` cast still costs exactly 30 SP
- [ ] 1.4 Confirm `world/skills/tests/test_cost_tiers.py:15-25` needs no edit — `spell_tier_for`
      already returns `None` for the now-PASSIVE `dual_wield_style`

## 2. Preset kit

- [ ] 2.1 In `world/lore/player_presets.py` (lines 98-100), move `dual_wield_style` from
      `yuka_darknight`'s `active_skills` to the start of its `passive_skills`, keeping
      `dual_blade_mastery` and `shadow_slash` active
- [ ] 2.2 Extend `world/lore/tests/test_player_presets.py::test_kit_validation_rejects_unknown_kind_mismatch_and_divine_gate`
      with the regression case `(make(active_skills=("dual_wield_style",)), "classifies it as")`
- [ ] 2.3 Run the preset tests to confirm `test_every_preset_skill_resolves_with_matching_kind`
      passes with the moved bucket

## 3. Clean cast rejection at the ownership step

- [ ] 3.1 Add `test_cast_of_reclassified_dual_wield_style_is_rejected_as_passive` to
      `world/rules/tests/test_action_pipeline_rejections.py`, mirroring the `flight` precedent
      (lines 64-70): grant `dual_wield_style` in the `passive` bucket and assert
      `resolve("dual_wield_style").reason is RejectReason.SKILL_NOT_ACTIVE` (no
      `covers_requirement` annotation yet — see 4.4)
- [ ] 3.2 Add a companion assertion in `world/rules/tests/test_action_preview.py` that
      `preview_skill(...).reason` reports the same `SKILL_NOT_ACTIVE` for an owned
      `dual_wield_style` (the requirement's preview half)
- [ ] 3.3 Confirm no existing test casts `dual_wield_style` expecting `UNKNOWN_EFFECT_ID` or a
      successful outcome (grep `dual_wield_style` in `world/rules/tests/` and
      `world/skills/tests/` after the edits)

## 4. Verification

- [ ] 4.1 Run the affected domains: `uv run --locked evennia test --settings test_settings.py
      world.skills world.lore world.rules.tests.test_action_pipeline_rejections
      world.rules.tests.test_action_preview world.rules.tests.test_combat_modifiers
      world.rules.tests.test_status_query`
- [ ] 4.2 Confirm the combat-modifier and status-query tests pass with zero edits (the rule row,
      its no-create contexts, and the status-display row are untouched)
- [ ] 4.3 Check `git diff --check` is clean; run `openspec validate --change
      fix-dual-wield-style-stance --strict`
- [ ] 4.4 Do NOT add `covers_requirement` annotations for the new delta requirement during
      implementation: `tools.spec_traceability check` indexes only main specs, so an annotation
      for `skill-registry::dual-wield-style-is-a-passive-stance-not-a-castable-active-skill`
      would fail with `unknown-requirement-id` until the delta is synced (same deferral as
      `fix-cast-clock-settlement` task 4.1). At archive time, after `openspec archive` syncs the
      delta into `openspec/specs/`, annotate the tests from 1.2 and 3.1 (and the companion 3.2
      assertion) with that requirement ID, and also tag the existing
      `test_rule_dual_wield_style_atk_phys_bonus` (`test_combat_modifiers.py:121-124`) so
      scenario 2 has a direct association
