## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

MemoryRecord stores owner identity, tick, category, core/working/archive tier, immutable content/provenance, salience, witnessed/told/inferred/public scope, confidence, subjects, sources and generation identity. W3 adds real thread linkage, not a placeholder model.

### 2. Boundary decision

Append-only MemoryRevision records represent availability, tier/decay, supersession and record relationships. Materialize effective metadata and owner generation in one transaction; never overwrite original content/provenance.

### 3. Boundary decision

Project W1 events through observation/visibility rules. Unique owner/source/projector-version keys and atomic progress prevent duplicate cognition. A claim remains told/inferred, never authoritative truth.

### 4. Boundary decision

Expose permission-filtered plain values to context; all writes stay in narrative. Normal retrieval excludes inactive/superseded records. Historical access remains permissioned; dialogue provenance is connected later in W1.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
