## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Use existing settlement-place/service anchoring for authored 銀羽驛站 branches. Add a minimal letter-only server surface and text-client equivalents; browser finite choices consume server affordances, never parse prose. Resolve established recipients to persistent IDs and reject ambiguity; exact keys/layout are selected under existing command/menu conventions during implementation.

### 2. Boundary decision

Any branch collects all due letters. Personal menus away from branches list collected letters only. Server authorization rechecks branch context, control/owner, collection state and body bound on every send/collect/read; presentation itself performs no writes.

### 3. Boundary decision

First read transaction records first-read tick and narrative read source once. Collection records acquisition, never content knowledge. Rereads are read-only; preserve durable delivery/read IDs for later memory projection.

### 4. Boundary decision

Update both command docs and tests/test_command_docs.py when keys, aliases, syntax or availability change. No remote quest acceptance, item transfer or formal appointment action appears in letter affordances.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
