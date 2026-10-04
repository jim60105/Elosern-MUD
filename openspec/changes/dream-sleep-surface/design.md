## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Integrate at accepted sleep outcome rather than duplicating duration/regen/safety logic. Existing time-skip-commands and skip-safety-gate remain unchanged in behavior; any new choice syntax is documented. Zero-second accepted sleep is valid; current rejection rules remain outright rejection.

### 2. Boundary decision

Sleep settles before optional dream open. Save durable sleep-result/session association so reconnect never repeats its settlement. Later explicit sleep can produce a new outcome while resuming saved discussion; do not confuse it with replay of the previous entry.

### 3. Boundary decision

Reuse existing server-authored finite menus and text input conventions for choice/confirmation/draft/awakening; browser does not infer count/state from prose. Owner/control/session revision gates revalidate on every request. Exact layout/keys follow existing UI and command conventions, not a new protocol invented in the proposal.

### 4. Boundary decision

The public feature composes lifecycle and Section 6.4 presentation together. No stripped-down dream UI ships first. Keep offline deterministic escape visible with pending/failed generation, no required ending call, no second physical settlement.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: time-skip-commands remains no-duration sleep with existing regeneration calculation; skip-safety-gate currently rejects outright. The optional post-settlement dream is additive and must not reinterpret either rule. world-clock converse remains unwired; dreams do not advance it.

Implementation reconciliation: text opts in with `sleep dream`; browser opts in
with exact `explore.wait` payload `{"sleep": true, "dream": true}`. The new
`dream` panel uses the existing versioned OOB registry/envelope and reports
durable session revision, count, track, validated scene/dialogue and choices.
`dream.say` uses two bounded message parts to preserve the transport's
per-string ceiling without reducing the lifecycle's 4000-character input bound.
Draft/confirm accept plain summaries or bounded structured authoring directions;
browser thread choices are server-authored and permissioned. Explicit later
entry resumes unconfirmed ended discussion with its original count, while
confirmed sessions remain final. Both sleep adapters record and report actual
committed ticks, retaining their original safety and settlement seams.
