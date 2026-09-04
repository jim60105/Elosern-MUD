<!-- Scope note (2026-09-04 split): the dialogue panel + mode protocol decisions moved to
     webclient-align-10-dialogue-panel; this design covers the session-state decisions only. -->
# Design: webclient-align-07-dialogue-session

## Context

`world/rules/dialogue.py` owns the scripted tables: `dialogue_key_for(npc)`, `table_response`,
`run_scripted_talk(npc, character, keyword)` → `ScriptedTalkResult` (the same seam
`explore.talk_scripted` and `talk` use), and freeform runs `npc.at_talked_to(speech, actor,
client)` through the guarded AI pipeline (offline: authored greeting/silence). The interact
target already ships ≤16 `{keyword_id, label}` descriptors from the dialogue table — the
panel's `choices` reuse that vocabulary owner. Movement completes through
`world/rules/movement_settlement.py::settle_movement`; combat starts through
`world/rules/combat_session.py::engage`; party membership purge (`world/rules/party.py::
purge_npc_memberships`) already walks NPC-despawn cleanup.
The coordinator resolves committed mode today as creation-pending → creation, active combat →
combat, else exploration.

## Goals / Non-Goals

**Goals:**
- Session truth: `db.dialogue_session` on the character — `{npc_id, line, updated_tick}` (plain
  JSON-safe dict; `npc_id` is a dbid, presence re-resolved per read; no live refs).
  `world/rules/dialogue.py` gains the ONLY read/write helpers (`open_or_refresh_dialogue`,
  `clear_dialogue_session`, `live_dialogue_session(npc-present check)`).
- Writers: `explore.talk_scripted`/`explore.talk_freeform` adapter success paths and the `talk`
  command path record `(npc, response line)`. Clearers: successful `settle_movement` of the
  character, `combat_session.engage` involving the actor, NPC leave-room/despawn/leave-party
  cleanup touching the session NPC. No other writer.
- `dialogue` panel v1 (available only when `live_dialogue_session` resolves; else
  `("dialogue_unavailable", "對話目前無法顯示")`): host triple `{identity, display_name,
  portrait_ref: null}` (party vocabulary), `bond_stage` = `npc.relations.stage_for(player).name`
  when the host is a bonded NPC else null, `line` = session line, `choices` = the host's table
  descriptors (≤16, `{keyword_id, label}`).
- Mode order `creation > combat > dialogue-live > exploration`; exploration/character panels
  keep shipping unchanged under `dialogue` mode; every session open/clear marks presentation
  dirty (mode + dialogue panel; clear additionally re-pushes nothing else beyond the rhythm).
- Offline: scripted path fully drives open/refresh/line; freeform degrade path records its
  authored line; no panel write requires any network service.

**Non-Goals:**
- No client surface (change 08), no AI-authored choices (choices are table-derived only —
  freeform conversation does not synthesize buttons), no dialogue history transcript on the
  panel (latest line only; history stays in the narrative stream), no explicit end-verb (the
  design doc defers one; movement/engage/departure clear it).

## Decisions

- **Session value is the rendered line, not a reference:** storing the composed reply keeps the
  presenter a pure reader and keeps the wire honest even if the NPC's table later changes; it is
  server-authored prose, bounded by the shared narrative-line bound (truncated at write).
- **Presence is re-resolved, never trusted:** `live_dialogue_session` requires the npc dbid to
  resolve to a present, interactable NPC in the character's location; a stale session degrades
  to the unavailable form (and the next clear seam or talk retires it) — mirrors party's stale-
  dbid filtering.
- **Bond stage disclosure:** stage NAME only (never affinity numbers), same rule as party rows;
  non-bonded or affinity-less hosts disclose null.
- **`MODES` extension is protocol-visible:** server `MODES`, snapshot/update validator, UMD mode
  allowlist, and the Vue store's mode handling all gain `dialogue` in the same change (the
  panel three-list agreement test extends to modes).
- **Freeform double-publish interplay:** the freeform adapter already publishes a full snapshot
  at one newer revision on settle; the session write happens BEFORE that publish so the snapshot
  carries mode `dialogue` atomically — no intermediate mode flap.
- **`talk` command parity:** the text-command path records the same session (design doc: the
  writer is the deterministic core, not the WS surface), so a `talk` reply also opens the
  session and re-commits mode `dialogue` — presentation parity between surfaces, no new text
  command.

## Risks / Trade-offs

- Mode flip-flop at movement boundaries is possible if clear and settle ordering races; the
  session write and the movement commit share the same tick ordering inside `settle_movement`'s
  transaction, and the coordinator recomputes mode per push — verified by a lifecycle test
  (talk → move → exploration).
- The panel discloses the latest line only; a client wanting scrollback reads the narrative
  stream (single source, no duplication on the OOB channel).
