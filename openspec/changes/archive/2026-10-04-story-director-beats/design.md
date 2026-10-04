## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Reuse existing capability descriptor/profile/client/prompt/guardrail and immutable snapshots. StoryDirector is separate from dream collaborator in permissions/history, even with the same profile. Proposals carry source candidate/request version and thread revision.

### 2. Boundary decision

Use indexed decision/beat work and source uniqueness, one selected beat maximum per decision. Acquire/compare thread revision in deterministic settlement; serialize same-thread scheduling so concurrent outputs cannot establish incompatible arrangements. None is a first-class valid result.

### 3. Boundary decision

Implement only existing executable narrative follow-up/clue/invitation-as-statement and letter sends. Physical arrangements/relationships call rules owners; unsupported formal appointments reject. Quest-seed execution is not registered until scenario-beat-compilation supplies the real quest boundary; no no-op or fake quest handler.

### 4. Boundary decision

Apply narrative-owned scheduling in narrative; delegate other effects through rules/quests/maps owners. Revalidate all mutable prerequisites against captured versions before committing, preserve atomic rollback where multiple owners participate, and reject stale conflicts without replacement filler.

### 5. Boundary decision

Exhausted generation/validation schedules nothing and leaves threads intact. Durable work/provenance survives restart; reuse guardrail retry/degrade rather than introducing a scheduler retry framework.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
