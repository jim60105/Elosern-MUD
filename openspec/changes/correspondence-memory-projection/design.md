## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Project durable delivery for NPCs and first-read for players. Collection alone creates no content memory. Owner/source uniqueness, progress and generation bump share the projection transaction.

### 2. Boundary decision

Gate NPC reply work until required delivery-memory progress is settled, or drain the same durable projector before snapshot capture. Do not let delayed projection cause an NPC to reply as if the delivered letter is absent or access an undelivered body.

### 3. Boundary decision

Retain letter references/ticks/reply-to for provenance and conversation summaries. Source statements create told memories, never world truths or quest events. Face-to-face turns remain a separate stream; cross-channel continuity uses selected cognition.

### 4. Boundary decision

Thread fields/joins are added by W3, not placeholder IDs in W2. Test complete send→delivery→reply→collect→read behavior with model/image services offline except recorded generation fixtures.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
