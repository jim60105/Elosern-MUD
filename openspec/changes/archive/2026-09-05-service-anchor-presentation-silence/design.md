# Design: service-anchor-presentation-silence

Ratified: R2 design §4–§5, D5/D6. Local implementation choices only.

## Context

Affordance emission: `web/webclient/presentation/affordances.py` owns the shared canonical
rules; navigation entries (`surface: "guild" | "shop"`) already emit "only for the exact local
host" — a darkened anchor room therefore already emits nothing, because presence-of-host IS the
current emission key. The disabled path exists as a shape (`disabled_reason.message`, precedent:
`target_dead` on engage). Settlement: `settle_npc_schedules(start, end)` queries NPCs carrying the
`schedule` tag and settles due entries; adding one predicate call at the NPC loop head is the
minimal seam.

## Goals / Non-Goals

**Goals:** honest presentation of `off_anchor`; a traveling clerk stays on the road; zero drift
for every non-traveling NPC (the silence predicate must be exactly false for them).

**Non-Goals:** any new affordance action ids, the possessed-NPC second silence trigger
(possession change owns it — this change defines the predicate with the place-bound trigger only),
interaction-kind vocabulary changes.

## Decisions

- **Predicate shape:** `schedule_silenced(npc) -> bool` in `service_gate.py` (it is service
  semantics, and it is where the possession trigger will be OR-ed in later — one gate, one home):
  true iff the npc has a `place`-bound service component AND a non-null `party_member` AND
  `npc.location` is not its anchor room. Person-bound party members are unaffected — the design
  expresses "no work schedule" for them through `schedule_template: null`, not through this
  predicate.
- **Skip shape inside settlement:** at the per-NPC loop head, before the due-entry iteration:
  silenced → `continue` (no entries, no events, no `npc_state_changed`). A `log_debug` per skip
  with the npc/service context rides the facade, context-gated like the rest of settlement.
- **Disabled affordance shape:** emission code calls `service_available(actor, host,
  component)` for the navigation entry's host; a non-allowed verdict emits the same entry with
  `enabled: False` + `disabled_reason.message` from the registry constant — the allowlist and
  entry shape stay untouched, so the presenter contract diff is additive-state-only.
- **Darkness pin without code:** no affordance code change for the anchor room; a test asserts a
  room containing the anchor but no host emits no shop/guild navigation entry (it would today),
  locking the "no ghost storefront" requirement.

## Risks / Trade-offs

- [Silenced clerk's mid-route state (on-route flag, effective_from)] → the skip precedes all
  entry processing exactly like "no schedule"; when the host returns to anchor (party dismissed
  there), the next window settles normally — schedule semantics already tolerate skipped windows
  (multi-day skip arithmetic is boundary-based, not per-entry-accounted).
- [Presentation drift between text and Vue surfaces] → the affordance rules are shared by both
  presenters (existing single-owner invariant); one emitter change covers both.
