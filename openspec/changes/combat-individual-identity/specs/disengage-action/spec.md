# Spec Delta

## MODIFIED Requirements

### Requirement: A successful flee adds the fleeing entity's key to Battlefield.fled; a failed attempt
An enemy or noninteractive individual flee SHALL add only the actor's stable individual identity to the fled set on success and mutate no participant state on failure; allied interactive escape SHALL retain confirmed whole-party retreat.

#### Scenario: A successful flee is reflected in Battlefield.fled after commit
- **WHEN** a `flee` request resolves successfully with the underlying attempt succeeding
- **THEN** the actor's stable individual identity is present in `battlefield.fled` after `resolve()` returns

#### Scenario: A failed flee attempt leaves Battlefield.fled unchanged
- **WHEN** a `flee` request resolves with the underlying attempt failing
- **THEN** the actor's stable individual identity is absent from `battlefield.fled` after `resolve()` returns, and no entity's
  `traits`, `sexual`, `buffs`, or `skill_grants` values differ from their pre-call state

#### Scenario: Both outcomes still produce a real EventLog
- **WHEN** a `flee` request resolves, whether the underlying attempt succeeds or fails
- **THEN** `ActionResult.success()` returns a non-`None` `event_log` containing an entry describing the
  attempt's outcome, and the standard flat time cost is reported in both cases

#### Scenario: Allied interactive escape uses party confirmation
- **WHEN** an allied actor in an interactive player session requests this innate flee mechanism
- **THEN** the request is routed to confirmed party retreat before any individual effect mutates the battlefield; enemy individual flee keeps the mechanism above unchanged

### Requirement: A fled entity is immediately excluded from targeting, turn order, and team-power
aggregation through existing combat and overwhelm mechanics
Once `battlefield.fled` contains an entity's stable individual identity, `world.rules.combat.BattlefieldActionContext.
is_present()`/`is_in_range()`, `world.rules.combat.run_round()`'s turn-order loop, and
`world.rules.overwhelm.team_effective_power()`/`hit_rate_verdict()` SHALL all treat that entity as no
longer part of the encounter, using their existing, unmodified implementations.

#### Scenario: A fled entity is skipped by run_round's initiative loop
- **WHEN** `combat.run_round(battlefield, action_provider)` is called on a battlefield where one roster
  member's stable individual identity is in `battlefield.fled`
- **THEN** that member takes no action that round, using `run_round()`'s existing fled-member filter;
  this change does not modify that function to produce the behavior

#### Scenario: A fled entity contributes zero to its team's power aggregate
- **WHEN** `overwhelm.team_effective_power(battlefield, team_key)` is computed for a team containing one
  fled member and one living, non-fled member
- **THEN** the result equals the living, non-fled member's own `effective_power()` value exactly, using
  `overwhelm.py`'s existing, unmodified filtering logic

#### Scenario: A fled entity cannot be targeted by any skill
- **WHEN** any `TargetSpec.SINGLE` skill is resolved against a target whose stable individual identity is in `battlefield.fled`
- **THEN** it rejects with `RejectReason.TARGET_OUT_OF_RANGE`, via `BattlefieldActionContext.
  is_in_range()`'s existing, unmodified behavior

