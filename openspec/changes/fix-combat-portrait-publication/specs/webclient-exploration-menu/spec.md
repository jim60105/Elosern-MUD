# Spec Delta

## MODIFIED Requirements

### Requirement: explore.engage delegates to the existing engage contract
The production action registry SHALL register `explore.engage`. Its payload SHALL accept exactly `monster_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session, re-resolve the monster from the actor's current location's present contents, and call `world.rules.combat_session.engage(actor, monster)`.

#### Scenario: Engage transitions to the combat dock
- **WHEN** an actor submits `explore.engage` for a present living hostile monster
- **THEN** `engage` returns its record, the update carries mode `combat`, a `context_actions` combat payload and a freshly rendered `art` catalog for those participants, the exploration dock unloads, and no exploration mutation is admitted in combat mode

#### Scenario: Engage rejects a remote or non-hostile target
- **WHEN** an actor submits `explore.engage` for a target that is absent, dead, or not a hostile `Monster`
- **THEN** the adapter rejects with a stable reason, no session is created, and the exploration dock remains usable

#### Scenario: Monster resolution never trusts stale or remote references
- **WHEN** the `explore.engage` adapter re-resolves the monster
- **THEN** it resolves only from the actor's current location's present contents — never a stored, remote, or ambiguous reference

#### Scenario: Engage re-verifies its contract and records the overwhelm class
- **WHEN** the adapter calls `engage`
- **THEN** it re-verifies a `PlayerCharacter` with no active session, a living hostile `Monster` in the same room, and records the initial overwhelm classification

#### Scenario: The engage adapter never touches combat state directly
- **WHEN** the `explore.engage` adapter runs
- **THEN** it does not assign session, battlefield, skip-safety, or location state directly and does not run any combat action

#### Scenario: A successful engage switches mode and refreshes both panels
- **WHEN** an engage succeeds
- **THEN** completion publishes status, context_actions, dialogue and art at one newer revision with mode combat; every non-null participant portrait_ref resolves in that same catalog before the correlated result releases the action gate, and services/exploration remain unavailable in combat

#### Scenario: An engage rejection creates nothing
- **WHEN** an engage is rejected
- **THEN** the completion publishes the safe stable reason and does not create a session or advance time

