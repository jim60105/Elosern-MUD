# Design

## Context

Combat upkeep takes its milestone snapshot after buff ticks can trigger pleasure reactions. Item settlement calls `apply_pleasure_gain` directly; defeat violations cause onsets and increment unlock-driving counters directly while their clock scope is empty. The existing non-resolver milestone writer currently has only clock/upkeep callers.

## Goals / Non-Goals

**Goals:** Record actual owner-local adult occurrences and newly crossed milestones in their own source transaction and at their actual world tick.

**Non-Goals:** No new adult mechanics, generic item deed eligibility, item/upkeep immediate nomination, additional clock advancement, lifetime-state backdating, gameplay-resolver idempotency API, migration or backfill.

## Decisions

1. Capture pre-state before the first relevant mutation. Combat upkeep snapshots before `tick_buffs`, then compares after buff reactions, decay and climax settlement. B supplies the engagement/round identity, so repeated later upkeeps cannot reuse `combat:combat:round:1`. Keep the clock owner's already-correct before-state ordering and avoid overlapping duplicate ownership.
2. Give accepted item uses an immutable operation identity allocated by the existing deterministic acceptance owner and passed into settlement. Use B's combat slot identity in combat, and a fresh accepted-operation identity outside combat. Never derive identity solely from item key/tick or effect display. Capture every affected recipient before applying the first item step; record only actual new adult milestones, not generic item actions, in the same transaction as consumption/effects.
3. In defeat aftermath, key actual attempts to the unique engagement, aggressor, attempt ordinal and selected victim. Compare before/after around declared pleasure and counter changes, record eligible adult-action outcomes including actual resistance/landed results and attach newly crossed subject-private milestones. Preserve existing empty clock scope, selected-recipient pool, deterministic draws, aftermath undo, and event-log semantics. Do not infer adult participation for an untouched ally or an unselected pool member.
4. Reuse the narrative-owned adapters and E's field authorization contract. Writers emit immutable evidence before outer commit; a required record failure rolls back item effects/consumption or the entire aftermath/upkeep unit, including caches. Retransmitted committed settlement evidence reuses source IDs and original records without re-executing the gameplay owner.

## Risks / Trade-offs

- A single item has several effects -> one accepted use owns its milestones; no duplicate action counts per effect.
- Defeat has attempted and landed outcomes -> retain resistance meaning without inventing landed effects or willingness.
- Cascade owner overlap -> assign exactly one source for each before/after interval and assert no repeated onset/unlock from later clock reads.

## Migration Plan

Integrate A, B and E first. Update accepted-operation callers and owner evidence together, with no compatibility defaults that hide missing IDs. No migration or backfill; preserve all authored balance and command syntax. Technical docs and relevant command behavior notes update during apply.

## Verification and size

Budget: upkeep 1 h; item owner 2 h; defeat owner 2 h; synthetic crossing/control/rollback smoke 2 h; docs/traceability/gates 1 h. Each regression exercises its real owner, pre-existing-state negative and an untouched control.
