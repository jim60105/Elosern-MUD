## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Add a real beat-scoped generation entry point sharing the canonical QuestBlueprint/schema/semantic validators. Use a no-content sentinel degradation on that capability path, not generic template replacement. Generic generate_quest_blueprint keeps existing offline templates; this distinction avoids silently changing current generic quest behavior.

### 2. Boundary decision

Pass only allowed narrative context and validated beat/source/thread revisions. Pure world/ai generation cannot import writers. Deterministic composition passes validated JSON-safe payload to existing world/quests compiler/registration; no world.ai import in quest compile.

### 3. Boundary decision

Enable the StoryDirector quest-seed executable registry entry only with this real handler. Before publication revalidate source/request version, thread arrangements, issuer authorization, rank/reward/lore references and current state; then atomically record linked beat/quest publication. Preserve scene instance/reclamation constraints and all-or-nothing rollback.

### 4. Boundary decision

Keep existing SceneBuilder and maps ownership; no bespoke room spawner or quest progress/acceptance mechanism. Quest offerings remain subject to actual contact/issuer acceptance paths; letters cannot accept or complete them.

### 5. Boundary decision

Persist source snapshot/blueprint/publication IDs for restart deduplication. If generation/compile fails, publish nothing, keep thread intact and create no filler.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: scenario-director requires generic generate_quest_blueprint to always degrade to a compatible template. The approved beat path forbids replacement filler. Add a explicitly beat-scoped entry point with no-content degradation, preserve generic templates; do not route beats through the generic fallback. quest-progress-tracking/dialogue-offer-quest remain authoritative gameplay-only.
