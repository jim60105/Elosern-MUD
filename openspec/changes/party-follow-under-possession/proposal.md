# Proposal: The whole party follows a possessed traversal

## Why

User decision (2026-10-18, follow-up to the party member management batch for `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`): while the player possesses a companion, the whole party — including the player's own body — follows the possessed body, so same-party members are always in the same room. Today `world/rules/party.py::follow_companions` returns early for any traverser that is not a `PlayerCharacter`, so a possessed companion walks away alone and the owner's body and other companions stay behind. The party-wide settlement, member presence checks and the "possession-identical" party window all rely on co-location.

## What Changes

- **Amendment of a previous non-goal.** The 2026-10-18 design listed "no change to possession entry or exit rules"; this change deliberately amends possession *movement*: a possessed traversal now brings the commander's body and every other present effective companion along. Entry and exit (possess / 歸位) rules are unchanged.
- `follow_companions(traversing_object, ...)`: the follower set is derived from effective membership via `resolve_commander` (`party-member-authority`) instead of requiring the traverser to be the player: the commander's body (when the traverser is a possessed companion) plus every effective companion other than the traverser that is co-located in the source room (room or wilderness registration).
- The owner body moves with quiet `move_to` / the wilderness provider API, is never puppeted, keeps its possession mirror and entranced line, and its map knowledge records the destination; the quest arrival re-observation runs for the commander.
- `movement_settlement.py` snapshots and compensates every follower, including the owner body, for a possessed traversal.
- The one 跟丟了 notification goes to the acting session (the possessed puppet).
- `companion-possession-transition`'s remote-companion release scenario now describes the only remaining separation: a failed follow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `party-system`: the follow requirement derives followers from effective membership and includes the owner body.
- `movement-settlement-atomicity`: compensation covers every follower of a possessed traversal.
- `companion-possession-transition`: the remote-position release scenario describes a failed follow.

## Impact

- `world/rules/party.py` (`follow_companions`, `_reobserve_quest_arrival`), `world/rules/movement_settlement.py` (`_snapshot_movement_state`, `_compensate_companions`), `typeclasses/exits.py` (`record_arrival` for the commander when it followed).
- Tests: `world/rules/tests/test_party_follow_possession.py` (sharded), updates to existing follow and possession transition tests.
- Observability: existing `party_follow_*` events gain `possessed` context; lint runs.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **2 of 32**.

- depends-on: party-member-authority

### Code and spec conflicts within the new batch

- `party-rest-move-settlement`: shared files `world/rules/movement_settlement.py`, `typeclasses/exits.py`, `world/rules/movement.py` callers (F; this change first, the settlement change then charges the travelling party including the owner body).
- `party-member-authority`: uses `resolve_commander` (D).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. Builds on the archived `fix-possessed-companion-room-location` (release room preservation, D4 owner-body guard), which stays intact.
