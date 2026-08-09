# Tasks: npc-schedule-runtime

## 1. Settlement core

- [ ] 1.1 Implement `settle_npc_schedules(start_tick, end_tick)` in `world/rules/npc_schedules.py`:
  query NPCs carrying the persistent `schedule` tag, build the due-occurrence work list
  `(due_tick, npc_stable_id, entry_index)` for occurrences in `(start_tick, end_tick]` with
  `due_tick >= effective_from_tick`, settle in that order; `state` entries update
  `npc.db.schedule_state` and emit `npc_state_changed`
- [ ] 1.2 Settle `move` entries: resolve target (stable key via registries or dbref override) to a
  destination room, find the traversable real Exit from the NPC's current room (deterministic
  order), traverse it; on success set `schedule_state` to the template's `default_state` and emit
  `npc_departed` / `npc_arrived`
- [ ] 1.3 Emit events with JSON-safe payloads (stable NPC identity; `state` or `from`/`to` target)
  and `due_tick = day_start + tick_offset`
- [ ] 1.4 Register the source: `register_event_source("npc_schedules", settle_npc_schedules)` in
  the same composition-root pattern as the other sources (verify placement against the
  sync-ordering guard test)
- [ ] 1.5 Per-entry failure isolation: unresolvable target, no exit, locked exit, or vanished
  destination skips only that entry with a bounded diagnostic log and no failure event;
  settlement never raises and never rolls back other NPCs

## 2. Interaction gating

- [ ] 2.1 Implement `interaction_reason(npc, interaction_kind) -> str | None` (stable authored
  reasons; `None` when unblocked); declare the `talk`, `engage`, `service_shop`, and
  `service_guild` kinds
- [ ] 2.2 Consult the `talk` gate in the scripted-talk entry path (`commands/talk.py`): blocked
  interactions show the stable reason and write no state (no affinity, no guide progress, no
  turn-in)
- [ ] 2.3 Consult the `talk` gate in the free-form seam (`typeclasses/npcs.py::at_talked_to` /
  `run_npc_exchange`): blocked interactions build no prompt, run no pipeline, append no memory,
  apply no intent
- [ ] 2.4 Consult the `service_shop` gate in the shop buy/sell commands (`commands/economy.py`)
  **and** the WebClient `shop.buy` / `shop.sell` adapters
  (`web/webclient/actions/service_actions.py`): blocked hosts return the stable reason with no
  transaction on every surface
- [ ] 2.5 Consult the `service_guild` gate in the guild operation commands (`commands/guild.py`)
  **and** the WebClient guild action adapters whenever the resolved local host is the NPC

## 3. Tests

- [ ] 3.1 `EvenniaTest`: due state entry updates `schedule_state` + emits `npc_state_changed`
  with payload
- [ ] 3.2 `EvenniaTest`: due move entry relocates along a real Exit, sets the template's
  `default_state`, emits `from`/`to` events with the entry's due tick; clock tick unchanged; no
  map knowledge recorded; no companion-follow side effect
- [ ] 3.3 `EvenniaTest`: locked exit and unresolvable target skip only that entry (log only, no
  failure event); other NPCs settle normally
- [ ] 3.4 Multi-day skip settles every due occurrence exactly once in `(due_tick, npc_stable_id,
  entry_index)` order, and equals repeated day-by-day advances (A→B→A route)
- [ ] 3.5 Mid-day assignment: passed occurrences never settle (no replay)
- [ ] 3.6 Gate tests on every surface: scripted talk blocked (stable reason, no
  affinity/guide/turn-in writes), free-form talk blocked (no prompt/pipeline/memory/intent),
  merchant blocked via command AND WebClient adapters (no transaction), guild host blocked via
  command AND WebClient action (no state change), `engage` kind declared and unreachable,
  unblocked NPC behaves exactly as before
- [ ] 3.7 Registration test: `npc_schedules` source is `settle_npc_schedules`; existing
  `settlement-stage-order` stage-order tests stay green

## 4. Verification

- [ ] 4.1 Run `openspec validate npc-schedule-runtime --strict`
- [ ] 4.2 Run the affected package tests (`world/rules`, talk surfaces, clock suites,
  webclient service action tests); keep `git diff --check` clean
- [ ] 4.3 Record canonical requirement IDs (`tools.spec_traceability list` after sync) and add
  `covers_requirement` annotations on the tests that establish the new and modified
  requirements; run `spec_traceability check`
