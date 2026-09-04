# Proposal: webclient-align-03-narrative-feed

## Why

The narrative caption diverges from the draft in three verified ways: (1) its shell lacks the
draft's `.feed-inner` blur panel with the left hairline rule, the uppercase head row naming the
mode (`敘述` / `戰鬥日誌`), and the `完整日誌` capsule button; (2) committed `sys`-kind lines
render without the draft's semantic treatment (sans, `paper-500`, `◈` seal prefix); (3) the
choice-point block mounts suggestion cards at the stream end while the dock's 建議 pane renders
the same cards — the draft has exactly one suggestion surface, the dock pane. The condition
island also renders an `無條件` placeholder where the draft renders nothing.

## What Changes

- Feed shell restyled to the draft: panel fill + blur + hairline border + shadow, the
  left-side `::before` gradient rule, and a head row carrying the mode label (exploration
  `敘述`, combat `戰鬥日誌`) plus the `完整日誌 ↑` capsule; the unread indicator sits beside the
  label. Bounded height, the single full-log control, focus-trap/Escape contract, and the same
  markup renderer are unchanged.
- Semantic line styling inside the log: committed `sys`-kind lines get the draft's `.sys`
  treatment with the `◈` prefix; emphasis renders gold `--gold-400`. No new data kinds are
  invented — only committed line kinds are restyled.
- Empty condition list renders no island at all (replaces the explicit `無條件` statement).
- **BREAKING (surface contract):** the stream choice-point block is removed. The dock's 建議
  tab pane becomes the only suggestion surface (its existing suppression logic already keeps
  it authoritative). `ChoicePointBlock.vue`, the choicepoint block layer, the stream-end-block
  facade path it alone used, its story, and its component-manifest entry are deleted in
  lockstep; the generating/ready/dismiss/reconnect semantics keep governing the dock pane
  through `webclient-context-actions-suggestions`.

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-contextual-hud`: the narrative-caption requirement is restated with the draft's
  head row and panel chrome; the condition-chip requirement's empty-state clause becomes island
  absence; an added requirement pins the semantic line styling.
- `webclient-action-choicepoints`: all stream-side choice-point requirements are REMOVED
  (the dock pane contract in `webclient-context-actions-suggestions` already governs the one
  surviving surface).

## Impact

- `web/webclient-app/components/NarrativeFeed.vue`, `ChoicePointBlock.vue` (deleted),
  `FullLogOverlay.vue` (trigger unchanged), `ConditionChips.vue`, `lib/choicepoint.js` and
  `lib/stream_end_block.js` (deleted paths), `stores/elosern.js` (choicepoint layer),
  `stories/Action/ChoicePointBlock.stories.js` + `component-manifest.json` (removed in
  lockstep for the coverage gate), `tests/action/choice_point_block.test.js` (deleted with its
  removed requirements).
- Vitest caption/chip/suggestion-surface tests updated; no server or protocol change.
- Deleting the choice-point browser surface also deletes
  `web/tests/browser/test_browser_choicepoints.py` and its `.github/browser-shards.json`
  entry in the same change; the evidence-harness annotations in
  `web/webclient/tests/test_node_suite_evidence.py` retarget to the surviving dock-pane vitest
  files (old IDs stay pinned until archive/sync, then retarget to the new dock-pane IDs).
- Adds the `webclient-component-showcase` delta removing the choice-point enumeration from
  the manifest minimum and the action-dock family contract.
