## Context

`world/rules/action.py`'s `_EFFECT_HANDLERS` registers `damage` (in `world/rules/combat.py`) as the
one trait-mutating cast effect that currently works end-to-end: cast → `PendingEffect` staged → HP
reduced. The skill-system redesign's spell catalog needs the mirror-image operation (HP restoration)
for a dozen-plus new spells, and no such handler exists.

## Goals / Non-Goals

**Goals:**
- Give `heal:<shape>` a working cast-time handler with the same reliability guarantees `damage`
  already has (staged via `PendingEffect`, resolved in the same step of the eight-step action
  resolution pipeline).
- Cap healing at the target's max HP — no overheal, no negative-HP edge case.

**Non-Goals:**
- No new status effects (regen-over-time, cleanse-on-heal) — pure instantaneous HP restoration only.
  A spell whose flavor text implies "and removes debuffs" (e.g. 淨化術) is out of this change's scope
  (see the sibling `cleanse-effect-handler` change, raised separately for exactly that gap).
- **No revival of a knocked-out target.** `world/rules/targeting.py`'s `_validate_alive` rejects any
  `hp <= 0` target as `target_dead`, and AREA shorthand expansion excludes `knocked_out` entities from
  every selection — this is a structural property of the existing targeting pipeline, not something
  this change can or should route around. A spell whose flavor text implies "revives" or "rescues from
  near-death" (e.g. 瀕死急救, 解除瀕死) only restores HP on an already-alive target under this change;
  any dependent spell-catalog change claiming an actual revival mechanic must downgrade that specific
  flavor claim rather than assume `heal`/`self_heal` provides it. As defense in depth, the heal/self_heal
  apply closure is additionally a no-op when the affected entity is not alive at commit time (rubber-duck
  hardening: a mid-action damage effect or a knocked-out caster can never be reversed into positive HP).
- Magnitude formula (how much HP a given caster's heal restores) is out of scope for this proposal to
  invent from scratch — it SHALL reuse whatever caster-stat-driven magnitude computation `damage`
  already uses (e.g. keyed off `magic_level`/a magic-power trait), substituting a healing coefficient
  for a damage coefficient, so the two effects share one well-tested magnitude pipeline rather than two
  parallel ones.
- Does not touch MP costs or any specific spell's registry entry — those are each spell-catalog
  proposal's job.

## Decisions

- **`heal:<shape>` mirrors `damage:<element>:<type>`'s shape** (a bare descriptor, no embedded number)
  rather than encoding a flat heal amount in the string, for consistency with how every other
  magnitude-bearing effect in this codebase resolves magnitude from caster state at cast time, not from
  registry-authored constants.
- **Single new handler function, not per-element heal variants.** Unlike `damage`, healing has no
  element-type interaction (no "heals more against dark-type targets"), so one `_handle_heal` function
  suffices; `shape` (`single`/`area`) is its only branch.
- **`self_heal` is a distinct prefix, not a third `heal:` shape value**, mirroring the existing
  `self_buff_apply`/`buff_apply` split (`action.py:337-365`) rather than overloading `heal:<shape>` to
  sometimes mean "the resolved target list" and sometimes mean "the actor" — a skill's cast handlers
  all receive the same resolved `targets` list, so an actor-directed effect needs its own prefix, not a
  shape flag on a target-list-driven one.
- **Reuses `PendingEffect` staging**, not a new effect-resolution primitive — this is a one-line
  precedent copy of `damage`'s existing registration pattern in `action.py`.

## Risks / Trade-offs

- [Risk] Overheal / negative-HP edge cases at the cap boundary. → Mitigation: clamp explicitly
  (`min(target.traits.hp.max, target.traits.hp.value + amount)`); add a boundary test at exactly-full
  HP and near-death HP.
- [Risk] Reusing `damage`'s magnitude pipeline with a substituted coefficient could silently break if
  that pipeline has damage-specific assumptions (e.g. reads `defense` for mitigation). → Mitigation:
  read `combat.py`'s actual magnitude computation before implementing; if it is not cleanly
  factorable, this task list includes an explicit "confirm/extract shared magnitude helper" step rather
  than copy-pasting damage's defense-mitigation logic into heal by mistake.

## Migration Plan

Purely additive — no existing behavior changes. Lands after `skill-effects-typed-model`, before
`spell-catalog-fire`/`spell-catalog-water`/`spell-catalog-light`.

## Open Questions

None — the "revival" grammar question raised in an earlier draft of this document is resolved by the
Non-Goals section above: `heal`/`self_heal` never revive a knocked-out target, full stop. Any spell
whose flavor text implied revival (生命之海, 復生之潮/`tidal_revival`, `revival_light`) is downgraded to
ordinary heal-only flavor in its own spell-catalog change, not solved here.
