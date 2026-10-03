## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

This is independent of dream UI and of StoryThread implementation; W1 durable turns/context are the real prerequisites. W3 thread revision support integrates automatically once narrative-story-threads lands.

### 2. Boundary decision

Create explicit pair epochs with retained originals and immutable summary generations. The existing world/rules/dialogue.py current-target session is neither history nor epoch. Shared letters contribute via memories, never a copied correspondence stream.

### 3. Boundary decision

Keep the prompt library API and four npc_dialogue.system placeholders intact: pass location="" in stable character/capability rendering, place current location in the new turn frame, and prepend shared global rules/digest. NPC persona stays in its system character anchor, public player persona stays user-side. Do not split into a second persona renderer.

### 4. Boundary decision

Add versioned per-section rendering and append-only frames. Mark current authoritative changes/supersession; never rewrite historical supplied state. Persona/prompt changes invalidate prefix/epoch; carry existing stale-persona rejection unchanged.

### 5. Boundary decision

Bound summary calls through the existing capability/guardrail/snapshot mechanism; preserve original records on failure. Reuse rendered budgets; measure profile-specific targets. Provider cache hints are optional transport details.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: npc-dialogue puts mutable location in its system prompt and uses a regenerated chat window. W1 preserves template placement; this successor delta moves location to current frames, retaining prompt-library placeholder API and persona-dialogue-injection permissions. It edits the same prompt requirement as W1 and must apply after it.
