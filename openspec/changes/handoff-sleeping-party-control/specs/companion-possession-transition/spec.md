# Spec Delta

## ADDED Requirements

### Requirement: Contextual handoff uses compensated verified control transfer
Sleep-driven handoff SHALL reuse the existing verified puppet/session/lock/cmdset writer and preserve one mirrored possession. Companion-to-companion transfer SHALL complete as one compensated transition. Technical failure SHALL restore truthful prior bindings, session puppet, occupied rooms, locks and cmdsets and offer retry/status without claiming success.

#### Scenario: Failure after releasing old body
- **WHEN** a companion-to-companion handoff fails after an unpuppet or mirrored write
- **THEN** old verified binding, sessions, caches, cmdsets and locations are restored; commander/draft and tick are unchanged

#### Scenario: Lifecycle
- **WHEN** a sleeping possessed member reloads, disconnects, is deleted or loses membership
- **THEN** existing verified cleanup remains the only lifecycle writer; no prompt-specific dangling possession is created

