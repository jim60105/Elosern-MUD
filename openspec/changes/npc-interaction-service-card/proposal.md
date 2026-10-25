# Proposal

## Why

The existing flat verb card renumbers actions from available rows and carries no service grouping. The approved interaction order requires consistent common slots and target-safe selection.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Integrate grouped NPC services into the existing interaction card with fixed slots, accessible disabled rows and stale-selection/focus safety.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-presence-rail`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `webclient-exploration-menu`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

use-person-focus.js::verbCardRows maps rows to digits and BACK_ROW. stores/elosern/presence.js re-resolves verb keys but cardPickKeys recalculates digit mappings on every key event. ChoiceCard.vue is the existing keyboard composite. Prototype docs/design/npc-service-menu has synthetic routes, CSS-only headings and overflow labels that are not gameplay services.

This is a one-engineer-day runnable slice with 5 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-plain-name-presentation
depends-on: npc-contextual-service-projection
depends-on: authored-dialogue-reading-client
depends-on: authored-dialogue-unread-notices
depends-on: webclient-immutable-adoption
depends-on: npc-service-text-parity

code-conflicts: U follows P/X/S and active reading-client/unread-notices/immutable-adoption. Shared use-person-focus, presence.js, ChoiceCard, AppClient, frame-resolvers and tests must be serialized; preserve source-aware reading receipts, notice timing, getCommittedState immutable reads and exact-base publication. Prototype remains unmodified evidence.

The complete new-new and relevant active-change matrix and amendment ownership are in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md`. The approved source remains unchanged.
