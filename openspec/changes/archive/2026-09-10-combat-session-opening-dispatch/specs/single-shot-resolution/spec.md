## MODIFIED Requirements

### Requirement: The session never dispatches compression for the foe-overwhelming direction
`world/rules/combat_session.py::submit_opening_action()` SHALL be the only production call site of
`resolve_overwhelm()`. It SHALL invoke the resolver only when both conditions hold: the player's team
is the overwhelming side per `classify_overwhelm()`, **and**
`overwhelm.commanded_damage_reaches_enemy()` reports that the submitted skill damages a member of
the opposing team. A foe-overwhelming verdict, a contested verdict, a non-damaging skill, and a
damaging skill aimed away from the opposing team SHALL each leave the resolver uncalled. No
submission made inside an already-active session SHALL reach the resolver by any path.

#### Scenario: Foe-overwhelming encounters never reach the resolver in production
- **WHEN** every production call site of `resolve_overwhelm()` is inspected
- **THEN** the only one is `submit_opening_action()`'s dispatch, it is gated on the player's team
  being the overwhelming side, and no call site passes a foe-team verdict

#### Scenario: The verdict alone does not reach the resolver
- **WHEN** `submit_opening_action()` runs for a non-damaging skill in an encounter whose
  `classify_overwhelm()` decides for the player's team
- **THEN** `resolve_overwhelm()` is not called and exactly one ordinary round resolves

#### Scenario: In-session submissions cannot reach the resolver
- **WHEN** `submit_player_action()` and `submit_player_item_use()` are called for a session whose
  `classify_overwhelm()` decides for the player's team
- **THEN** neither reaches `resolve_overwhelm()`, and each resolves exactly one ordinary round
