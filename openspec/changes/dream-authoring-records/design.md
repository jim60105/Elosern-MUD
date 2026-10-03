## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Store private session drafts and immutable request versions with owner, desired direction/constraints, source references, validation status and unique version submission key. These are authoring data, never MemoryRecord inputs.

### 2. Boundary decision

Pure deterministic validation checks referenced participants/threads, established facts/personality and executable direction constraints. Return concrete reason codes/messages; do not substitute a different desired story. Approval is direction, not outcome.

### 3. Boundary decision

Confirmation transaction fixes the version and durable scheduling request once; drafts have no scheduling work. Editing creates a new unconfirmed version. Offline validation works without an LLM; StoryDirector capability follows later.

### 4. Boundary decision

Use spoiler-filtered summary/creative preferences for collaborator access. Hidden answers for StoryDirector are absent from this read model; same model profile never grants shared history or permissions.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
