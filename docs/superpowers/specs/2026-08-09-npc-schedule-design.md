# NPC Schedules — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The `npc_schedules` world-clock settlement source (master design §6.5), the `NPC.schedule`
data seam (master design §5.2), scheduled NPC movement and state, and interaction gating.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, §5.2 `NPC(LivingEntity) + schedule`,
§6.5 settlement stage `npc_schedules`). Where this document conflicts with the master design, the
master design wins unless this document explicitly amends it.

---

## 1. Product Context

The world-clock settlement order lists ten stages; nine are registered with concrete sources.
`npc_schedules` is the only stage name that exists in `world/rules/clock.py` (`_STAGE_ORDER`, line
41) with no `register_event_source("npc_schedules", ...)` caller anywhere in the codebase — the
other four world-event seams (`caravan_arrivals`, `shop_hours`, `quest_deadlines`,
`instance_reclamation`) all have live sources. The `NPC.schedule` attribute is likewise an unused
placeholder (`typeclasses/npcs.py:31`, `AttributeProperty(default=None)`).

This change claims both seams: NPCs with schedule data move to designated rooms and change visible
states at fixed world times, and their states gate player interactions. The system is fully
deterministic and offline-playable: no LLM and no image-generation service participates.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| S1 | **Unified schedule-entry model.** One entry shape covers both movement (with a destination) and state change (with a state value); both share the same tick field and settlement path. | One data model, one settlement path. A storekeeper retiring to the back room and a guard resting at noon are the same concept with different fields filled. |
| S2 | **Dual data source.** `rulebook/npc_schedules.yaml` ships role templates (`guard`, `storekeeper`, `resident`, ...); an NPC references one by `db.schedule = {template: <key>, overrides: {...}}`. Special NPCs (event or major characters) may instead store a full entry list directly on `db.schedule` with no template. | Follows D9 ("balance numbers are data that should be tunable without touching Python"); special NPCs are not forced into a template shape. |
| S3 | **Real Exit traversal.** At the scheduled moment, a move entry resolves the destination and walks the actual Exit path from the NPC's current room (honoring locks and vetoes). `at_post_traverse` is already a no-op for non-player objects (`charge_movement` and `record_arrival` only act on `PlayerCharacter`), so NPC movement never advances the clock, never records map knowledge, and never triggers companion follow. | Shares the single movement pipeline (map-movement-clock / party-follow idiom); time cost remains a player-action concept (D4). |
| S4 | **State gates interactions.** A busy/resting state makes `talk` (scripted and free-form), `engage`, and the NPC's hosted services return a fixed stable rejection reason; the NPC does not leave the room for a state change. | Under the unified model a state is consequential, not decorative; the player sees one coherent response path. |
| S5 | **Per-entry skip on failure.** A failed settlement (missing exit, locked exit, vanished destination) logs a bounded diagnostic and an event, skips that entry, and continues with the rest; it never blocks the settlement segment or rolls back other NPCs. | Matches the project's deliberate-skip tolerance; one NPC's broken schedule must not stall the clock. |

---

## 3. System Design

### 3.1 Data model

`world/rules/rulebook/npc_schedules.yaml`:

```yaml
schema_version: 1
templates:
  guard:
    - { tick_offset: 21600, kind: move,  target: "north_gate" }
    - { tick_offset: 50400, kind: state, state: "resting" }
    - { tick_offset: 64800, kind: move,  target: "barracks" }
```

Entry fields:

- `tick_offset`: seconds since world day start (resolved through the existing clock day math);
  entries repeat every world day.
- `kind`: `move` or `state`.
- `move` entries carry `target`: a stable key resolved through existing registries (anchors, known
  NPC posts) or a direct dbref override.
- `state` entries carry `state`: a bounded value from the rulebook's declared state vocabulary
  (e.g. `duty`, `resting`, `busy`).

Per-NPC storage (`npc.db.schedule`, JSON-safe, schema-versioned):

- template reference: `{"schema_version": 1, "template": "guard", "overrides": {...}}`
- full custom list: `{"schema_version": 1, "entries": [...]}` (special NPCs)

> **Amended 2026-08-09 (rubber-duck review).** Four clarifications:
> 1. Templates gain an optional `default_state` field (vocabulary-validated, default `None`);
>    a successful `move` settlement sets `schedule_state` to the template's `default_state` —
>    move entries themselves never carry a `state` field.
> 2. Schedules are assigned through one validated API,
>    `set_npc_schedule(npc, schedule)` (the sole writer of `npc.db.schedule`), which validates,
>    records an `effective_from_tick` (the assignment world tick), and maintains a persistent
>    `schedule` tag on the NPC. Settlement queries by that tag, so post-startup spawned or
>    reassigned NPCs are always found.
> 3. Only occurrences with `due_tick >= effective_from_tick` settle — assigning a schedule
>    mid-day never replays entries whose due moment already passed.
> 4. `ScheduledEvent`s carry JSON-safe payloads (stable NPC identity; `state` or `from`/`to`
>    target) and `due_tick = day_start + tick_offset`, never the settlement end tick.

Runtime state: `npc.db.schedule_state` (current state value or `None`), written exclusively by
`world/rules/npc_schedules.py`.

### 3.2 Settlement

`world/rules/npc_schedules.py`:

```python
def settle_npc_schedules(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Settle every due schedule entry in (start_tick, end_tick]."""

def interaction_reason(npc, interaction_kind) -> str | None:
    """Return a stable rejection reason when the NPC's schedule state blocks an interaction."""
```

- Registered through `register_event_source("npc_schedules", settle_npc_schedules)` so the stage
  order in `_STAGE_ORDER` becomes fully real.
- Scans NPCs carrying the persistent `schedule` tag (maintained by the validated assignment API and
  startup sync) and, for each entry with `start_tick < day_start(entry_day) + tick_offset <= end_tick`
  and `due_tick >= effective_from_tick`, settles it:
  - `move`: resolve destination → find the real Exit from the NPC's current room that leads to it
    → traverse (locks and vetoes apply) → on success set `schedule_state` to the template's
    `default_state` and emit `npc_arrived`; on failure skip with a bounded diagnostic only (no
    failure event).
  - `state`: update `schedule_state` and emit `npc_state_changed`.
- Due occurrences settle in `(due_tick, npc_stable_id, entry_index)` order, so one multi-day
  `advance()` produces the same locations as repeated day-by-day advances; duplicate `tick_offset`s
  within one NPC use stable entry-index tie-break.
- Multi-day skips use boundary arithmetic (per-entry day math), never per-second iteration,
  mirroring caravan/shop settlement.

### 3.3 Interaction gating

`talk` (scripted and free-form), `engage`, and NPC-hosted services query `interaction_reason()`
before proceeding. A non-`None` result returns the existing stable-rejection path with the authored
Traditional Chinese line (e.g. 她現在正忙著整理貨架，沒有理會你。). A `None` result means the
interaction proceeds exactly as today.

> **Amended 2026-08-09 (rubber-duck review).** The gate is consulted at **every** surface that
> resolves a local NPC host and performs a service transaction — the Telnet commands *and* the
> WebClient service action adapters (`shop.buy` / `shop.sell` / guild operations) — so a busy
> merchant cannot be traded through the browser while blocked by the command path. The
> interaction kinds are enumerated (`talk`, `engage`, `service_shop`, `service_guild`) with their
> exact consult points. `engage` is declared as a gate kind but is currently unreachable: the
> engagement surface rejects non-hostile targets (`SessionReason.NOT_HOSTILE`) before any
> schedule check, and the schedule model is NPC-only; the kind is carried so a future
> NPC-combat change inherits the gate.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/rules/clock.py` | `npc_schedules` source registration — the last unregistered stage |
| `typeclasses/npcs.py` | `schedule` placeholder attribute activated: template reference or full entry list |
| `typeclasses/exits.py` | Reuses the traversal path (locks/vetoes unchanged); non-player no-ops already built in |
| talk / engage / service entry points | Query `interaction_reason()` for gating |
| `world/lore/` registries | Stable `target` key resolution (anchors, known NPC posts) |
| Startup sync | Idempotent schedule confirmation/indexing, same pattern as `sync_guard_npc()` |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| Missing or malformed template | NPC has no schedule (`log_warn`); game continues |
| Missing / locked / vanished Exit at due time | Per-entry skip + bounded diagnostic; NPC stays put |
| Startup sync failure | `log_warn`; NPC without schedule; startup not blocked |
| LLM / art services offline | Irrelevant — the system is fully deterministic |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Pure logic | `unittest.TestCase`: entry parsing (template + overrides vs full list), tick boundary arithmetic, multi-day skip, state vocabulary validation |
| Evennia integration | `EvenniaTest`: due movement along real Exits (locked exit skipped), state updates, gating stable reasons for talk/engage/services, player movement never triggers NPC schedule, failure isolation between NPCs |
| Clock | `npc_schedules` registered; stage position within the fixed `_STAGE_ORDER`; existing `settlement-stage-order` tests stay green |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `npc-schedule-model` | 11 (`world-clock`), lore registries | `rulebook/npc_schedules.yaml` templates, `db.schedule` data model (template ref / full list), parsing and validation, startup sync, pure unit tests |
| 2 | `npc-schedule-runtime` | 1, 13b (movement pipeline), 19/23d (talk surface) | Clock source registration, settlement, Exit traversal, `interaction_reason()` gating, event emission, integration tests |

---

## 8. Out of Scope

- NPC AI, personality, or dialogue content (scripted and LLM dialogue remain separate).
- Per-NPC schedules authored through the import schema (import cards keep the current verbatim
  fields; a future import extension owns that).
- Schedule-driven shop opening hours (owned by `shop_hours`); NPC state gating is a separate layer
  on top of shop hours.
- Any change to combat, quest, or economy mechanics beyond the interaction gate.
- Multi-day weekly schedules (the model repeats daily; a weekly-cycle extension is a future seam).

---

## 9. Open Questions Carried Forward

- None blocking. Weekly schedule cycles, schedule authoring through imports, and schedule-driven
  speech lines are deliberately deferred seams; the entry model and settlement path are the hooks
  they would extend.
