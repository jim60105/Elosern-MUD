## Context

`scenario_director.py:487-500` accepts any positive quantity; `compile.py:379-435` passes it through for REACH/ESCORT; `room_observation.py:91-108` calls `fulfill_record` on the first matching arrival, jumping straight to full quantity. Separately, `compile.py:540-575` makes ESCORT stages with `npc_req` impossible (npc_req requires instance; ESCORT forbids instance), while permanent-location stages are never bound to protected entities (`scene_builder.py:354-369`), so `_escort_ready` (`room_observation.py:36-50`) can never be satisfied.

## Goals / Non-Goals

**Goals:**
- No registered quest can be structurally uncompletable.
- Arrival progress is bounded by quantity per event.

**Non-Goals:**
- Implementing a full protected-entity escort binding flow (NPC escort with instance scenes) — tracked separately; until then ESCORT publishing is refused.
- Changing DEFEAT/ACQUIRE quantity semantics.

## Decisions

**D1 — Cap REACH/ESCORT quantity at exactly 1** at both the proposal validator and the compiler, mirroring `definitions._validate_objective` per-kind checks. Shipped catalog quests already use quantity 1, so nothing breaks.

**D2 — Refuse ESCORT publishing until a binding path exists.** The proposal validator and `register_generated_quest` reject ESCORT stages (and the director refuses 護衛 requests with a clear message) until a protected-entity binding flow is implemented. This converts a silent uncompletable quest into an explicit rejection.

**D3 — Defensive increment in arrival observation.** `observe_room_entry` increments progress by one (capped at quantity) instead of calling `fulfill_record` unconditionally, so the one-transition rule and the quantity-1 cap make behavior identical today while removing the jump-completion path.

## Risks / Trade-offs

- **ESCORT feature availability**: players cannot obtain escort quests until the binding flow lands; the alternative (uncompletable quests) is strictly worse.
- **Delta-compat**: any authored ESCORT content currently in flight would be rejected at publish — the project has no released content beyond the catalog.
