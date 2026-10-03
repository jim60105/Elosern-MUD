## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Store session/version/submission IDs, completed count, pending response identity, saved input and delivered response references. One outstanding turn per session; enforce uniqueness/session revision compare-and-swap for duplicate/concurrent input.

### 2. Boundary decision

Define successful delivery at the existing server presentation acceptance boundary: validated response is committed to a recoverable player response record and dispatched by that identity; reconnect replays that same response, never creates a new exchange. Do not count a mere generated response or failed transport. Outbox/progress and count commit atomically, so crashes never consume twice.

### 3. Boundary decision

Cap completed exchanges at six and independently bound rendered input. Validate exchange-five convergence and exchange-six summary/no-question semantics through the existing guardrail in the presentation capability; this change owns counting/choices only.

### 4. Boundary decision

Confirm/draft/awaken are deterministic operations and available even when pending generation fails. Re-entry resumes the saved draft/count without replaying prior sleep. Do not publish player dream entry until dream-explicit-presentation and dream-sleep-surface provide the approved scene and sleep contract.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
