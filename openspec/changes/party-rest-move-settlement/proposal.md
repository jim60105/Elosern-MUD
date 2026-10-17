# Proposal: Party-wide rest and movement time settlement

## Why

Design §2 and §4.6 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: `world/rules/time_skip.py::advance_skip` and `world/rules/movement.py::charge_movement` advance the world clock with only the acting character in scope, so resting never regenerates a companion's gauges, never expires its buffs, and never settles its practice booking. Companions only settle in combat.

## What Changes

- SKIP advances (`rest`, `sleep`, `wait`, `explore.wait`, `explore.practice` skips) settle the present party scope of the acting character (`party-member-authority`): the acting character, the commander, and every effective companion in that room.
- Movement advances settle the traverser plus the companions that travel with it (co-located in the source room of a player-character traversal). A possessed traverser has no followers and keeps its single-entity scope.
- The movement and skip rollback snapshots cover every settled member, so a failed advance restores each member's gauges, buffs and booking.
- Church rite, GM console, defeat aftermath and combat settlement keep their current scopes. A member in another room is never settled.
- `sleep` still computes its duration from the acting character's own regeneration need (unchanged).

## Capabilities

### New Capabilities

- `party-time-settlement`: which commander-initiated clock advances settle the present party and which keep their scope.

### Modified Capabilities

- `movement-cost-charging`: `charge_movement` passes the travelling party instead of the traverser alone.
- `time-skip-commands`: the rest/skip advance passes the present party scope.
- `world-clock`: the documented call-site scopes change for the skip commands.
- `settlement-stage-order`: the practice-stage note no longer claims single-entity SKIP scopes.

## Impact

- `world/rules/time_skip.py`, `world/rules/movement.py`, `typeclasses/exits.py` (passes the source room to `charge_movement`), `world/rules/movement_settlement.py` (snapshot registry for travelling members), `commands/skip.py`, `web/webclient/actions/exploration_actions.py` (no payload change).
- Tests: `world/rules/tests/test_party_time_settlement.py` (new, sharded), updates to existing movement/skip tests that pinned single-entity scope.
- Observability: the existing `clock_advance` event gains a `scope` count in context; observability lint runs.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **2 of 30**.

- depends-on: party-member-authority

### Code and spec conflicts within the new batch

- `party-field-settlement-scope`: shared specs `world-clock`, `party-time-settlement` (S, ordered: this change first); no shared code file.
- `party-practice-booking`: shared files `world/rules/time_skip.py`, `commands/skip.py`; shared specs `time-skip-commands`, `settlement-stage-order` (F, ordered: this change first; the later change re-modifies the same rest requirement preserving this scope text).
- `party-unlock-notices`: shared file `world/rules/clock.py` only if the practice stage sink is touched (D via practice booking).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. The archived possession room fix is consumed unchanged.
