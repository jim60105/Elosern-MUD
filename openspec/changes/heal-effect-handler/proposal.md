## Why

The skill-system redesign's spell catalog (`docs/superpowers/specs/2026-08-12-skill-system-redesign-
design.md` §4.4) adds healing spells across the fire, water, and light elements (e.g. 治癒術,
治癒之泉, 高級治癒, 神聖光輝). No `heal` effect prefix or cast-time handler exists anywhere in the
codebase today — `damage:<element>:<type>` is the only trait-restoring/reducing cast effect currently
wired up. Without this change, every healing spell in the three dependent `spell-catalog-*` proposals
would be unimplementable.

## What Changes

- Add a new `heal` effect-ID convention: `heal:<shape>` where `<shape>` is `single` or `area`,
  mirroring the existing `damage:<element>:<type>` convention's shape (no numeric magnitude encoded in
  the string — magnitude is computed at resolution time from caster stats, exactly like `damage`
  already does).
- Add a separate `self_heal` effect-ID convention (no `<shape>` argument), mirroring how
  `self_buff_apply` (`action.py`) binds to the acting entity rather than the skill's resolved target
  list — needed because a target-list-driven `heal:<shape>` cannot express "the caster heals
  themself while the same cast also damages an enemy target" (e.g. a life-draining or self-sustaining
  attack spell). This was found missing during rubber-duck review of the batch this change belongs to.
- Add a cast-time handler in `world/rules/combat.py` (co-located with the existing `damage` handler,
  registered the same way via `register_effect_handler`) that restores `hp` on the target(s) (or the
  actor, for `self_heal`), capped at the target's max, and stages the change through the existing
  `PendingEffect` mechanism `damage` already uses.
- Add `HealEffect(shape: Literal["single", "area"])` and `SelfHealEffect()` to
  `world/skills/effects.py`'s typed-effect dispatch (depends on `skill-effects-typed-model`).
- **Explicitly excludes reviving a knocked-out target.** `world/rules/targeting.py` structurally
  prevents selecting a knocked-out (`hp <= 0`) entity as a skill target (`_validate_alive` rejects it as
  `target_dead`; AREA shorthand expansion excludes `knocked_out` entities entirely). `heal`/`self_heal`
  only ever restore HP on an already-valid, already-alive target — reviving a knocked-out ally is a
  separate, unbuilt battlefield-state feature, not part of this change's scope (see design.md).

## Capabilities

### New Capabilities
- `heal-effect-handler`: the `heal:`/`self_heal` effect conventions, their typed representation, and
  their cast-time resolution behavior (HP restoration capped at max, staged via `PendingEffect`; no
  revival of knocked-out targets).

### Modified Capabilities
(none — this is purely additive; no existing capability's requirements change)

## Impact

- New code in `world/rules/combat.py` (handler) and `world/skills/effects.py` (typed effect, extending
  the dispatch table `skill-effects-typed-model` establishes).
- Depends on `skill-effects-typed-model` (must land first).
- Blocks `spell-catalog-fire`, `spell-catalog-water`, `spell-catalog-light` (the three elements whose
  §4.4 spell lists include healing spells) — they cannot declare a working `heal:` effect until this
  lands.
