# Spec Delta

## MODIFIED Requirements

### Requirement: Fixed-title grants ride the triggering action's atomic transaction
A registered event-effect planner SHALL evaluate pending predicates against the step-7 EventLog (non-EventLog faces read through the existing shared read helpers) and stage fixed-title grants as `PendingEffect` values committed inside the triggering action's own transaction; collection membership short-circuits re-grants, so a staged-then-rolled-back grant re-applies naturally when its events next appear and nothing can be written twice. Quest-completed predicates SHALL be excluded from action-time discovery; the completing quest owner SHALL settle them through the unified automatic award entry point under the completion occurrence.

#### Scenario: A predicate-satisfying kill grants inside the same commit
- **WHEN** an action commits an EventLog satisfying a `first_kill_tier` predicate
- **THEN** the fixed entry (with `granted_tick`) is in `title_collection` at that transaction's commit, atomically with the action's other effects

#### Scenario: Planner rollback cannot double-grant
- **WHEN** a staged grant is rolled back and a later action reproduces the same qualifying events
- **THEN** exactly one entry exists afterwards

#### Scenario: A live grant pushes one notification
- **WHEN** a fixed-title grant commits successfully on a live session
- **THEN** one OOB notification (「獲得稱號：屠龍者」) is pushed

#### Scenario: Quest completion awards do not wait for a later action
- **WHEN** a newly completed quest satisfies a synthetic registered quest-completed title predicate
- **THEN** the completion settlement grants and attributes that title before its fact commits; an unrelated later skill action does not rediscover the completion under its own source

### Requirement: Award evidence finalizes atomically and survives replay
Title writes, automatic award results and source evidence SHALL share the source settlement transaction, including when a nested completion owner writes inside an outer purchase, delivery, action or reward transaction. Award results SHALL be finalized before immutable event persistence. Replaying a committed occurrence SHALL retain its original grant results and SHALL NOT replace them with an empty replay result.

#### Scenario: Rollback after writes
- **WHEN** a fault follows gameplay, title, award and narrative writes before outer commit
- **THEN** all durable and cached gameplay/title state and related records return to their prior values

#### Scenario: Replay keeps suppression evidence
- **WHEN** the same committed source settles again after its title is already owned
- **THEN** one source remains and its original nonempty award results are returned unchanged

#### Scenario: Completion grants finalize before the event
- **WHEN** one committed quest completion newly grants several synthetic built-in titles
- **THEN** all results use that completion source, are present when the immutable fact is first committed, and suppress its immediate player notification through the generic award contract

#### Scenario: Outer completion owner fails after the inner writer
- **WHEN** purchase, delivery, action or automatic-chain settlement fails after completion title and evidence writes but before outer commit
- **THEN** gameplay, title collection and equipped state, award evidence, events and pending projection work restore in durable storage and warmed caches

#### Scenario: Replay preserves original completion awards
- **WHEN** a committed completion with nonempty awards is replayed after those titles are already owned
- **THEN** its original immutable results are returned without new grants, additional evidence or loss of source suppression

## ADDED Requirements

### Requirement: Quest completion awards use completion occurrence attribution
Quest-completed built-in-title grants SHALL use the completion occurrence source and the unified automatic award contract within that settlement. Existing ownership SHALL produce no new grant for a new occurrence. Recipient-specific immediate suppression SHALL require no event-type exception. The starter epithet SHALL remain attributed to its separate reward claim.

#### Scenario: Synthetic future completion title uses the unchanged service
- **WHEN** a synthetic new quest-completed title is registered and real quest completion sends its normal notification
- **THEN** the nominated recipient is suppressed without service changes and the deed remains usable at later wake or logout

#### Scenario: Other recipients and old ownership do not suppress
- **WHEN** only another recipient gains a title or a new completion merely encounters a title the player already owns
- **THEN** that completion is not suppressed by the player's award-result rule

#### Scenario: First reward claim retains its own source
- **WHEN** a completed quest is later claimed for its first guild reward
- **THEN** the authored starter epithet is awarded under the reward claim rather than retroactively patched into the completion fact
