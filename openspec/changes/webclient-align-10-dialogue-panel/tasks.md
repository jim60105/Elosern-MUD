# Tasks: webclient-align-10-dialogue-panel

## 1. Panel + protocol

- [ ] 1.1 `MODES` gains `"dialogue"`; oob-protocol snapshot shape mirror + Node-gate
  fixtures updated in lockstep.
- [ ] 1.2 `web/webclient/presentation/dialogue.py`: available form
  `{available, host{identity,display_name,portrait_ref}, bond_stage|null, line,
  choices[{keyword_id,label}]}` from change-07 session state; unavailable form
  `("dialogue_unavailable", "對話目前無法顯示")` when the session is not live or the
  host record is corrupt; exact-key validator; registry registration; UMD + Vue
  allowlists gain `dialogue`.

## 2. Coordinator + wire

- [ ] 2.1 Mode resolution creation > combat > dialogue-session-live > exploration;
  session live ⇒ `mode == "dialogue"` + panel available; session cleared ⇒ mode
  returns and the panel degrades to unavailable (never stale).
- [ ] 2.2 Adapter hook (07) result reaches the wire: the settled record precedes the
  existing snapshot publish; stale/discarded completions publish nothing new.

## 3. Tests + traceability

- [ ] 3.1 Evennia: presenter shape (bonded/non-bonded host, corrupt session →
  unavailable), validator rejections, mode-resolution matrix, live→clear snapshot
  transition, allowlist agreement. `covers_requirement` literal IDs for the
  panel/mode IDs land at the archive/sync commit (IDs unknown to the checker before
  sync; magic-xp P1 precedent); shard manifest updated for every new module.
- [ ] 3.2 Node gate: oob mirror fixtures pass `node --test`.

## 4. Verification

- [ ] 4.1 Focused Evennia labels + `tools.spec_traceability check`.
- [ ] 4.2 Live container probe (WS): scripted talk → snapshot presents mode dialogue
  + available panel with the settled line; move → mode returns to exploration, panel
  unavailable.

## 5. Chain note

- [ ] 5.1 Apply AFTER webclient-align-07-dialogue-session-state (session
  helpers/writer/clear seams). Change 08 (dialogue surface) depends on this change.
