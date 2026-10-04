## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Section 6.4 explicitly approves sexual presentation; do not inherit the retracted sanitized position. The setting is white space, bed, obscured goddess-like counterpart and continuous explicit scene plus creative dialogue. Store prompt prose only in prompts YAML; proposal/tests need no fixed erotic prose.

### 2. Boundary decision

Reuse existing guardrail with separate collaborator schema/access validators and injected LLMProfile/client. Keep collaborator separate from StoryDirector even when sharing deployment. Provide only preferences and spoiler-filtered adventure summaries; no secret director answers, deity identity or authoritative mutation claims.

### 3. Boundary decision

DreamTrack is narrative-owned session data, never a live SexualState handler. Read canonical AROUSAL_LEVELS/five pleasure bands via pure vocabulary/band utilities. Use initial pleasure 0 and configured six deltas calibrated to traverse bands and reach convergence climax. A server-computed prospective next phase is supplied to generation, then committed only with successful completed exchange; retries reuse that phase.

### 4. Boundary decision

Validate one combined scene/dialogue response, phase fidelity, exchange-five convergence and exchange-six summary with no new question. Do not make explicit content itself a failure. Generated fields never directly mutate count/track.

### 5. Boundary decision

Ending is deterministic: reuse validated saved presentation/phase plus canonical phase labels and a fade/awakening affordance, not a new generative call or fixed explicit prose fallback. At climax render post-climax phase; before climax fade without forcing it. All live traits/counters/relationships/skills/buffs/codex remain at post-sleep baseline.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: sexual-state-handler owns live pleasure/counters/climax and remains unchanged. DreamTrack reuses vocabulary/pure band lookup only; no live handler or persistent character effects. guardrail is layer-scoped and can accept the approved explicit capability without a global policy change.
