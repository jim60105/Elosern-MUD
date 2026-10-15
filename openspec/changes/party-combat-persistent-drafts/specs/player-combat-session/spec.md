# Spec Delta

## ADDED Requirements

### Requirement: Confirmed round selections persist as one editable session draft
Each session SHALL store one JSON-safe next-round draft bound to session identity and round revision, with at most one confirmed closed-kind command per required actor. Entries SHALL contain validated identities and payload values, never live objects. Before completion, an entry SHALL be replaceable without executing it.

#### Scenario: Replace earlier selection
- **WHEN** two allies need commands and the first confirmed actor chooses another skill or item before the second confirms
- **THEN** the new entry replaces its prior entry; no dice, enemy policy, upkeep, resource deduction or time runs

#### Scenario: Stable serialization
- **WHEN** a confirmed skill, item or tactical command is committed and loaded afresh
- **THEN** its actor/action/target/scale data reconstructs from validated identities without persisted live references


### Requirement: Draft completeness is derived again from authoritative membership
Every confirmation and complete-draft preflight SHALL reevaluate required actor membership and all commands. Invalid entries SHALL produce per-member reselection reasons while retaining valid entries. A changed required set SHALL require a fresh explicit confirmation rather than silently executing an old incomplete draft.

#### Scenario: Changed roster
- **WHEN** an ally joins, leaves or becomes unable to act while choices are collected
- **THEN** required progress updates without a round, valid entries remain and missing or invalid choices are reported

#### Scenario: Resources or equipment change
- **WHEN** an earlier selected command is no longer valid when the final member confirms
- **THEN** no initiative or upkeep starts, invalid entries require replacement and unaffected entries remain


### Requirement: Draft editing has a separate stale-write version
Draft edits SHALL carry the current session identity, round_revision and draft_version. An admitted edit SHALL increment draft_version. A stale or concurrent edit SHALL reject without overwriting a newer confirmed entry or affecting another session or round.

#### Scenario: Concurrent replacement
- **WHEN** two requests edit the same old draft version
- **THEN** at most one edit is admitted and the other receives canonical progress without overwrite


### Requirement: Reconnect and restart restore confirmed selection progress without execution
Confirmed entries SHALL survive disconnect and process restart. Reconnection SHALL restore their session/revision/progress and SHALL NOT invent missing commands, activate tactical choices or advance combat. Session termination SHALL clear its active draft.

#### Scenario: Restart unfinished draft
- **WHEN** one of several members has a confirmed command when transport or process restarts
- **THEN** the confirmed entry remains, missing members remain unselected and elapsed rounds/time are unchanged


