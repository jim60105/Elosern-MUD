## Context

`observe_room_entry` (`world/rules/onboarding.py:182-212`) implements the skip rule correctly (`room_entry_decision`, `world/onboarding/guide.py:129-142`) but is called only from `GridRoom.at_object_receive` (`typeclasses/rooms.py:59-69`); plain `Room` (`rooms.py:17-29`), `TerrainRoom` (`:82-101`), and `InstanceRoom` (`:124-132`) never invoke it. The shared movement-completion path (`typeclasses/exits.py:35-47` and the wilderness traversal branches `:123-192`) already runs after every successful move.

## Goals / Non-Goals

**Goals:**
- One observation call site for all room types, idempotent and safe for onboarded players.

**Non-Goals:**
- Changing guide progression logic, corridor definition, or arrival-scene content.

## Decisions

**D1 — Extract a shared completion helper, then observe.** Today the four successful movement paths (grid exit via `MovementCostMixin.at_post_traverse`, wilderness entry, wilderness return, wilderness step) each run their own `charge_movement` + `record_arrival` + `follow_companions` sequence. This change first extracts a single `after_successful_movement(player, room)` completion helper that all four paths call (preserving today's ordering), then calls `observe_room_entry(player)` from that helper and removes the `GridRoom.at_object_receive` onboarding hook. The observer is idempotent (one-transition rule) and a no-op for onboarded players, so the move back into the corridor after skipping stays inert.

**D2 — Keep quest room observation separate.** `QuestObservableRoomMixin`/`GridRoom` hooks for REACH/ESCORT progression remain unchanged; only onboarding observation moves.

**D3 — Wilderness flows through the same helper.** The wilderness entry/return/step branches are refactored to call the shared completion helper instead of their hand-duplicated sequences; no extra hook is added to `TerrainRoom`.

## Risks / Trade-offs

- **Observer timing**: arrivals now observe slightly later (after movement completes) — the same ordering quest observation uses; arrival-scene replay suppression depends on `first_arrival_seen`/state, both set by the observer, so behavior remains correct.
- **Double observation**: the GridRoom hook is removed, so no double-fire.
