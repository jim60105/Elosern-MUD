## ADDED Requirements

### Requirement: Companions fight as allies in the player's combat session
When the player engages a hostile target, `engage` SHALL include every bound companion that is
co-located, living, and not knocked out in the session's allied team (`player_ids`). The
battlefield's two-team model SHALL treat companions as allies: `relation_to` returns ALLY for
them, ALLY-targeting skills and the `all-allies` shorthand may include them, and the player's
ENEMY-targeting skills SHALL NOT select them; opposing-team combatants SHALL be able to target
companions. Each companion SHALL receive at most one deterministic policy request per round
through the session's non-player action provider (the same `monster_behaviour_policy` pipeline
monsters use, whose target selection is team-relative), and SHALL NOT consume or delay the
player's queued request.

#### Scenario: Co-located living companions join the engagement
- **WHEN** a player with two co-located living bound companions engages a monster
- **THEN** both companions are in the session's allied team, the battlefield roster contains them,
  and the party binding is unchanged

#### Scenario: Distant, dead, or knocked-out companions do not join
- **WHEN** a player's bound companion is in another room, has HP 0, or is marked knocked out
- **THEN** that companion is absent from the session's allied team

#### Scenario: Companions act once per round through the policy provider
- **WHEN** one round runs with a player, two companions, and two monsters
- **THEN** the player's request is supplied exactly once, each companion receives at most one
  deterministic policy request targeting the opposing team, and each monster receives at most one

#### Scenario: The player's enemy-targeting skills never select companions
- **WHEN** the player resolves an ENEMY-targeting skill in combat with companions
- **THEN** no companion appears among the selectable targets

#### Scenario: A companion's fallback policy attacks the opposing team without fleeing
- **WHEN** a companion (which has no monster threat tier) acts through the policy provider
- **THEN** its request targets an opposing-team combatant and is never a flee request

### Requirement: Knocked-out companions are persistent battlefield state and can never die
A companion whose HP crosses from positive to non-positive SHALL be knocked out nonlethally: HP
floors at 1, `target_knocked_out` is emitted, `target_defeated` is not, and no kill credit, XP,
DEFEAT progress, or loot consumer observes a companion death. The knockout SHALL be marked on the
battlefield at damage-commit time, SHALL be persisted in the session record's `knocked_out_ids`,
and SHALL be reconstructed on battlefield rebuild. A knocked-out companion SHALL be excluded from
initiative order, from receiving policy requests, from all target selection (the player's
`all-allies`, opposing-team enemy selection, and AREA shortcuts), from overwhelm classification,
and from the terminal living checks. The knockout marker SHALL clear only when the companion's HP
rises above 1 through the ordinary clock-driven regen; until then the companion SHALL NOT join a
new engagement. The party binding SHALL remain unchanged throughout.

#### Scenario: A companion's lethal crossing becomes a knockout
- **WHEN** a monster's damage would cross a companion's HP from positive to non-positive
- **THEN** the companion's HP floors at 1, `target_knocked_out` is emitted, no `target_defeated`
  entry exists, and the battlefield marks the companion knocked out within the same commit

#### Scenario: Hostile kills stay lethal
- **WHEN** identical damage would cross a monster's HP from positive to non-positive
- **THEN** the ordinary lethal crossing and `target_defeated` behavior apply unchanged

#### Scenario: A knocked-out companion stops acting and cannot be targeted
- **WHEN** a companion is knocked out and the next round runs
- **THEN** the companion receives no policy request, is excluded from the player's `all-allies`
  expansion and from opposing-team target selection, and every remaining participant still acts

#### Scenario: Knockout state survives a rebuild
- **WHEN** a session with a knocked-out companion is reconstructed (e.g. after a reload)
- **THEN** the companion is still excluded from action, targeting, and terminal checks

#### Scenario: A knocked-out companion cannot re-engage before recovery
- **WHEN** a session ends with a companion knocked out and the player engages again before the
  companion's HP rose above 1
- **THEN** the companion does not join the new session's allied team

#### Scenario: Recovery clears the knockout marker
- **WHEN** a knocked-out companion's HP rises above 1 through clock-driven regen
- **THEN** the companion may join a later engagement as a living participant

### Requirement: Combat terminal rules are player-centric
The session SHALL end in defeat when the player (the session owner) is defeated — HP at or below
zero or marked knocked out — even when companions remain standing; it SHALL end in victory when
every opposing-team combatant is defeated or fled; flee, forfeit, and the round cap SHALL behave
unchanged. A knocked-out companion SHALL NOT end the session. Settlement, flee, forfeit,
skip-safety registration, and the party binding SHALL be unchanged by companion participation.

#### Scenario: Player defeat ends the session with companions alive
- **WHEN** the player's HP crosses to zero or the player is knocked out while companions still stand
- **THEN** the session settles its elapsed rounds and clears combat state as an ordinary defeat

#### Scenario: Victory requires only the foes team to be gone
- **WHEN** every foe is defeated or fled while the player and companions remain
- **THEN** the session settles as victory

#### Scenario: A knocked-out companion does not end the session
- **WHEN** a companion is knocked out while the player and foes remain active
- **THEN** the session persists and the player's next action continues the round loop

#### Scenario: Knocked-out companions recover after combat
- **WHEN** a session ends with a companion knocked out at 1 HP
- **THEN** the binding remains and the companion's HP regenerates through the ordinary clock-driven
  regen over subsequent world-time advances, clearing the knockout marker above 1 HP
