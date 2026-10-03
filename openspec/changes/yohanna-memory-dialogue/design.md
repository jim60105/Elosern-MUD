## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Cut over every face-to-face dialogue caller from destructive chat-memory trimming to narrative-owned append-only pair turn records. Bound only the rendered prompt view. Store submission/delivery identity, tick, provenance and player-versus-NPC turn kind; idempotent settlement appends each delivered response once.

### 2. Boundary decision

Use the existing injected client, guardrail, eight-kind face-to-face intent contract, schedule gate, co-location checks, thinking cleanup and stale-persona rejection. Persistence is deterministic orchestration, never world/ai. A stale-persona response is neither shown nor recorded; authored offline greeting/silence behavior remains.

### 3. Boundary decision

Preserve NPC own hidden persona access and player public-only identity/appearance/social connections; do not copy player life story/personality into knowledge. W1 keeps the existing prompt template placement; W3 changes stable-prefix placement explicitly.

### 4. Boundary decision

Author 尤漢娜‧庫柏 (Yohanna Cooper), a guild-artisan-circle character with hereditary barrel-making family name, through current profile/persona/naming conventions. Supply one deterministic initial protection encounter and later revisit route. Do not inherit 莉亞, missing family, mine plot, promises, identifiers or dialogue from the temporary handoff.

### 5. Boundary decision

Permanent mechanics tests use synthetic actors and FakeLLMClient, never shipped lore names or live services. Register any separate Yohanna data-contract test in the existing freeze manifest. Local controlled generation smoke verifies assembled context/downstream response, not exact model wording; this optional controlled smoke is not a permanent automated test.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: npc-dialogue requires destructive bounded per-character history and pre-persona byte-identical user payloads. Replace these with durable pair turns/bounded views and rendering-version-relative persona omission; retain all intent, offline, schedule, thinking and stale-persona scenarios. W3 later replaces prompt placement, not these safety contracts.
