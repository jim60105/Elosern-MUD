## Context

`world/rules/movement.py`'s `charge_movement(traversing_object, cost_key)` is the single, shared
movement-cost entry point — per `movement-cost-charging`'s own spec, every non-teleport exit lineage
charges movement through it, never through a bespoke inline `advance()` call. `flight` and
`flash_step` currently declare `movement:*` effects with zero consumers. Per D8 of the approved design
doc, this round does not build a distance-tiered fast-travel system — it scopes the lore's "can reach
far/near locations" down to a cost/restriction waiver on the existing traversal path.

**Correction to the approved design doc**: §3.1's Core Architecture table describes `movement` as
"Cast → `action.py` handler." Found during rubber-duck review: this change instead reclassifies
`flight`/`flash_step` to `PASSIVE` with no cast handler at all (see Decisions below) — the ambient
waiver is a better fit for how these two skills actually read narratively, matching the same D3
precedent `skill-effects-typed-model` already established for `body_enhancement`. This is a correction
in the same spirit as `divine-mystery-skills`' `RaceProfile` finding: the parent design doc's summary
table was wrong about this one detail, caught while writing the implementing proposal.

## Goals / Non-Goals

**Goals:**
- Owning `flight` waives the `wilderness_move` clock cost.
- Owning `flight` or `flash_step` passes any exit explicitly marked as flight-required.
- The waiver is purely ownership-triggered — no cast action, no MP/SP spent per use.

**Non-Goals:**
- No new zone/distance/fast-travel system (D8) — this is strictly a waiver on the existing single
  shared charging function and a narrow opt-in exit flag, not a new traversal mechanism.
- No existing exit gains `requires_flight=True` as part of this change — the flag is added to the
  relevant typeclass(es) but not populated onto any current map content; that is world-building content
  work outside a skill-system proposal's scope.
- Does not recost `flight`'s MP (that is `spell-catalog-wind`'s job, landing after this change).

## Decisions

- **`flight`/`flash_step` reclassify `ACTIVE` → `PASSIVE`**, mirroring `skill-effects-typed-model`'s D3
  treatment of `body_enhancement`. The waiver is ambient (checked inside `charge_movement()`, which
  already runs on every traversal) rather than something a player discretely activates — there is no
  narrative or mechanical moment where "casting flight" would mean something different from "owning
  flight," so no cast handler is built.
- **The flight-required flag lives on the exit typeclass, not as a new registry**, matching how other
  per-exit traversal facts (cost keys) are already modeled per `movement-cost-charging`'s existing
  pattern — one flag, checked at `charge_movement()`'s call site, not a parallel lookup table.
- **`wilderness_move` waiver only for `flight`, not `flash_step`.** Lore explicitly separates "far"
  (flight) from "near" (flash_step) — `flash_step` is not framed as a wilderness-traversal replacement,
  so it only affects the flight-required-exit check, not the wilderness clock-cost waiver.

## Risks / Trade-offs

- [Risk] A full waiver of `wilderness_move` cost could let a flight-owning entity (any elf character,
  given the narrative's power level) traverse wilderness for free indefinitely, changing game balance
  in ways not fully explored. → Mitigation: this is explicitly the lore's stated intent ("可前往遠處的
  場合" implies unencumbered long-distance travel for a flight-capable caster); if this proves
  unbalanced in play, it's a tuning change to one `if` condition, not an architecture problem.

## Migration Plan

No data migration. Lands after `skill-effects-typed-model`. `spell-catalog-wind` depends on this
change landing first (it recosts `flight`'s MP on an already-PASSIVE-reclassified skill definition).

## Open Questions

None.
