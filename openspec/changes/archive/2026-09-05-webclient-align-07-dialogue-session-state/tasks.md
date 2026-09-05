# Tasks: webclient-align-07-dialogue-session-state

## 1. Session helpers in the deterministic core

- [x] 1.1 `world/rules/dialogue.py`: JSON-safe session helpers as the ONLY writers —
  `open_or_refresh_dialogue(character, npc, line)` (bounded line truncation at write),
  `clear_dialogue_session(character, npc=None)`, `live_dialogue_session(character)` returning
  the session only when the stored dbid resolves to a present, interactable NPC in the
  character's location; storage on `db.dialogue_session` (`{npc_id, line, updated_tick}`).
- [x] 1.2 Observability: `dialogue_session_open`/`dialogue_session_clear` boundary `log_info`
  events with `char`/`npc` context through the `world.observability` facade; run the
  observability lint.

## 2. Writer + clearer wiring

- [x] 2.1 `explore.talk_scripted` adapter: hook the record into the `run_scripted_talk`
  success-result branch (the branch that delivers the authored response); greeting/no-keyword
  and failure paths record nothing.
- [x] 2.2 `explore.talk_freeform` settled path → the adapter supplies the settled-line observer
  callback to `at_talked_to` (the seam invokes it only after the reply or authored degrade
  line is actually presented and the completion gate still passes), and the callback records
  BEFORE the existing newer-revision snapshot publish; the mid-flight-stale completion and the
  silent degrade record nothing.
- [x] 2.3 `commands/talk.py`: hook the record into the scripted-success result branch of
  `run_scripted_talk`; greeting/no-keyword and turnin-list paths excluded.
- [x] 2.4 Clear seams: `world/rules/movement_settlement.py::settle_movement` success;
  `world/rules/combat_session.py::engage`; NPC cleanup seams (leave-room / despawn /
  leave-party purge) clearing when the session NPC matches.
- [x] 2.5 Presentation sync rides the existing push rhythm (rubber-duck amendment,
  2026-09-05): the adapter paths publish a full snapshot after the action and the text-command
  path refreshes through `refresh_after_command`, both AFTER the session write/clear, so no
  dedicated push is wired by this state-only change — the session has no protocol-visible
  surface yet. The dedicated presentation fan-out is wired by webclient-align-10-dialogue-panel
  when it registers the `dialogue` panel and mode (mirroring the change-4 party-push seam).

## 3. Tests + traceability

- [x] 3.1 Evennia modules: session lifecycle (open via WS, open via talk cmd, refresh in place,
  move-clears, engage-clears, departure-clears, stale-dbid not-live, offline scripted drive);
  adapter hooks (scripted records on success branch only, freeform records-before-publish,
  stale records nothing). `covers_requirement` literal IDs land at the archive/sync commit
  (IDs unknown to the checker before sync; magic-xp P1 precedent);
  `.github/evennia-shards.json` updated in the same change.

## 4. Verification

- [x] 4.1 Focused Evennia labels + `tools.spec_traceability check` + observability lint.
- [x] 4.2 Server-side probe: scripted talk → session state present; move → cleared; engage →
  cleared (no client-visible surface yet — the panel/mode ship in webclient-align-10).

## 5. Chain note

- [x] 5.1 webclient-align-10-dialogue-panel consumes these helpers for its `dialogue` panel +
  mode; webclient-align-08's surface depends on 10, not on this change.
