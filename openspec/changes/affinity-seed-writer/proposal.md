## Why

`world/rules/affinity.py` has exactly one writer, `apply_affinity_change`, and
it is built for *interaction* deltas: a closed source vocabulary, a shared daily
budget, clamping against the record's cap, and a party auto-leave recheck on
every negative delta.

Nothing can currently establish a relationship that no interaction produced. A
starting companion, a quest-granted ally, or any authored bond has to either
abuse the interaction writer — burning daily budget and resolving a fictitious
source — or write the record from outside the module and break the single-writer
boundary. Both are wrong.

This change adds the missing primitive on its own, ahead of its first consumer,
so the affinity capability's contract change is reviewed and tested in isolation
rather than buried inside a companion feature.

## What Changes

- `world/rules/affinity.py` gains `seed_affinity(npc, player, value)`: a
  one-shot writer that creates a fresh `AffinityRecord` at `value` with `cap` at
  `NATURAL_CAP` and the daily counter zeroed and stamped with the current world
  day.
- It refuses to overwrite an existing record for the pair, so a seed can never
  launder an interaction gain past the daily budget or erase a real history.
- It rejects a value outside `1..NATURAL_CAP`.
- It consumes no daily budget, resolves no source, and runs no auto-leave
  recheck, because a seed is not an interaction.
- It snapshots and restores the host's `relations_data` surface on failure,
  following `apply_affinity_change`'s existing discipline, so a failed seed
  leaves nothing readable in the in-process attribute cache.
- `apply_affinity_change` is untouched.
- The capability's sole-writer requirement widens from "one function" to "one
  module with two narrowly-scoped writers", which is the honest statement of the
  boundary being defended.

The first consumer is `preset-companion-activation`; nothing calls the new
function in this change. That is a deliberate forward-declared seam, not a fake
implementation.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `affinity-system`: the sole-writer requirement now bounds the *module* rather
  than a single function, and adds the seed writer's own constraints.

## Impact

- `world/rules/affinity.py` — one new function; no change to the record shape,
  the handler, the stage ladder, the budget logic, or the auto-leave hook.
- `world/rules/tests/test_affinity.py` — seed behavior, refusal to overwrite,
  range rejection, budget isolation, and the no-recheck guarantee.
- Unaffected: `world/rules/party.py`, every existing affinity caller (talk,
  trade, guild, quest turn-in, friendly fire, sexual resist), and every
  presentation surface.
