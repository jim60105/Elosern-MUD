# party-follow

## Why

`party-core` binds up to four NPC companions, but a bound companion is inert: the player can walk
away and the NPC stays behind. This change makes companionship visible — companions follow the
player through exits via the single shared traversal pipeline, with no time cost and no clock
charge, and report "跟丟了" when they cannot follow. The follow behavior is the mechanical core
the later combat and quest changes assume ("companions are present where the player is").

## What Changes

- **Follow on every exit success path.** The follow function is invoked from all three real
  traversal success paths: the shared `MovementCostMixin.at_post_traverse` hook (grid, instance,
  and base exits), the wilderness gate entry branch, and the wilderness return/step branches —
  the wilderness exits perform their own traversal and never reach the shared hook.
- **Silent, costless companion movement.** Companions move with no world-clock charge (the clock
  advances only on player action), no announce messages, and no player-gated observer side
  effects (the project's room observers are all PlayerCharacter-gated). Grid/instance moves use
  quiet `move_to`; wilderness entry and steps go through the provider's coordinate API
  (`enter_wilderness` / `move_obj`) — never a plain `move_to` into a wilderness room, whose
  `at_object_receive` rejects Evennia's `move_type` kwarg after the location was already set.
- **跟丟了 handling.** A companion whose move fails stays put and the player receives one fixed
  Traditional Chinese notification per traversal naming every companion left behind; the
  companion remains bound and rejoins naturally when the player traverses from its room.
- **Exit traversal only.** Teleports, spawns, and other non-exit relocations do not pull
  companions; a bound companion in another room is never teleported to the player; stale party
  entries (deleted NPCs) are skipped without raising.
- **No new commands, no new UI, no command-docs changes.**

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `party-system`: The membership capability gains the follow requirement — companions move with
  the player through exit traversal, costless and silent, with the 跟丟了 fallback and the
  exit-only scope.

## Impact

- **New code**: the follow function in `world/rules/party.py` (or a dedicated
  `world/rules/party_follow.py`) plus its test module.
- **Modified**: `typeclasses/exits.py` (the `MovementCostMixin.at_post_traverse` hook calls the
  follow function), `openspec/specs/party-system` (delta added at archive time).
- **Dependencies**: `party-core` (membership binding), `map-movement-clock` (the shared
  post-traversal hook).
- **Out of scope**: joint combat (`party-combat`), quest assistance and the +2 completion bonus
  (`party-quest`), companion pathfinding or re-summoning, auto-teleport following.
