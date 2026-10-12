# Spec Delta

## ADDED Requirements

### Requirement: Dream dispatch and activation emit correlated boundary events

Confirmation handoff, claims, waiting/failure, publication, recovered execution and actual activation SHALL emit facade events with stable English identifiers and available request/version, owner, work/stage, process token, decision, thread, package, scene, tick and call_id context. Credentials SHALL remain filtered; full prompts SHALL remain in transcripts. Exceptions SHALL be reported through the facade and logs SHALL NOT widen in-world knowledge.

#### Scenario: Saved source correlates stages and activation
- **WHEN** a confirmed version completes background generation, publication and encounter activation
- **THEN** boundary events identify the same durable source/work and available stage/publication identities, with the actual guarded call IDs and no fabricated pre-call identifier

#### Scenario: Waiting recovery and failure are distinguishable
- **WHEN** work waits for capability, resumes an interrupted stage or fails during settlement
- **THEN** distinct stable events carry structured reasons and available correlation context, and an exception path includes the facade exception argument

#### Scenario: Secret and multiline payload handling
- **WHEN** generation diagnostics contain credentials, long multiline prose and full messages
- **THEN** credential filtering excludes secrets, prose context follows the existing 200-character single-line bound and full permitted payload is retrieved by transcript call ID
