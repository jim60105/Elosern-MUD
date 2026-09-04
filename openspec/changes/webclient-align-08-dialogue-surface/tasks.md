# Tasks: webclient-align-08-dialogue-surface

## 1. Store + derived model

- [ ] 1.1 Expose committed `dialogue` panel availability + host/bond/line/choices in the Vue
  store; one shared derived view-model helper (host triple, who-segment rule, picks, digit
  window) reused by the feed, the dock pane, and their stories.

## 2. Feed dialogue variant

- [ ] 2.1 `NarrativeFeed.vue`: mode+availability branch — head label `對話` with no `完整日誌`
  capsule; `.dlg` box (gold-initial/portrait avatar, `display_name · 羈絆 <stage>` who line,
  serif `line`); `.choices`/`.pick` numbered rows + trailing `⌨ 自由對話 → 指令列` row per the
  draft tokens; session line rendered once with the live-region announcement invariant; plain
  fallback when the panel is transiently unavailable.
- [ ] 2.2 Free-dialogue row focuses the borrowed command line through the existing freeform
  path; pick activation dispatches `explore.talk_scripted {npc_id, keyword_id}`.

## 3. Dock dialogue form

- [ ] 3.1 `dialogue.root` descriptor in the resolver registry: single `對話選項` tab; pane rows
  from the same derived model; unavailable panel → shared degradation marker with the
  server-authored reason; teardown decision point gains `dialogue.root` (mode switch resets).
- [ ] 3.2 Legend swaps to `數字鍵 1–4 選 · → 指令列自由對話` (kbd `→`) while the dialogue form
  presents, per the shortcut-legend requirement restated in this change's delta; digit keys
  1–4 activate rendered picks and `→` focuses the borrowed command line, only while the
  dialogue form presents (never intercepted from the input field); pointer/Enter/digit share
  the router dispatch entry.

## 4. Tests

- [ ] 4.1 Vitest (feed): box fields incl. bond-null who segment; dispatch-once pick payload;
  free row focuses input without dispatch; announce-once live region; transient-unavailable
  fallback; head label/capsule matrix across the three visible modes.
- [ ] 4.2 Vitest (dock/router): `dialogue.root` rows verbatim from panel; degradation marker;
  feed/dock single-source equality; digit + arrow-key scoping (dialogue form vs focused input);
  legend variant swap on form flip with the single-instance hook;
  teardown-to-dialogue-root stack reset.
- [ ] 4.3 Matrix test update: dialogue column visible across islands/minimap/party/tracker/
  command line; backdrop art unchanged on mode flip.

## 5. Verification

- [ ] 5.1 Focused Vitest labels + `tools.spec_traceability check`.
- [ ] 5.2 Live container check 1600x900: scripted talk → dialogue variant matches the draft
  screenshot region (avatar/who/serif/picks), digit pick submits, command line stays visible;
  move → cockpit returns to exploration presentation with no leftover box.

## 6. Chain note

- [ ] 6.1 Apply AFTER webclient-align-03/05/09/10 land (W3): the contextual-hud delta restates
  requirements as modified by those changes (tracker island = 09, dialogue panel/mode = 10);
  rebase the chained blocks if their texts move.
