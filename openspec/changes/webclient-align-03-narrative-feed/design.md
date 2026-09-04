# Design: webclient-align-03-narrative-feed

## Context

The draft owns the caption as `.feed > .feed-inner` (panel fill, blur 7, hairline border,
shadow, left `::before` gradient rule) with a head row (uppercase tracking label +
right-aligned `完整日誌` capsule on `--ink-780`, radius 99) and semantic log-line classes
(`.sys` sans/`paper-500` with `◈ ` seal prefix; `em` gold; `.cmt` mp-blue — combat arrives in
change 08). The live `NarrativeFeed.vue` renders the unread indicator + a plain button with no
head row and no hairline, and committed `sys`-kind lines (store `NARRATIVE_KINDS` includes
`sys`) render unstyled. `ConditionChips.vue` renders an explicit `無條件` statement for the
empty list — a clause the contextual-hud spec itself pins, so the spec changes with the code.

The stream choice-point (`ChoicePointBlock.vue` + `lib/choicepoint.js` + the
`stream_end_block.js` facade wrapper used only by it) renders the same cards the dock 建議 pane
renders; `ActionDock` already suppresses its legacy section when the router 建議 frame is the
surface. The draft's only suggestion surface is `.pane[data-pane=suggest]` in the dock.

## Goals / Non-Goals

**Goals:**
- Caption chrome, head row, and capsule match the draft values verbatim.
- `sys` lines get the draft treatment; emphasis gold. Committed kinds only.
- Empty condition list → no island in the DOM.
- One suggestion surface: the dock pane. Stream block, its layer, wrapper, story, and manifest
  entry removed together (coverage-gate lockstep).

**Non-Goals:**
- No changes to the tokenize→vnode pipeline, `.inp` echoes/divider, `.map-art`, unread/live
  region, scroll pinning, the full-log focus trap, or prose-scale setting.
- The preserved UMD modules (`web/static/webclient/js/elosern/stream_end_block.js`,
  `option_cards.js`) and the dependency-free Node gate are frozen and untouched; only the Vue
  app's use of the stream-end facade is removed.
- Dialogue and combat `.cmt` variants belong to change 08.

## Decisions

- **De-dup direction:** delete the stream side, keep the dock pane. The draft shows cards only
  in the dock; the dock already owns dismiss, digit keys, and the count badge. Alternative
  (keep stream, drop pane) rejected: the draft's tab badge and digit-key legend both name the
  dock surface.
- **Traceability transition:** the choice-point capability's surviving semantics (generating →
  ready in place, transport-reset removal, card/dispatch identity, degraded-never-in-stream)
  are re-anchored as ADDED requirements on the suggestions pane, with the old stream
  requirements REMOVED. Existing choicepoint tests are migrated to dock-pane assertions and
  carry `@covers_requirement` for the new IDs; the removed IDs stay uncovered in the main spec
  until this change is archived and its delta synced — the gap is visible by design, never
  bypassed (AGENTS traceability rule).
- **Head label source:** committed mode only (`敘述` in exploration; `combat` → `戰鬥日誌`).
  No second state. The full-log capsule keeps the existing open/focus/Escape wiring; only its
  chrome moves into the head row.
- **sys mapping:** the renderer already knows the line kind; mount `.narr-line--sys` and style
  it with the draft rules including the `◈ ` `::before`. `err`/`out`/`in` keep current styling.

## Risks / Trade-offs

- Deleting the block layer touches the facade bootstrap in `bridge.js` — the block controller
  construction goes with it; the fallback text path (legacy view) is unaffected.
- The `無條件` clause has pinned tests (vitest + contextual-hud scenario) — updated in the same
  change so no stale pins survive.
