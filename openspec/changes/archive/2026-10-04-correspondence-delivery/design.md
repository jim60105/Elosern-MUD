## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Store letter rows indexed by recipient/status/due_tick with immutable body, sender/recipient identities, sent/due ticks, optional reply-to, collection/read ticks and durable transition IDs. Only letters, no cargo payload abstraction. Institution is 銀羽驛行; branches are 銀羽驛站.

### 2. Boundary decision

Accepted send creates due_tick = send_tick + configured game-hour rule (default one hour). NPC sent→delivered always succeeds; player sent→available waits for later acquisition. Persistent identities survive movement/room reclamation; no location lookup or receipt condition.

### 3. Boundary decision

Insert correspondence_delivery after npc_schedules and before instance_reclamation; preserve all existing stages as an ordered subsequence and the one-day advance bound. Register a generation-free source via existing register_event_source. Query exact due ticks, not calendar-hour rounding.

### 4. Boundary decision

Letter/event/progress rows commit in the clock transaction; surface declaration covers any touched cached instances/read models, refreshed or invalidated on rollback. Do not load a recipient live handler at delivery. NPC cognition projection consumes a durable delivery source in the later memory integration change.

### 5. Boundary decision

Settle actual ticks only, including skips and combat terminal settlement. Current skip-safety rejects outright; do not implement hypothetical partial-skip behavior. In any existing interrupted outcome use its actual committed interval.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: world-clock and settlement-stage-order pin an exact stage list and declare callback surfaces. Explicitly insert correspondence_delivery and include table/cache rollback; retain existing ordering and one-day bounds. skip-safety-gate currently rejects outright, so no shortening mechanism is added.
