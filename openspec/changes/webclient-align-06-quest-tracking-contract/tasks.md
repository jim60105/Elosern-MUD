# Tasks: webclient-align-06-quest-tracking-contract

Scope note: the client surfaces (tracker island, quest-browser toggle, showcase) were split
into webclient-align-09-objective-tracker-ui. This change is the server contract only.

## 1. Tracking state in the deterministic core

- [ ] 1.1 `world/quests/runtime.py`: `tracked: bool = False` on `QuestRecord`; `to_storage`
  writes it, `from_storage` defaults a missing key to false (no rewrite); `accept_quest` never
  sets it.
- [ ] 1.2 New lifecycle op `set_quest_tracked(actor, quest_id, tracked)`: full-log
  validate-before-replace; reject tracked=true for non-`in_progress` records and beyond the cap
  of 3 (module constant); untrack idempotent; rejection raises the transition error with zero
  writes.

## 2. WS action + services panel v4

- [ ] 2.1 Action registry + `service_actions.py`: `guild.quest_track` exact payload
  `{quest_id, tracked: bool}`; adapter re-resolves the actor's log, calls
  `set_quest_tracked` once, surfaces the cap/terminal refusal as a bounded rejected message;
  no `GuildStaff` host requirement.
- [ ] 2.2 `world/rules/service_view.py` quest rows gain `tracked`;
  `web/webclient/presentation/services.py`: `SERVICES_SCHEMA_VERSION = 4`, row validator exact
  keys + `tracked: bool` mirror.

## 3. Objectives panel

- [ ] 3.1 New `web/webclient/presentation/objectives.py`: available form from
  `read_records` filtered to `tracked && in_progress` (quest-log order, ≤3) —
  `{quest_id, display_name, objective_line (describe_objective), stage_index, stage_total,
  stage_progress, objective_quantity, reward_copper (offer copper or None), deadline_line
  (describe_deadline or None)}`; empty → `rows: []`; `QuestDataError` → shared unavailable form.
- [ ] 3.2 Exact-key validator; registry registration; UMD + Vue allowlists gain `objectives`
  (three-list agreement test extended).
- [ ] 3.3 Coordinator invalidation: quest write seams (accept/abandon/fulfil/fail +
  acquire/planner/room_observation/transitions progress paths) and `set_quest_tracked` mark the
  holder's presentation dirty for `services` AND `objectives`.

## 4. Tests + traceability

- [ ] 4.1 Evennia: runtime tests (round-trip with `tracked`, legacy-key default, cap 4th refusal
  zero-write, terminal refusal, untrack idempotence) in `world/quests/tests/`; presenter tests
  (tracked-only rows, guild-hall independence, corrupt-log degradation, validator rows,
  track/progress/fulfil re-push) in `web/webclient/presentation/tests/`; adapter tests (dispatch
  once, cap refusal bounded message, schema rejects extra fields). Land `covers_requirement`
  literal IDs at the archive/sync commit (IDs unknown to the checker before sync; magic-xp P1
  precedent); `.github/evennia-shards.json` updated for every new module in the same change.

## 5. Verification + design-doc amendment

- [ ] 5.1 Append the dated amendment to
  `docs/superpowers/specs/2026-09-04-webclient-redesign-alignment-design.md` §3 Change 6: the
  tracker derives from the host-independent `objectives` panel, not guild-host-gated services
  rows, and the client surfaces split into change 09; all other Change 6 decisions stand.
- [ ] 5.2 Focused Evennia labels + `tools.spec_traceability check`.
- [ ] 5.3 Server-side probe (WS `ui_action`): track → `guild.quest_track` accepted, `tracked`
  flips in the next services commit, `objectives.rows` gains the row; 4th track refused;
  non-`in_progress` refused (no client UI until change 09).

## 6. Chain note

- [ ] 6.1 webclient-align-09-objective-tracker-ui consumes this contract (panel + rows +
  action); change 08's tracker restatement chains change 09's contextual-hud requirement.
