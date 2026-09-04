# Tasks: webclient-align-07-dialogue-session-state

## 1. Session helpers in the deterministic core

- [ ] 1.1 `world/rules/dialogue.py`: JSON-safe session helpers as the ONLY writers —
  `open_or_refresh_dialogue(character, npc, line)` (bounded line truncation at write),
  `clear_dialogue_session(character, npc=None)`, `live_dialogue_session(character)` returning
  the session only when the stored dbid resolves to a present, interactable NPC in the
  character's location; storage on `db.dialogue_session` (`{npc_id, line, updated_tick}`).
- [ ] 1.2 Observability: `session_open`/`session_clear` boundary `log_info` events with
  `char`/`npc` context through the `world.observability` facade; run the observability lint.

## 2. Writer + clearer wiring

- [ ] 2.1 `explore.talk_scripted` adapter: hook the record into the `run_scripted_talk`
  success-result branch (the branch that delivers the authored response); greeting/no-keyword
  and failure paths record nothing.
- [ ] 2.2 `explore.talk_freeform` settled path → record BEFORE the existing newer-revision
  snapshot publish; stale-completion path records nothing.
- [ ] 2.3 `commands/talk.py`: hook the record into the scripted-success result branch of
  `run_scripted_talk`; greeting/no-keyword and turnin-list paths excluded.
- [ ] 2.4 Clear seams: `world/rules/movement_settlement.py::settle_movement` success;
  `world/rules/combat_session.py::engage`; NPC cleanup seams (leave-room / despawn /
  leave-party purge) clearing when the session NPC matches.
- [ ] 2.5 Every open/refresh/clear marks the character's presentation dirty.

## 3. Tests + traceability

- [ ] 3.1 Evennia modules: session lifecycle (open via WS, open via talk cmd, refresh in place,
  move-clears, engage-clears, departure-clears, stale-dbid not-live, offline scripted drive);
  adapter hooks (scripted records on success branch only, freeform records-before-publish,
  stale records nothing). `covers_requirement` literal IDs land at the archive/sync commit
  (IDs unknown to the checker before sync; magic-xp P1 precedent);
  `.github/evennia-shards.json` updated in the same change.

## 4. Verification

- [ ] 4.1 Focused Evennia labels + `tools.spec_traceability check` + observability lint.
- [ ] 4.2 Server-side probe: scripted talk → session state present; move → cleared; engage →
  cleared (no client-visible surface yet — the panel/mode ship in webclient-align-10).

## 5. Chain note

- [ ] 5.1 webclient-align-10-dialogue-panel consumes these helpers for its `dialogue` panel +
  mode; webclient-align-08's surface depends on 10, not on this change.
