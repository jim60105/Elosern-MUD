## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Store indexed StoryThread rows, immutable origin/source references and revisions. Separate factual summary/observed commitments from proposed plans and unresolved questions. A lifecycle transition is an explicit deterministic operation; inactivity may inform dormancy but never infer abandonment.

### 2. Boundary decision

Add actual relational linkage to existing events, memories, letters and durable pair turns now that the owner exists. Link statements as statements; only existing rules/quest commits create actual commitments. No parallel quest lifecycle.

### 3. Boundary decision

Add thread revision to retrieval/context snapshot keys and read identities. Owner permissions constrain eligible thread membership/sources before ranking. Revisioning preserves old snapshots and changes only subsequent generations.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
