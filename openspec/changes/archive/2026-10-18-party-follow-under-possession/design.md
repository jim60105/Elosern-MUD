# Design: The whole party follows a possessed traversal

## Context

See proposal.md. `follow_companions(player, source_location, ...)` returns immediately unless `player` is a `PlayerCharacter`; it moves `live_companions(player)` co-located with the source (room match or wilderness `itemcoordinates` match), records one 跟丟了 notice, then re-observes quest arrival. `charge_movement` already charges a possessed puppeted traverser (`is_player_driven`). `settle_movement` snapshots companions only for a `PlayerCharacter` traverser. The archived possession room fix restores the companion's room on release and keeps the D4 owner-body location guard; the owner body is unpuppeted but keeps a real location and an entranced line.

## Goals / Non-Goals

**Goals:** same-party members stay co-located through possessed movement; all-or-nothing compensation; no change to possess/release gates.

**Non-Goals:** reuniting members separated by a failed follow or by non-exit relocation, disconnect recovery, any change to who may possess.

## Decisions

- **Explicit amendment.** This change records the user's 2026-10-18 decision amending the design's "no change to possession rules" non-goal for movement only.
- **Follower set** = `resolve_commander(traverser)` plus `live_companions(commander)` (which includes the possessed NPC), minus the traverser; a direct traversal by the owner body while possessing cannot occur because the body is unpuppeted, filtered by the existing co-location predicate against the source. For a player traverser this equals today's set. An unresolvable commander (stale possession flag) follows nobody and is logged.
- **Owner body move**: companions keep `move_to(destination, quiet=True)` (hooks run, as today). The unpuppeted body instead first runs `destination.at_pre_object_receive(body, source)` as an explicit gate (a refusal is an ordinary left-behind with the 跟丟了 notice), then moves with `move_to(destination, quiet=True, move_hooks=False)` so `PlayerCharacter.at_post_move` side effects (action options, arrival lore, story encounter activation) never fire for a body nobody is playing; the commander's `record_arrival` is called explicitly once. Wilderness moves use the provider API with the same pre-check.
- **Wilderness**: the possessed puppet keeps a shared wilderness room alive; a body left behind by a failed follow may sit in a recycled room with `location=None`, so co-location for the body uses the existing registration predicate (`_companion_co_located`), and presence checks treat it as absent until it rejoins.
- **Compensation**: the movement snapshot records every follower (owner body included) and `_compensate_companions` restores them; the possession mirror is not touched by movement.
- **Notification** goes to the traverser's sessions, which is what the player sees while possessing.

## Risks / Trade-offs

- [Owner-body hooks firing as a player arrival] → Tests assert no action-options regeneration, dialogue clearing or encounter activation is attributed to the unpuppeted body.
- [Behaviour change for players used to leaving the body behind] → Intentional per the user decision.

## Migration Plan

Pre-release; existing separated parties stay separated until their next traversal from a shared room. Revert the implementation commit to roll back.

## Verification and documentation ownership

EvenniaTest: possessed grid, wilderness entry, wilderness step and return traversals bring body and companions; failed follow leaves only the failing member and one notice; injected clock failure returns traverser, body and companions; release after a possessed walk leaves both figures in the destination room; player traversal unchanged. Observability lint (event context), shard registration, `tools.contract_gate`. No command syntax change, so command docs are unchanged; the 說明 party help text (`party-management-acceptance`) mentions that the party follows a possessed companion.
