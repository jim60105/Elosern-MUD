# dialogue-epochs Specification

## Purpose
Preserves durable pair dialogue through explicit compaction epochs while rendering stable versioned prefixes and bounded current frames.

## Requirements

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

### Requirement: Dialogue budgets admit the mandatory persona-card floor

The `npc_dialogue` rendered profile budget SHALL admit the mandatory dialogue
content of a fully-authored pair: an NPC persona block at the compact card's
full bound (2000 rendered code points, no truncation) rendered into the
character anchor, plus the speaking player's public persona block inside the
current frame, with zero optional material (no history, recall, or summary)
SHALL fit the profile's maximum input budget.

#### Scenario: A full-card pair converses without degradation

- **WHEN** a dialogue context is built for an NPC whose persona card is at the
  full compact-card bound and a speaking player whose public persona record
  flattens to a block
- **THEN** context building succeeds with the full NPC card and the player's
  persona present in the prompt, the captured accounting reports total rendered
  tokens at or below its max input budget, and the exchange is not degraded to
  the authored greeting by a budget failure

#### Scenario: Oversized optional history reduces before rejection

- **WHEN** replayed epoch frames and chat-memory lines push the assembled pair
  prompt beyond the profile's maximum input budget
- **THEN** frames and memory drop oldest-first, then cognition and epoch
  summary, until the prompt fits, and only a still-overflowing mandatory
  current frame rejects

#### Scenario: Section hard bounds never reject what the aggregate bound admitted

- **WHEN** optional dialogue sections are sized against the aggregate input bound
- **THEN** content the aggregate input bound admits is never rejected later by a section hard bound

#### Scenario: Deterministic reduction converges to acceptance

- **WHEN** the deterministic reduction order (oldest replay frames, then
  chat-memory lines, then recall cognition, then epoch summary) has converged
  inside the aggregate bound
- **THEN** the final prompt is accepted rather than degraded

#### Scenario: Mandatory overflow is the only budget failure path

- **WHEN** a dialogue prompt hits any budget limit
- **THEN** rejection of mandatory overflow is the only budget failure path, and mandatory content is never silently removed

### Requirement: Caching is optional observability

Prefix hashes, estimates and provider-reported cached tokens SHALL be recorded as observability only. Provider controls SHALL stay in transport/profile capabilities; correctness SHALL work with caching disabled.

#### Scenario: Provider supports no caching
- **WHEN** the same context renders with a provider lacking cache hints
- **THEN** generation uses the same bounded context without provider-cache prerequisites
