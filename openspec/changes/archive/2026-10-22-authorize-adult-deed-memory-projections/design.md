# Design

## Context

The adult source contains mixed knowability and may be public because a third living entity is present. `events` schedules memory projection after commit; `memory` generically copies the complete public event content into each participant's witnessed memory. Current dialogue rendering only reads a summary, so the established defect is owner-readable memory disclosure, not a proven nested-field model leak.

## Goals / Non-Goals

**Goals:** One pure recipient authorization decision shared by nomination and adult memory projection; no private-data escape through a second durable consumer.

**Non-Goals:** No broader reputation/witness system, new bystander memory entitlement, historical memory repair, private authoring projection, memory-tier rebalance or blanket marking of all deeds private.

## Decisions

1. Extract A's recipient-parameterized adult projection into a small deterministic narrative-owned helper, or an appropriate existing projection module. Both `recent_deeds` and the explicit adult branch in `memory` consume it. Keep the content envelope detached, typed and allowlisted; no AI import or writes inside the projector. Remove the old independent projection implementation rather than retaining two authorization conventions.
2. Apply event visibility and owner eligibility before field projection. Preserve the existing no-projection behavior for private events in the memory workflow and private-authoring exclusions. Public adult events do not bypass field checks; nomination can still read the player's personally authorized private experience through its existing path. Merely present third parties receive neither participation nor memory by this change.
3. Project observable act/roles/results per recipient. Private milestone summaries belong only to their subject; raw rolls, internal auto-comply reasoning and another participant's unknown counters never enter a memory or derived summary. A deterministic readable memory summary, where needed by the existing reader, is derived only from the same authorized fields and claims no consent or public recognition.
4. Keep original source IDs and immutable event content for authorized storage consumers. Memory record creation and progress completion stay atomic and replay-idempotent. An unauthorized/malformed adult record is omitted fail-closed with a bounded diagnostic, never passed through the generic raw-content branch. Unrelated event categories and the protection projector retain their existing behavior.

## Risks / Trade-offs

- Current prompt and memory eligibility differ -> share field authorization only, not blanket workflow eligibility or memory storage policy.
- Partial projection after failure -> verify memory/progress rollback, restart and per-owner counts alongside returned content.
- Internal award evidence can ride the raw event -> authorize exposed fields explicitly; do not copy source dictionaries wholesale.

## Ownership

The shared projector is `world/narrative/adult_projection.py`; its consumers are `world/narrative/recent_deeds.py` and `world/narrative/memory.py`. `world/narrative/action_adapters.py` stays the producer and keeps its settled-effect vocabulary, which the projector now enforces as an allowlist rather than copying effect rows wholesale. The change also owns the focused memory/selector test modules, the new `world/narrative/tests/test_adult_memory_projection.py` (registered in shard 4 of `.github/evennia-shards.json`) and the knowledge-boundary section of `docs/development/narrative-memory-and-recall.md`.

Two seams are touched beyond those files because the admitted evidence shape is now enforced: legacy adult fixtures in `world/narrative/tests/test_recent_deeds_selection.py` and `server/conf/tests/test_title_nomination_service.py` were updated from non-production effect rows to the settled-effect shape the producer emits. Both fixtures keep their original intent (an adult occurrence with an effect and a milestone, and an authorized adult outcome reaching the prompt).

## Migration Plan

A is required. Cut over both consumers in one change. No persisted-event or memory rewrite, parser aliases or backfill. This change protects newly projected sources and pending projection recovery under the current contract. Update knowledge-boundary documentation and traceability.

## Verification and size

Budget: shared projector 2 h; memory dispatch 2 h; public actor/recipient/bystander and replay/rollback behavior 2 h; smoke/docs/lint/gates 2 h. Read owner memories through the public authorized API and compare private controls.
