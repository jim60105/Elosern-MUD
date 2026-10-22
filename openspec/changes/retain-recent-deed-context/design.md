# Design

## Context

Every supported `NarrativeEvent` already has a stored location identity, but `AuthorizedDeedRecord` and all rendered facts omit it. C retains complete quest objective bindings; F adds real non-resolver owners. The selector returns `frozen_tick`, but `_build_context` discards it and scheduling logs a missing context field as zero.

## Goals / Non-Goals

**Goals:** Keep readable committed location/time facts and one frozen request time across all adapters and diagnostics.

**Non-Goals:** No live entity serialization, selection-time room lookups, source-history repair, inference of unknown locations, changed 48-hour/count/JSON limits, new prompt collision inputs or logging of private prose.

## Decisions

1. Producers snapshot a bounded location reference (durable identity plus readable label) inside the source settlement using their actual location owner. Preserve the existing canonical event location identity and put the detached label alongside source content. Update quest, examination, combat, skill/adult and owner-local milestone producers together; include virtual-room location context only when the owner already has it. Unknown location stays explicitly unknown rather than guessed.
2. Carry authorized location and occurrence tick through `AuthorizedDeedRecord`, grouping and serialization. A compressed group retains source-linked occurrence context for differing times/locations; it does not assign the first location to later occurrences or duplicate a misleading action-source claim. Nested encounter actions retain their own location context. The existing 8000-code-point envelope budget includes these references and still drops only complete groups.
3. Preserve C's complete objective/result snapshot without resolving mutable quest/room registries at selection time. IDs and readable labels make the request intelligible after a room is renamed or removed; no foreign private fields are reintroduced by contextual rendering.
4. Freeze world tick once in service admission before feed construction, pass it explicitly to selection, and carry the same integer in the detached nomination context. Use it in admitted/completed/error diagnostics with player, trigger and retained-source counts. Do not substitute default zero, recalculate after generation, or read a later clock for an old request. An unavailable clock fails the read workflow without changing gameplay/cooldown.

## Risks / Trade-offs

- More context can reduce retained groups -> preserve complete facts and source synchronization under the existing budget, without truncating JSON or labels into false identities.
- Room lifecycle can outlive source storage -> prove the prompt uses the committed snapshot after rename/removal.
- Shared producer metadata edits -> integrate F first and serialize G against D and all producer edits; main-spec synchronization has one owner.

## Migration Plan

Integrate A/B/C/E/F before the metadata cutover. Migrate current callers/fixtures; malformed old unsupported payloads remain fail-closed, with no compatibility renderer or backfill. Update technical prompt/diagnostic documentation and traceability during apply.

## Verification and size

Budget: producer metadata 2 h; projection/context references 2 h; frozen admission/diagnostics 1 h; real-source time/location/budget smoke 2 h; docs/gates 1 h. Assert exact nonzero frozen ticks and no private prose in errors as well as admission.
