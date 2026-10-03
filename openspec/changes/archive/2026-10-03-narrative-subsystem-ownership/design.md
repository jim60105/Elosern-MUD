## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No code, runtime behavior, import-contract changes, migrations, or compatibility work.

## Decisions

### 1. Boundary decision

Explicitly amend the architecture diagram, directory layout, and named deterministic-owner list in the AI engine design and AGENTS.md. Narrative owns events, memory/revisions, threads, letters, attention/context snapshots, authoring records, and validated beat scheduling only as each is implemented. Do not create unused package scaffolds.

### 2. Boundary decision

Preserve the distinction between game-state authority and generation. world/ai emits proposals only; narrative applies only its own data. General actions and relationships call world/rules; quests call world/quests; rooms and instances call world/maps; lore and skills remain registry/read-only.

### 3. Boundary decision

This is a documentation-only authorization amendment; use skip_specs: true rather than inventing an executable requirement. Future behavior deltas begin in W1. No implementation, import-ban weakening, or tables are part of W0.

### 4. Boundary decision

W4 is deferred without artifacts: collect W1 labeled retrieval failures and actual memory-growth measurements, then decide consolidation triggers, decay policies, summary validation/budgets, Deep Recall call/result/token ceilings, and admin permissions. Real prerequisites are owner memory/revisions, calibrated Fast Recall, immutable snapshots, and dialogue epochs; threads are needed only for thread-aware maintenance. Embeddings require demonstrated lexical retrieval failures; cargo needs a separate approved design.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: AI engine design and AGENTS.md enumerate maps and quests but omit narrative. This explicit amendment resolves that architecture gap; no main capability spec is changed.
