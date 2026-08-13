## Why

`light_sword_style` and `dual_wield_style` both declare `weapon_style:*` effects with no consumer —
casting `light_sword_style` (an attack skill, `SINGLE` target) always rejects `UNKNOWN_EFFECT_ID`, and
owning `dual_wield_style` (a stance skill, `SELF` target, no direct effect) does nothing. Per the
approved design doc §3.3, these two skills are different shapes of problem and get different fixes:
the attack skill should just use the already-working `damage` convention; the stance skill should
become an ownership-triggered rule-table row.

## What Changes

- `light_sword_style`'s effect changes from `weapon_style:light_sword` to
  `damage:light:physical` — no new mechanism, reuses the already-working `damage` handler exactly as
  `fire_ball`/`shadow_slash` already do.
- `dual_wield_style`'s effect stays `weapon_style:dual_wield`, but gains a consumer: a new
  `skill_owned` row in `combat_modifiers.yaml` granting a to-hit/damage adjustment while the entity is
  in this stance, conditioned on dual-wielding (two weapons equipped) if the equipment system exposes
  that fact, or on bare ownership otherwise (see design.md for the equipment-check investigation task).
- `WeaponStyleEffect` in `world/skills/effects.py` narrows to only the stance case (`dual_wield`)
  going forward — `light_sword` is no longer a `weapon_style` value once its skill moves to `damage`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-registry`: `light_sword_style`'s effect string changes from `weapon_style:light_sword` to
  `damage:light:physical`.
- `combat-modifier-table`: gains a `skill_owned` row for `dual_wield_style`.

## Impact

- `world/skills/registry.py` (one skill's `effects` list), `world/rules/rulebook/combat_modifiers.yaml`
  (one new row).
- Depends on `skill-effects-typed-model` (typed effects) and `skill-owned-rule-condition` (the
  `skill_owned` primitive this change's `dual_wield_style` row uses) — both must land first.
