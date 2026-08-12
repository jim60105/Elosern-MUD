## MODIFIED Requirements

### Requirement: Companions fight as allies in the player's combat session
When the player engages a hostile target, `engage` SHALL include every bound companion that is
co-located, living, and not knocked out in the session's allied team (`player_ids`). The
battlefield's two-team model SHALL treat companions as allies: `relation_to` returns ALLY for
them, freely-targetable (ANY) skills and the `all-allies` shorthand may include them, and the
player SHALL be able to select companions as explicit damage targets — companion hits apply the
friendly-fire penalty contract (affinity-friendly-fire) rather than being rejected; opposing-team
combatants SHALL be able to target companions. Each companion SHALL receive at most one
deterministic policy request per round through the session's non-player action provider (the same
`monster_behaviour_policy` pipeline monsters use, whose target selection is team-relative), and
SHALL NOT consume or delay the player's queued request.

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

#### Scenario: A damage skill may select a companion as its explicit target
- **WHEN** the player resolves a freely-targetable (ANY) damage skill with a companion as the
  explicit target
- **THEN** the companion appears among the selectable targets and the hit applies the
  friendly-fire penalty contract instead of being rejected at the faction check

#### Scenario: A companion's fallback policy attacks the opposing team without fleeing
- **WHEN** a companion (which has no monster threat tier) acts through the policy provider
- **THEN** its request targets an opposing-team combatant and is never a flee request
