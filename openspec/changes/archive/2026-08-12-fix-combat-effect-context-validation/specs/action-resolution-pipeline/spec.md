## ADDED Requirements

### Requirement: Preflight rejects missing handler context before any round cost

`ActionResolver.preflight()` and the combat-session revalidation SHALL verify that every effect handler's declared context keys are present in the submitted `event_context`; a missing key SHALL reject the action before initiative, round count, upkeep, or world time changes.

#### Scenario: Missing disguise context rejects before initiative

- **WHEN** a player submits `status_disguise` in combat without `event_context.disguise`
- **THEN** the action is rejected at preflight, no round is consumed, and the enemy does not act

#### Scenario: Missing dominion context rejects before initiative

- **WHEN** a player submits `dominion_art` without `confer_skill_key`/`confer_scale`/`confer_trait_keys`
- **THEN** the action is rejected at preflight, no round is consumed, and the enemy does not act

#### Scenario: Out-of-combat casts with supplied context still work

- **WHEN** a player casts `status_disguise` out of combat with the disguise context supplied by the command
- **THEN** the cast resolves normally
