# Spec Delta

## MODIFIED Requirements

### Requirement: The session never dispatches compression for the foe-overwhelming direction
No combat-session submission SHALL reach `resolve_overwhelm()` by any path. Every interactive
encounter SHALL resolve its one completed round through `combat.run_round()` alone — whatever
`classify_overwhelm()` decides and whatever the submitted action aims at — so a player-overwhelming,
foe-overwhelming or contested encounter all face the same ordinary per-round round and no interactive
entry point compresses. `world/rules/overwhelm.py`'s resolver SHALL remain an independent
non-interactive mechanism that no session entry point calls.

#### Scenario: Foe-overwhelming encounters never reach the resolver in production
- **WHEN** every production call site of `resolve_overwhelm()` is inspected
- **THEN** no combat-session entry point is among them, and no call site passes a foe-team verdict

#### Scenario: The verdict alone does not reach the resolver
- **WHEN** `submit_opening_action()` runs for a non-damaging skill in an encounter whose
  `classify_overwhelm()` decides for the player's team
- **THEN** `resolve_overwhelm()` is not called, and the seed either waits for the remaining required
  actors or resolves exactly one ordinary round

#### Scenario: In-session submissions cannot reach the resolver
- **WHEN** `submit_player_action()` and `submit_player_item_use()` are called for a session whose
  `classify_overwhelm()` decides for the player's team
- **THEN** neither reaches `resolve_overwhelm()`, and each resolves exactly one ordinary round

#### Scenario: Each unmet condition leaves the resolver uncalled
- **WHEN** the encounter has a foe-overwhelming verdict, a contested verdict, a non-damaging skill,
  or a damaging skill aimed away from the opposing team
- **THEN** each of these leaves `resolve_overwhelm()` uncalled, resolving through the ordinary round
  path instead
