## Why

`dual_wield_style` is the last half-migrated skill from the run-2 audit's "18 inert ACTIVE skills"
finding. Its intended mechanical effect already landed as an ownership-triggered rule-table row
(`combat_modifiers.yaml` `dual_wield_style_atk_phys_bonus`, conditioned on `skill_owned` +
`dual_wielding`), but the skill itself is still declared `SkillKind.ACTIVE` with an `sp: 8` cost and
a `SELF` target. The action resolver registers no `weapon_style` effect handler, so an in-combat
cast attempt rejects `UNKNOWN_EFFECT_ID` at effect resolution (out-of-combat attempts reject
earlier as `SKILL_NOT_USABLE_OUT_OF_COMBAT`) — the exact dead-ACTIVE shape the design doc
§3.3 and the `body_enhancement`/`flight` reclassifications already eliminated elsewhere.

## What Changes

- `dual_wield_style` in `world/skills/registry.py` reclassifies to `SkillKind.PASSIVE`,
  `TargetSpec.NONE`, and an empty `cost` — matching the PASSIVE/empty-cost shape of the
  ownership-triggered rule-table skills (`body_enhancement*`, mastery skills, `defense_instinct`,
  …) and the `NONE` target of the mastery/instinct passives. This explicitly amends design doc
  §3.3's literal "`SELF` target" description of the stance, which predates the PASSIVE
  reclassification; §3.3's core ruling (owning the stance drives the `skill_owned` rule table)
  is what this change implements. Its
  `effects=["weapon_style:dual_wield"]` string is unchanged: the typed `WeaponStyleEffect` already
  declares the rule-table consumption path, and the combat rule matches on `skill_owned`, not the
  effect prefix. **BREAKING** (internal only, unreleased project): the skill can no longer be cast;
  a cast attempt now rejects `SKILL_NOT_ACTIVE` at the resolver's ownership step (and
  `SKILL_NOT_ACTIVE` in `action_preview`) instead of reaching `UNKNOWN_EFFECT_ID`.
- `yuka_darknight`'s preset kit moves `dual_wield_style` from `active_skills` to `passive_skills`
  in `world/lore/player_presets.py`, satisfying the existing load-time kind-mismatch validation.
  `dual_blade_mastery` (the castable 宗師級 attack) and `shadow_slash` stay active — the preset
  keeps its full offensive kit.
- No production change to `action.py`, `action_preview.py`, `combat.py`, `monster_behaviour.py`,
  `cost_tiers.py`, `combat_modifiers.py`, `status_query.py`, `effects.py`, or
  `world/imports/validate.py`: verified — every consumer already keys on `SkillKind` and either
  handles PASSIVE correctly (`SKILL_NOT_ACTIVE` in step 1 / preview) or requires ACTIVE (monster/NPC
  AI damage-skill selection), so the reclassification is safe without touching them.
- Tests updated to the new contract: registry shape assertions, the
  `test_dual_wield_style_ownership_has_no_bearing_on_cost` fixture (skill moves to the passive
  bucket), the preset kit tests, and a new clean-rejection test mirroring the `flight` precedent
  (resolver) plus its `action_preview` companion.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-registry`: `dual_wield_style` reclassifies from an inert castable `ACTIVE` skill to a
  `PASSIVE` stance whose ownership drives the already-landed rule-table bonus; cast attempts reject
  `SKILL_NOT_ACTIVE` at the ownership step.

## Impact

- `world/skills/registry.py` — `dual_wield_style` kind/target/cost (effects unchanged).
- `world/lore/player_presets.py` — `yuka_darknight` kit bucket for `dual_wield_style`.
- Tests: `world/skills/tests/test_registry.py` (shape + cost-independence fixture),
  `world/lore/tests/test_player_presets.py` (kind-mismatch case),
  `world/rules/tests/test_action_pipeline_rejections.py` (new passive-rejection test with
  `covers_requirement`), and `world/rules/tests/test_action_preview.py` (companion preview
  assertion). `world/skills/tests/test_cost_tiers.py` and the combat-modifier/status tests are
  unaffected (they already treat the stance as passive).
- No player-command surface, docs, schema, or migration artifacts change (0 released users).
