## Why

`flight` and `flash_step` both declare `movement:*` effects with no consumer — owning either grants
nothing today, and their lore descriptions ("可前往遠處/較近的場合") have no distance-tiered
fast-travel system to hook into. Per the approved design doc (D8, §4.4 footnote), this round scopes
the `movement` prefix down to something the existing engine already supports: a cost/restriction
waiver on `charge_movement()`, the single shared movement-cost entry point.

## What Changes

- Add `MovementEffect(mode: Literal["flight", "flash_step"])` to `world/skills/effects.py`'s dispatch
  (depends on `skill-effects-typed-model`).
- `world/rules/movement.py`'s `charge_movement()` gains a waiver check: a `PlayerCharacter` owning
  `flight` skips the `wilderness_move` cost entirely when traversing wilderness; owning `flight` or
  `flash_step` also passes any exit/traversal that is marked as requiring flight (a new,
  narrow `requires_flight` flag on the relevant exit typeclass(es), defaulted `False` everywhere it
  isn't explicitly set — no existing exit gains this flag as part of this change).
- `flight` and `flash_step` reclassify from `ACTIVE` to `PASSIVE` — same reasoning as
  `body_enhancement`'s D3 reclassification: the waiver is an ambient, ownership-triggered effect
  applied inside `charge_movement()`'s existing call path, not a discrete action a player performs, so
  there is no cast handler to register and none is added.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `movement-cost-charging`: `charge_movement()` gains the flight/flash_step waiver check.

## Impact

- `world/rules/movement.py` (waiver check in the single shared entry point), `world/skills/registry.py`
  (no change to `flight`/`flash_step`'s definitions beyond what `skill-effects-typed-model`'s typed
  parsing already requires — MP/cost rebalancing for `flight` happens in `spell-catalog-wind`, not
  here), `world/skills/effects.py` (`MovementEffect`).
- Depends on `skill-effects-typed-model`. Independent of every other mechanism change in this batch.
- `spell-catalog-wind` depends on this change landing first (it recosts `flight`'s MP and should not
  touch a skill mid-flight of this change's own edits).
