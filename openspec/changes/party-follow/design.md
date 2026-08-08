# party-follow Design

## Context

`party-core` owns the membership binding. Player movement funnels through three real traversal
success paths, not one: `MovementCostMixin.at_post_traverse` in `typeclasses/exits.py` (grid,
instance, and base exits), and the two wilderness exits in the same file —
`WildernessGateExit.at_traverse` (grid → wilderness) and `WildernessReturnExit.at_traverse`
(wilderness return + ordinary wilderness steps) — which perform their own movement, charging, and
arrival recording and never reach `at_post_traverse`. Any follow design that claims "every exit
lineage" without covering the wilderness paths is wrong.

Constraints: the world clock advances only on player action; the project's room observers
(`GridRoom.at_object_receive`, `InstanceRoom.at_object_receive`) are all gated on
`isinstance(obj, PlayerCharacter)`, so moving NPCs quietly fires none of them; Evennia 6.1.0's
`move_to` sets the destination before calling `destination.at_object_receive(..., move_type=...)`,
and the contrib `WildernessRoom.at_object_receive` does not accept `move_type` — a plain `move_to`
into a wilderness room therefore reports failure after the object already arrived, and the
wilderness coordinate bookkeeping is skipped. Wilderness movement must go through the provider's
coordinate API.

## Goals / Non-Goals

**Goals**

- Companions follow on every exit success path: grid/instance/base, wilderness gate entry,
  wilderness step, wilderness return.
- Costless (no clock charge), silent (no announce messages, no player-gated observers), and
  binding-preserving follow.
- Correct wilderness moves through the provider API, never `move_to` into wilderness rooms.
- Deterministic 跟丟了 fallback naming all left-behind companions, once per traversal.
- Follow scoped to exit traversal only; no teleporting of distant companions.

**Non-Goals**

- Pathfinding or re-summoning, teleport/spawn following, companion clock costs, follow OOB
  events, combat and quest integration (`party-combat`, `party-quest`).

## Decisions

### D-1: One follow function, three hook sites

`world/rules/party.py::follow_companions(player, source_location, *, destination=None,
wilderness_coordinates=None, wilderness_name=WILDERNESS_NAME)` is called from:

1. `MovementCostMixin.at_post_traverse` — `destination` mode for grid/instance/base exits.
2. `WildernessGateExit.at_traverse` success branch — `wilderness_coordinates=entry.wilderness_xy`.
3. `WildernessReturnExit.at_traverse` — the ordinary-step branch passes
   `wilderness_coordinates=target_location.coordinates`; the return branch passes
   `destination=grid_room`.

One function keeps the follow contract (co-located filter, per-companion failure capture,
single notification) in one place; the three call sites are thin and each covered by an
integration test.

### D-2: Wilderness movement uses the provider API; grid movement uses quiet move_to

Companions entering or stepping within the wilderness move through
`enter_wilderness(companion, coordinates=..., name=...)`, which routes to the script's
`move_obj` and maintains `itemcoordinates` — the only correct path for wilderness rooms. Grid,
instance, and base destinations use `move_to(destination, quiet=True)`: quiet suppresses the
announce messages, and the project's arrival observers are all `PlayerCharacter`-gated so no
quest, onboarding, art, or interaction observer fires for an NPC. The follow contract does NOT
claim `quiet=True` suppresses `at_object_receive` — it claims the observers that would fire for
NPCs are none, which is verified by test.

### D-3: Safe companion resolution reuses the party-core contract

`follow_companions` resolves the party through the safe bound-companion accessor (skipping stale
dbids, non-NPC entries, and backref mismatches, per `party-core`'s purge contract), so a deleted
NPC's leftover entry can never raise from the traversal hook or block the other companions.

### D-4: Failures are collected, named, and reported once

Each companion move runs in its own try/except; failures append the companion's key to a list.
After all moves, if the list is non-empty, the player receives one fixed Traditional Chinese
「跟丟了」 line naming the failed companions. The hook never raises.

## Risks / Trade-offs

- [A wilderness path misses the follow call] → all three success branches are explicit call
  sites, each with an integration test (gate entry, ordinary step, return).
- [`move_to` into a wilderness room corrupts coordinates] → impossible by construction: the
  wilderness modes never call `move_to` (D-2); a regression test pins the provider-API usage.
- [Quiet movement still runs `at_object_receive`] → all project observers are
  `PlayerCharacter`-gated; the test asserts no observer side effect fires for companions.
- [A stale dbid crashes the hook] → safe resolution (D-3); a stale-entry test covers it.
- [The 跟丟了 wording drifts] → the fixed template names the failed companions and is tested for
  exactly one notification with multiple failures.

## Migration Plan

No released users; no data migration. Existing parties gain follow on the next server start;
rollback is a revert of the hook calls.

## Open Questions

- None blocking. The exact 跟丟了 sentence is authored at apply time in Traditional Chinese with
  the named-companion template.
