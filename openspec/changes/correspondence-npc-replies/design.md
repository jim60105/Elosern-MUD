## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Reuse the W1 cognition builder, immutable snapshot and existing client/profile/guardrail. Register a separate correspondence schema and validators; world/ai returns proposals only. Separate channel contract permits none/validated relationship adjustment, not the eight face-to-face kinds.

### 2. Boundary decision

Create durable reply eligibility/work at delivery; source and recipient identity determine deduplication. On failure keep pending; do not promise response or add a retry policy. Each intentional later attempt uses existing guardrail behavior and an immutable captured context; revalidate current state before apply.

### 3. Boundary decision

Reply-to/snapshot/outgoing send and work completion commit once. Apply allowed relationship effects through world/rules with its existing bounds/daily budgets; a rejected effect does not fabricate a committed effect in speech. No co-location gate for remote exchange; other authorization/relationship rules remain.

### 4. Boundary decision

An outgoing reply starts one-hour travel only when its send commits. Incoming delivery never waits for a model. No quest accepting/progress, codex unlock, item transfer, physical action or formal appointment channel.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: npc-dialogue and dialogue-offer-quest permit face-to-face quest assignment and completion-time co-location checks. Their contracts remain face-to-face only; correspondence uses a distinct restricted channel and never routes offer_quest through those appliers.
