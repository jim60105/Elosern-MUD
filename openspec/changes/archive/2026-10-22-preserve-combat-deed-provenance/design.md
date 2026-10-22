# Design

## Context

`reconstruct_battlefield` carries roster state but no encounter identity. Combat passes session/round/slot data through execution scope and narration strings, while `build_action_source_id` looks for dynamic battlefield attributes and falls back to cast/tick identity. The world tick remains unchanged across ordinary rounds. Terminal source IDs already use `engagement_id`, but terminal content and selector joins still use reusable `session_id`.

## Goals / Non-Goals

**Goals:** Give every committed combat action and upkeep occurrence an authoritative identity and one encounter join key.

**Non-Goals:** No redesign of transport session IDs, revision/CAS tokens, initiative, timing, combat outcomes or existing protection projection. No database migration or old-record fallback.

## Decisions

1. Carry a frozen combat provenance value through the existing rules execution context: unique `engagement_id`, round ordinal and action-slot ordinal. Construct it from the durable combat record at the composition point, for ordinary, opening and compressed paths. Do not parse display/narration strings for persistence identity or attach guessed `session_id` attributes to a battlefield. Update all context constructors and relevant declared interfaces together.
2. Derive action source IDs from engagement + round + slot + actor; effects and title awards use the same occurrence. Skill identity is evidence, not an alternative occurrence allocator. Resolver-independent upkeep sources use engagement + round + entity + transition discriminator. Retransmitted settlement notifications reuse these keys; distinct slots/rounds never share them even at the same world tick.
3. Carry `encounter_id = engagement_id` in action, milestone and terminal content, and group only on that key. Keep transport `session_id` as separate diagnostic metadata, never as a dictionary overwrite key. Apply the same owner-allocated engagement identity to examination construction, not only hostile `engage_group`.
4. Update typed consumers and remove the obsolete combat cast/tick fallback. Out-of-combat cast identity remains owned by its existing accepted operation. When combat provenance is missing, reject malformed required evidence rather than invent an out-of-combat occurrence.

## Risks / Trade-offs

- Combat has multiple execution surfaces -> prove real ordinary repeated actions and at least one opening/compressed path, plus simulated examination identity isolation.
- Reusable transport sessions can coexist -> test zero-time surrender/re-engagement through selector output, not just two event rows.
- New identity fields touch test construction -> migrate synthetic constructors without compatibility defaults that mask missing production metadata.

## Migration Plan

A is integrated first. Cut over all combat evidence producers, award source readers and selector joins together. No backfill or migration; no replaying old gameplay. Preserve immutable event replay and the existing protection consumer. Update technical docs and traceability during apply.

## Verification and size

Budget: context propagation 2 h; source and join cutover 2 h; real combat/replay/rollback regressions 2 h; focused smoke/docs/gates 2 h. Observe multiple same-skill slots or rounds retained with distinct sources and the correct terminal group.
