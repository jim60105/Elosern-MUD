## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Deterministic composition produces plain immutable values for world/ai. A thin descriptor binds existing LLMProfile/client/prompt/schema/rendering versions, validators, snapshot and trace IDs. No second client, retry system or stateful framework.

### 2. Boundary decision

One rendered representation includes headings/attribution during selection and assembly. Calibrate profile-specific section soft targets and hard limits after reserving completion, future Deep Recall and safety margins. Reject mandatory anchor overflow.

### 3. Boundary decision

Persist payload or reconstructible immutable sources with exact read revisions, not hashes alone. Store capability/version/source/section/budget/truncation data. Retry reuses capture; new generation invalidates on owner changes. W3 adds thread revisions.

### 4. Boundary decision

Use world.observability and extend its catalog. Record actual input/output/provider-cache tokens when available, retries/degrade/latency, stable-prefix estimates and selected IDs. Full debug retention requires opt-in controlled storage.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
