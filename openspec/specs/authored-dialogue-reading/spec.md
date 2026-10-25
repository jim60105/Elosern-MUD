# authored-dialogue-reading Specification

## Purpose
Provide narrative-owned formal reading, delivered receipts and pure-chain synchronization through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## Requirements

### Requirement: Generated reading persists by logical package-role identity
Reading SHALL use the owning player, stable logical host and source-aware topic identity for both providers. Generated phase/binding retirement SHALL invalidate receipts without erasing saved completion. Physical role dbid changes or save/reload SHALL not reset logical reading.

#### Scenario: Role rematerialization retains completion
- **WHEN** a published package role with saved reading resolves to a new physical dbid
- **THEN** its same-phase topics retain completion while old physical-context receipts reject

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

### Requirement: Generated acknowledgements use the same memory-only lifecycle
Static/generated completion SHALL share one exact-ID in-memory retry/ordering state machine. Phase/control retirement SHALL discard obsolete pending memory while retaining server reading. Generated identifiers SHALL be preserved without truncation.

#### Scenario: Generated phase retires pending completion
- **WHEN** a generated completion is pending and its phase context retires
- **THEN** the client discards the stale queue entry and uses current server reading without completing new-phase content

### Requirement: Frontend completion retries remain memory-only
After explicit formal-scene finish, the client SHALL retry a failed completion acknowledgement in memory without requiring immediate rereading. It SHALL distinguish pending from saved and discard pending state on fresh reload, character exit or context retirement. No durable browser completion queue SHALL exist.

#### Scenario: Retry without rereading
- **WHEN** completion transport fails after the final explicit activation, then same-context transport recovers
- **THEN** the exact acknowledgement retries without another selection/effect and only saved response clears pending status

#### Scenario: Reload discards pending
- **WHEN** the app reloads before a failed acknowledgement saves
- **THEN** server unread/predecessor state wins and latest valid delivery restarts at line one

### Requirement: Optimistic public reading cannot unlock qualified topics
Local pending completion SHALL reveal only already delivered public-chain successors. Qualified topics SHALL wait for server-saved predecessors and current server eligibility. Unrelated reading updates SHALL not restart or auto-advance current playback.

#### Scenario: Pending public successor
- **WHEN** a root is locally finished but its acknowledgement is pending
- **THEN** its pre-delivered public successor can play and queues completion after predecessor, while protected descendant remains absent

#### Scenario: Other connection saves
- **WHEN** another current connection completes a topic while this connection reads another scene
- **THEN** markers synchronize without stealing focus or changing the current line
