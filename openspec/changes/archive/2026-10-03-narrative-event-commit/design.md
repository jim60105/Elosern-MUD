## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Use indexed Django tables for NarrativeEvent and projection progress. Store immutable structured facts, persistent participants, applicable location, tick, visibility, salience, and source IDs. Initial coverage is W1 protection, ordinary and compressed combat; do not persist every EventEntry indiscriminately.

### 2. Boundary decision

Identify an occurrence by durable encounter/session identity, committed ordinal and projector version, protected by unique constraints. Persist identity before reconnect reuse. Never use display names, EventLog object identity, equal prose hashes, or timestamps as source identity.

### 3. Boundary decision

Insert event and pending projection inside the existing outer action/round/terminal transaction committing the result. Nested savepoint completion and transient on_commit callbacks are insufficient. A callback may wake work; restart scans pending rows. Preserve cached-attribute snapshot/restore semantics.

### 4. Boundary decision

Keep EventLog as a transient immutable narration DTO. Establish protection from committed participant/outcome evidence, not model speech. No memory table or fake thread here.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: event-log is a transient committed DTO, not a durable source. Add narrative-events without changing event-log or converting gameplay to event sourcing.
