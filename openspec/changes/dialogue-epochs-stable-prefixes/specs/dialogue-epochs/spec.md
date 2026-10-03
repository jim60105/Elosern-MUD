## Purpose

Preserves durable pair dialogue through explicit compaction epochs while rendering stable versioned prefixes and bounded current frames.

## ADDED Requirements

### Requirement: Epoch compaction preserves original turns and provenance

Each player/NPC pair SHALL retain an append-only turn stream with explicit epochs for compaction and natural boundaries, distinct from the current-target dialogue session. Compaction SHALL preserve original turns and source revisions. Failed summaries SHALL leave originals and the current usable epoch intact.

#### Scenario: Summary fails
- **WHEN** epoch summarization fails validation or services are offline
- **THEN** original turns remain and bounded recent/fixed/recall context remains usable

#### Scenario: Compaction succeeds
- **WHEN** a valid derived summary starts a new epoch
- **THEN** all summarized turns remain retrievable with immutable source references and generation identity

### Requirement: Stable prefixes change only at legitimate invalidation

Assembly SHALL order global rules, world digest, capability contract, character anchor, epoch summary and append-only frames. Changing location, relations, recall and affordances SHALL be in the new frame. Historical frames SHALL retain original tick data; current frames SHALL distinguish superseded facts. Persona/prompt/rendering changes SHALL invalidate the affected prefix/epoch. Profile hard budgets SHALL still apply.

#### Scenario: Two turns change location
- **WHEN** a pair continues within an epoch after movement
- **THEN** the old prefix/frames remain byte-identical and the new frame carries current location

#### Scenario: Actors share global context
- **WHEN** two actors use the same global rules/world digest/rendering version
- **THEN** their global prefix sections are identical

#### Scenario: Persona changes
- **WHEN** a persona edit occurs during a pending reply
- **THEN** the established stale-persona rejection remains and future generation uses a newly versioned prefix

### Requirement: Caching is optional observability

Prefix hashes, estimates and provider-reported cached tokens SHALL be recorded as observability only. Provider controls SHALL stay in transport/profile capabilities; correctness SHALL work with caching disabled.

#### Scenario: Provider supports no caching
- **WHEN** the same context renders with a provider lacking cache hints
- **THEN** generation uses the same bounded context without provider-cache prerequisites

