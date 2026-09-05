# Tasks: webclient-align-10-dialogue-panel

## 1. Panel + protocol

- [x] 1.1 `MODES` gains `"dialogue"`; oob-protocol snapshot shape mirror + Node-gate
  fixtures updated in lockstep.
- [x] 1.2 `web/webclient/presentation/dialogue.py`: available form
  `{available, host{identity,display_name,portrait_ref}, bond_stage|null, line,
  choices[{keyword_id,label}]}` from change-07 session state; unavailable form
  `("dialogue_unavailable", "對話目前無法顯示")` when the session is not live or the
  host record is corrupt; exact-key validator; registry registration; UMD + Vue
  allowlists gain `dialogue`.

## 2. Coordinator + wire

- [x] 2.1 Mode resolution creation > combat > dialogue-session-live > exploration;
  session live ⇒ `mode == "dialogue"` + panel available; session cleared ⇒ mode
  returns and the panel degrades to unavailable (never stale).
- [x] 2.2 Adapter hook (07) result reaches the wire: the settled record precedes the
  existing snapshot publish; stale/discarded completions publish nothing new.

## 3. Tests + traceability

- [x] 3.1 Evennia: presenter shape (bonded/non-bonded host, corrupt session →
  unavailable), validator rejections, mode-resolution matrix, live→clear snapshot
  transition, allowlist agreement. `covers_requirement` literal IDs for the
  panel/mode IDs land at the archive/sync commit (IDs unknown to the checker before
  sync; magic-xp P1 precedent); shard manifest updated for every new module.
- [x] 3.2 Node gate: oob mirror fixtures pass `node --test`.

## 4. Verification

- [x] 4.1 Focused Evennia labels + `tools.spec_traceability check`.
- [x] 4.2 Live container probe (WS): scripted talk → snapshot presents mode dialogue
  + available panel with the settled line; move → mode returns to exploration, panel
  unavailable.

## 5. Chain note

- [x] 5.1 Apply AFTER webclient-align-07-dialogue-session-state (session
  helpers/writer/clear seams). Change 08 (dialogue surface) depends on this change.

## 9. Post-critique hardening (rubber-duck `DuckChange10`)

- [x] 9.1 確認 text-command `talk` 的 presentation 刷新真實存在（`inputfuncs.text` →
      `observe_command_settlement` → full snapshot；以 e2e 測試固化，见 9.5）
      — Blocking #1 為 false positive，證據：e2e probe `MODE: dialogue AVAIL: True`
- [x] 9.2 Enforce the mode/panel atomicity invariant at the coordinator: every panel
      update injects a freshly rendered `dialogue` panel (mirrors the UMD mirror;
      closes the stale-panel window the critique found in the recompute/reconcile
      split)
- [x] 9.3 Close the UMD duplicate-keyword registry hole: `seen` is
      `Object.create(null)` so a literal `__proto__` keyword_id cannot defeat the
      own-property check
- [x] 9.4 Python `keyword_id` validation rejects lone surrogates exactly like the UMD
      mirror (validator parity drift closed)
- [x] 9.5 Tests: text-command `talk` e2e publishes `mode: dialogue` with the available
      panel; coordinator injection carries `dialogue` in unrelated subset updates;
      node fixtures for `__proto__` duplicates and lone-surrogate keyword ids. The
      injection rule is server-emission behavior (the client must still accept a
      subset update that omits `dialogue`), so it is defended by the coordinator
      tests only; the departure push inherits the epoch guard of
      ``publish_panel_update``, covered by ``test_coordinator_push``.
- [x] 9.6 Delta spec: state the atomicity guarantee as a scenario in the
      `webclient-oob-protocol` delta; re-validate `--strict`
