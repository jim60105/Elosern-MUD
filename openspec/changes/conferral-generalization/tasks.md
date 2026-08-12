## 1. Generalize the grant shape

- [ ] 1.1 Drop `trait_keys` from `ConferredSkillGrant` in `world/skills/handler.py`
- [ ] 1.2 Update `record_conferred_grant()` in `world/rules/skill_effects.py` to drop the `trait_keys`
      parameter
- [ ] 1.3 Update `_handle_confer_skill_partial` in `world/rules/action.py` to stop requiring/passing
      `confer_trait_keys` in its event context; remove it from `requires_event_context`

## 2. Update consumers

- [ ] 2.1 Update `SkillHandler.effective_value` to derive affected traits from the referenced skill's
      `parsed_effects` (via `skill-effects-typed-model`) instead of the dropped `trait_keys` field
- [ ] 2.2 Update `combat_modifiers.py`'s `skill_owned` context builder (from `skill-owned-rule-condition`)
      to check `conferred_grants()` for grants referencing a `RuleTableEffect`-shaped skill and fold in
      the scaled adjustment

## 3. Structural exclusion

- [ ] 3.1 Implement the gate-type-effect rejection (`EFFECT_RESOLUTION_FAILED`) by pattern-matching the
      referenced skill's parsed effect class, not a hardcoded skill-key list
- [ ] 3.2 Test the exclusion against every currently-known gate-type class
      (`ElementMasteryEffect`, `SexualMasteryEffect`, disguise's effect class)

## 4. Fixture and test updates

- [ ] 4.1 Update any existing test fixture constructing `ConferredSkillGrant` with `trait_keys` to the
      new shape
- [ ] 4.2 Run the full existing `skill-handler` scenario suite; confirm the 統御術 body-enhancement
      scenario still passes with the new derivation path
- [ ] 4.3 New test: conferred grant reaching a `skill_owned` rule-table adjustment (task 2.2's scenario)
