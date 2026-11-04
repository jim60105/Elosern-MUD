# Spec Delta

## MODIFIED Requirements

### Requirement: A successful flee adds the fleeing entity's key to Battlefield.fled; a failed attempt
Individual flee SHALL preserve the existing agility contest and stable fled identity, require a committed legal affordable journey in mapped combat, and use explicit abstract context in standalone combat; allied interactive escape SHALL retain confirmed party retreat.

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

#### Scenario: Mapped flee departure
- **WHEN** a mapped enemy succeeds through the resolver
- **THEN** fled state and actual source departure commit together; failure preserves position/group and no abstract world fallback is selected
