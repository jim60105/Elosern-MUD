# Spec Delta

## MODIFIED Requirements

### Requirement: Entry gates are deterministic, stable-coded, and precede all generative work
Possession SHALL resolve the same canonical effective party membership for general and temporary companions. Existing ordered stable-coded gates `not_bound`, `not_co_located`, `in_combat`, `dialogue_open`, and `already_possessing`, together with existing living-state restrictions, SHALL apply before any generative work or write. Only a validated contextual sleep-driven handoff SHALL relax in_combat and replace an existing possession through one verified transfer; all membership, co-location, living/action, dialogue and account-scope checks SHALL remain binding. Account-wide single-possession scope and fixed reason messages SHALL remain unchanged.

#### Scenario: Temporary membership permits ordinary possession
- **WHEN** a live temporary-only companion passes every existing entry gate
- **THEN** the existing possession transaction and puppet-transfer ladder control that exact NPC and retain the original player as owner

#### Scenario: Temporary status waives no gate
- **WHEN** a temporary target is remote, unavailable, in combat, in dialogue, or the account already possesses an NPC
- **THEN** the existing corresponding refusal writes no possession state

#### Scenario: Every gate names its reason with zero writes
- **WHEN** each of the five gate conditions is provoked individually
- **THEN** the matching `PossessionGateError` reason surfaces with its fixed message and neither possession attribute changes

#### Scenario: One account possesses at most one NPC
- **WHEN** the account's character A possesses companion X, and (through a second session or another character) an unrelated possession of Y is attempted
- **THEN** `already_possessing` refuses the second possession

#### Scenario: The bound and co-location gates
- **WHEN** the target is not a live bound companion of this player, or is not co-located
- **THEN** `not_bound` or `not_co_located` refuses accordingly

#### Scenario: The combat gate reuses the party helper
- **WHEN** either side is in an active combat session and the operation is not a validated sleep-driven handoff
- **THEN** `in_combat` refuses, using the same `is_in_active_session` helper the party-adjustment
  boundary uses

#### Scenario: The dialogue gate checks for an open session
- **WHEN** the NPC has an open dialogue session
- **THEN** `dialogue_open` refuses

#### Scenario: The already-possessing gate scans the account's own characters only
- **WHEN** an ordinary entry finds the player already possesses another NPC, or this account's other characters already possess
  any NPC
- **THEN** `already_possessing` refuses, scanned over the account's own characters only

## ADDED Requirements

### Requirement: Sleep-driven handoff is contextual and requires confirmation
Only committed sleep incapacitation of the currently controlled body SHALL offer a handoff to an awake living action-capable co-located effective member or awake owner. Choices SHALL identify current fatigue and return-versus-possession semantics. No candidate SHALL be chosen automatically; selection/cancel SHALL preserve commander and combat draft with no time.

#### Scenario: Possessed sleeper returns home
- **WHEN** a controlled companion enters voluntary sleep while its owner is awake
- **THEN** the zero-time entry offers explicit return to that owner before elapsed sleep; owner actions may then recover the companion without making the owner asleep

#### Scenario: Unselected transition
- **WHEN** an unselected companion falls asleep or a sleeping owner wakes
- **THEN** only status changes; no mandatory prompt or automatic repuppeting steals the current selection

#### Scenario: Cancel
- **WHEN** the player closes handoff while controlling a sleeper
- **THEN** no time passes, no completed sleep is claimed, and only non-acting status/recovery controls remain

### Requirement: Handoff confirmation revalidates the exact candidate
Confirmation SHALL rederive authenticated account/session, current unavailable body, commander, party membership, co-location, awake/living/action state and existing possession restrictions. Stale/ineligible choices SHALL reject with a stable reason and current candidates without substitution. Remote possession and nested possession SHALL remain impossible.

#### Scenario: Stale candidate
- **WHEN** a listed candidate moves, sleeps, leaves, dies or changes account session before confirmation
- **THEN** the request changes no binding/time/draft and returns current choices, never a substitute

#### Scenario: Combat exception stays narrow
- **WHEN** ordinary possess is attempted during combat without current-body sleep incapacitation
- **THEN** existing in_combat refusal remains; a lawful contextual handoff alone may use the exception

