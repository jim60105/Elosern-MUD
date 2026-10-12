# Spec Delta

## Purpose

Owns durable confirmed-dream execution, bounded background generation and recoverable publication status without creating fictional game effects.

## ADDED Requirements

### Requirement: Each confirmed version has one durable work identity

The system SHALL persist one database-unique work record per creative request/version, carrying owner, source key, state/stage, execution token, snapshot/proposal and publication references, structured reason and tick. Confirmed direction SHALL remain immutable. Work SHALL contain validated stage data and SHALL NOT contain credentials or unrestricted raw transcripts.

#### Scenario: Duplicate and edited confirmations
- **WHEN** a confirmed version is replayed and a separately edited version is explicitly confirmed
- **THEN** replay returns the original work identity and the new version has a distinct source and work record

### Requirement: One server-owned pump processes eligible work in confirmation order

One game-server service SHALL own background claims and allow at most one running story generation. Eligible work SHALL queue in stable confirmation order. Capability-disabled work SHALL wait without blocking other eligible sources. Confirmation and work management SHALL NOT advance game time or await model completion.

#### Scenario: Slow background generation
- **WHEN** a model call stays unresolved while two eligible versions are confirmed
- **THEN** both confirmation responses finish, only one generation runs and the later work remains queued without clock charge

#### Scenario: Disabled stage does not block queue
- **WHEN** an earlier source requires a disabled capability and later work has its required capabilities
- **THEN** the earlier source becomes waiting_service without a model call and the later eligible source runs

### Requirement: Dispatch states distinguish waiting from terminal failure and durable success

Work SHALL expose queued, generating_story, generating_scene, publishing, waiting_service, arranged and failed states. Disabled or absent required profiles SHALL wait before their stage claim. Exhausted bounded generation, validation, unsupported effects or execution errors SHALL fail with a reason and no partial publication. Arranged SHALL require durable accepted result references; readable prose or no eligible arrangement SHALL NOT count as success.

#### Scenario: Terminal failure is not rerolled
- **WHEN** malformed or misfitting output exhausts the existing bounded retries
- **THEN** work becomes failed with its source preserved and later pump notifications do not silently generate a new attempt/source

#### Scenario: Waiting is reconsidered on lifecycle notification
- **WHEN** configuration activation/reload, startup or another pump notification makes a waiting stage available
- **THEN** the same work becomes eligible without a legacy scanner, infinite polling or an independent retry subsystem

### Requirement: Saved checkpoints and fenced execution govern restart

Successful stage output SHALL persist before the next stage. Exclusive service restart SHALL fence interrupted execution tokens and reuse valid saved output when relevant snapshots validate. Only an uncommitted interrupted stage SHALL be regenerated when permitted; committed sources SHALL never generate another package. Shutdown SHALL stop new claims and invalidate unfinished callback ownership without lease-expiry races.

#### Scenario: Restart at each saved boundary
- **WHEN** interruption occurs after saved story output, saved blueprint or immediately before publication
- **THEN** restart uses one source and its valid checkpoints, without duplicate decision/thread/beat/package and without replaying a completed valid model stage

#### Scenario: Stale callback after shutdown
- **WHEN** an invalidated token or old source version delivers output after restart
- **THEN** it changes no work result, publication, dialogue exchange or committed history

#### Scenario: Checkpoint fact becomes contradictory
- **WHEN** a required actor or relevant story fact changed before interrupted execution resumes
- **THEN** current revalidation rejects or regenerates only the uncommitted interrupted stage under the same identity and never ignores the changed fact

### Requirement: Publication commits narrative and executable references together

Settlement SHALL atomically persist the accepted decision, thread linkage, scheduled beat/result, validated scene package where required and source-to-publication linkage. Work SHALL become arranged in that transaction. Failure SHALL restore registration/cache views with no orphan scene, issuer, accepted quest or partially linked beat. Notices and scene fan-out SHALL follow commit and SHALL NOT be the sole evidence of publication.

#### Scenario: Failure after publication writes
- **WHEN** fault injection fails after package or beat writes before commit
- **THEN** no publication/result references survive, affected caches match persisted state and no success notice is sent

#### Scenario: Crash after commit before notice
- **WHEN** publication commits and fan-out is lost
- **THEN** restart/reconnect reads the same arranged publication without another package, NPC, offer or reward

### Requirement: Status feedback follows the current legal owner mapping

Ordinary output SHALL distinguish confirmation receipt, preparation, waiting, arrangement and failure in Traditional Chinese, with spoiler-safe reasons for model failure, missing capability, invalid place, stale required fact and unavailable actor. Delivery SHALL resolve the saved owner's current legal session/control mapping. Offline work SHALL remain durable; reconnect SHALL present latest status and authoritative scene. Notices SHALL NOT promise exactly-once delivery.

#### Scenario: Disconnect and change controlled actor
- **WHEN** generation finishes offline and the owner reconnects controlling a lawful party member
- **THEN** latest status goes to that current session, contains no future identities/hidden locations/outcomes and does not address the stale pre-generation actor

### Requirement: Fresh initialization excludes historical reconciliation

Deployment SHALL target a rebuilt game database with current schema and normal idempotent initialization, without migration, compatibility parsing or old-request scanning. Reset scope SHALL be the verified configured game database and SQLite sidecars only; logs, transcripts, assets, art, credentials, service configuration and unrelated mounts SHALL survive. Proposal creation SHALL NOT execute or schedule destructive reset.

#### Scenario: Fresh deployment proof
- **WHEN** the approved implementation is deployed through the supported Evennia/uv and normal image/source workflow to a fresh database
- **THEN** initialization is idempotent, no historical request is imported or dispatched and protected non-database resources remain unchanged

#### Scenario: Existing request without work
- **WHEN** startup encounters a creative request with no dispatch record
- **THEN** it creates no work from that request and resumes only existing nonterminal dispatch records
