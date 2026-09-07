# party-system delta

## MODIFIED Requirements

### Requirement: Party membership is bounded, persistent, and single-writer

`world/rules/party.py` SHALL be the sole writer of party membership: `player.db.party` holds the list of companion NPC dbids (at most 4) and each companion's `npc.db.party_member` holds the player's dbid. `join_party(npc, player)` SHALL require an NPC target, co-location (same room), no existing binding, and a party below the 4-companion bound; `leave_party(npc, player, reason)` SHALL remove the binding regardless of the reason. Both SHALL commit the player-side and NPC-side writes atomically, SHALL restore both entities' in-process caches on failure, SHALL be idempotent under re-application, and SHALL survive reloads. `join_party` SHALL have exactly two production callers: the player-initiated invite path, and preset activation binding a declared starting companion. Neither caller SHALL assign `player.db.party` or `npc.db.party_member` itself, and a companion bound at activation SHALL be indistinguishable from an invited one for every later party operation — follow, combat, quest assist, dismissal, and the auto-leave recheck.

#### Scenario: A valid join binds both sides
- **WHEN** a player invites a co-located NPC with 2 companions already
- **THEN** the NPC appears in `player.db.party`, the NPC's `party_member` is the player, and the party size is 3

#### Scenario: The party bound is four companions
- **WHEN** a player with 4 companions invites a fifth NPC
- **THEN** the join is rejected with a full-party outcome and no binding changes

#### Scenario: A remote NPC cannot join
- **WHEN** a player invites an NPC in another room
- **THEN** the join is rejected and no binding changes

#### Scenario: A duplicate join is a no-op
- **WHEN** a join is attempted for an NPC already bound to the player
- **THEN** the join is rejected and no binding changes

#### Scenario: A failed join restores both entities
- **WHEN** the NPC-side write fails after the player-side write applied
- **THEN** both database and in-process values return to their pre-join state and no partial binding is observable

#### Scenario: Membership survives a reload
- **WHEN** a player with companions disconnects and reconnects
- **THEN** `player.db.party` and each companion's `party_member` are unchanged

#### Scenario: An activation-bound companion behaves like an invited one
- **WHEN** a starting companion bound at activation is exercised through follow, combat, quest assist, and dismissal
- **THEN** every operation behaves exactly as it does for an invited companion, with no origin-dependent branch
