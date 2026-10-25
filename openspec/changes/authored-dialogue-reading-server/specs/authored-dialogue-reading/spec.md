# Spec Delta

## Purpose

Provide narrative-owned formal reading, delivered receipts and pure-chain synchronization through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

### Requirement: Formal reading is persistent owner-shared narrative state
Formal completion SHALL persist by owning player, host and stable topic identity and synchronize to that owner current connections. Refusal, opening, abandoned and failed text-emission playback SHALL not complete a formal topic. Variant changes and relocking SHALL not erase completion.

#### Scenario: Possession shares completion
- **WHEN** a possessed body completes a formal topic and the owner later opens the same host
- **THEN** the same topic remains read without copying body-local state

#### Scenario: Concurrent duplicate completion
- **WHEN** two valid connections acknowledge the same delivered topic
- **THEN** one monotonic completion persists and both see saved server state, with no repeated gameplay effect

### Requirement: Completion accepts only delivered context-bound content
The server SHALL accept acknowledgement only for a retained server-issued formal delivery in the authenticated current context. Delayed valid deliveries from other topics SHALL remain acknowledgeable after a newer selection. Stale, foreign, refused or forged deliveries SHALL write nothing.

#### Scenario: Delayed completion after another topic
- **WHEN** topic A was delivered, topic B is now playing and A completion retries
- **THEN** A is saved if its receipt/context remain valid and B playback is not replaced

#### Scenario: Forged or stale receipt
- **WHEN** an acknowledgement names another owner, undelivered content, refusal or a retired phase
- **THEN** no read/predecessor state or game effect changes

### Requirement: Public reading chains never authorize protected content
Pure public successor scenes SHALL be effect-free and reveal in predecessor order with persisted progress. Protected qualified descendants SHALL remain absent from pre-delivered bundles and SHALL require saved formal predecessors plus server qualification.

#### Scenario: Chain acknowledgement arrives out of order
- **WHEN** a public successor completion reaches the server before its predecessor
- **THEN** it is refused until predecessor completion saves, and no reward or protected body is released

#### Scenario: Successful text chain emission
- **WHEN** a non-paged text client receives a public root and successor in order
- **THEN** each complete successful attributed emission records the same owner reading state without per-line timing proof

