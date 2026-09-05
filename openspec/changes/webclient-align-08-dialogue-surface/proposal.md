# Proposal: webclient-align-08-dialogue-surface

## Why

Changes 07/10 landed the session lifecycle, the `dialogue` panel, and `dialogue` mode, but the client
still presents conversation as plain narrative text: the draft's dialogue mode is a focused RPG
dialogue box (64px avatar, gold speaker line with 羈絆 stage, serif reply) with numbered choice
picks, a mirrored 對話選項 dock tab, and a HUD matrix where the whole cockpit STAYS visible while
dialogue is live. Without this change the server's dialogue mode has no surface — the panel would
sit committed and unrendered.

## What Changes

- **Visibility matrix gains the dialogue column** (REDESIGN §2): narrative caption visible
  (dialogue focus), HUD islands/vitals/conditions visible, minimap visible, party quickbar
  visible, objective tracker visible, action dock visible (dialogue form), command line visible,
  scene backdrop unchanged; creation stays creation-only. This amends the matrix requirement and
  the dialogue-time visibility clauses of the change-05 quickbar and change-06 tracker
  requirements (both currently gate to exploration+combat).
- **Feed dialogue variant**: while mode is `dialogue` and the panel is available, the narrative
  caption head label reads `對話` and the `完整日誌` capsule is NOT rendered (draft-exact); the
  caption presents the draft `.dlg` box — avatar (portrait via the art catalog when `portrait_ref`
  resolves, gold initial-letter fallback while the seam ships null), gold `who` line
  `display_name · 羈絆 stage` (stage segment only when `bond_stage` is non-null), and the serif
  `line` — followed by the numbered `.choices` picks from `dialogue.choices` (`1..n` mono badges;
  activating submits `explore.talk_scripted {npc_id, keyword_id}` under the existing dispatch
  contract) with the trailing `⌨ 自由對話 → 指令列` row that focuses the borrowed command line
  through the existing freeform-borrow path.
- **Dock dialogue form**: while mode is `dialogue` the action dock presents a single `對話選項`
  tab whose pane mirrors the same committed `dialogue.choices` list (same rows, same dispatch —
  one source, two presentations, per the draft), with the legend swapped to
  `數字鍵 1–4 選 · → 指令列自由對話` — change 01's shortcut-legend requirement, restated as
  MODIFIED in this change's delta (its "command-line hint contract" attribution was wrong: the
  legend owner is change 01, not the command line). Digit keys `1–4` activate the first four
  picks and `→` focuses the borrowed command line (orthogonal to
  the change-02 letter bindings; pointer and Enter dispatch identically).
- **No new persisted state, no new protocol surface**: purely committed-panel-driven rendering;
  no invented fields, no client-side dialogue history (the narrative stream keeps the transcript).

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-contextual-hud`: MODIFIED — the visibility matrix gains `dialogue`; the caption
  requirement (as modified by webclient-align-03-narrative-feed) gains the `對話` head label and
  the dialogue-mode capsule absence; the party quickbar requirement (as modified by
  webclient-align-05-party-hud) and the objective tracker requirement (as modified by
  webclient-align-09-objective-tracker-ui) include dialogue in their visible-mode sets. ADDED — the
  feed dialogue variant requirement and the dock dialogue pane requirement.

## Impact

- `NarrativeFeed.vue` (dialogue variant + head label branch), `ActionDock.vue`/`DockTabBar.vue`
  (dialogue root form + mirror pane), the keyboard router (digit picks in dialogue mode),
  `AppClient.vue`/`stores/elosern.js` (mode-gated anchors); styles per the draft `.dlg`,
  `.choices`, `.pick` tokens.
- No component-manifest change (the dialogue box renders inside the existing `NarrativeFeed`
  component family; the dock pane rides the existing pane renderers) — the showcase/deferred
  bookkeeping is untouched.
- Chained MODIFIED blocks: this delta re-states requirements as modified by changes 03/05/06 —
  apply/merge after those land (roadmap wave W3 after W1/W2, per the alignment design).
