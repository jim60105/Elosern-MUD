## 1. Generalize the grant shape

- [x] 1.1 Drop `trait_keys` from `ConferredSkillGrant` in `world/skills/handler.py`
- [x] 1.2 Update `record_conferred_grant()` in `world/rules/skill_effects.py` to drop the `trait_keys`
      parameter
- [x] 1.3 Update `_handle_confer_skill_partial` in `world/rules/action.py` to stop requiring/passing
      `confer_trait_keys` in its event context; remove it from `requires_event_context`

## 2. Update consumers

- [x] 2.1 Update `SkillHandler.effective_value` to derive affected traits from the referenced skill's
      `parsed_effects` (via `skill-effects-typed-model`) instead of the dropped `trait_keys` field
- [x] 2.2 Update `combat_modifiers.py`'s `skill_owned` context builder (from `skill-owned-rule-condition`)
      to check `conferred_grants()` for grants referencing a `RuleTableEffect`-shaped skill and fold in
      the scaled adjustment

## 3. Structural exclusion

- [x] 3.1 Implement the gate-type-effect rejection (`EFFECT_RESOLUTION_FAILED`) by pattern-matching the
      referenced skill's parsed effect class, not a hardcoded skill-key list. The check is shared and
      runs in both the resolution-time handler (`_handle_confer_skill_partial`, so the resolver returns
      `EFFECT_RESOLUTION_FAILED` at cast-resolution time) and the write primitive
      (`record_conferred_grant`, so direct callers are equally protected). The same rejection applies
      to a skill carrying no continuous-valued effect (`StatMultiplyEffect`/`RuleTableEffect`) any
      grant consumer can resolve, so a grant can never be a silent no-op
- [x] 3.2 Test the exclusion against every currently-known gate-type class
      (`ElementMasteryEffect`, `SexualMasteryEffect`, disguise's effect class) and against a
      no-continuous-effect skill

## 4. Fixture and test updates

- [x] 4.1 Update any existing test fixture constructing `ConferredSkillGrant` with `trait_keys` to the
      new shape
- [x] 4.2 Run the full existing `skill-handler` scenario suite; confirm the 統御術 body-enhancement
      scenario still passes with the new derivation path
- [x] 4.3 New test: conferred grant reaching a `skill_owned` rule-table adjustment (task 2.2's scenario)
