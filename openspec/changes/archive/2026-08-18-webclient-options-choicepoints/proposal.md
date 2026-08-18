## Why

The AI action-options surface (overview decision A-6) is dual-placed: `ready` suggestion cards
appear both in the persistent dock section and as a choice-point in the narrative stream — the
VN-like placement where the player is actually reading the story. Without the stream placement
the "AI 建議" moment stays a sidebar detail; with it, the curated next-action question lands
exactly where the world is being described, while the shell keeps a single append/scroll owner for
the narrative.

## What Changes

- A new narrative choice-point layer driven solely by committed `context_actions` suggestions
  state (`panels["context_actions"].suggestions`), consuming the presentation store's `subscribe`
  notifications after each `commitPresentation`:
  - `generating` appends one muted stream-end line "AI 正在構思建議…"; a generating →
    generating commit renders nothing new (the line stands until `ready` replaces it).
  - `ready` replaces the generating line **in place** with the card group.
  - `unavailable` (initial state, dismiss) and any context_actions panel absence or non-exploration
    mode removes the block; `degraded` is never rendered in the stream (dock-only rule from the
    webclient design doc §4).
- The choice-point is a **movable stream-end block** owned by the `window.Elosern.narrativeInput`
  facade (goldenlayout.js): narrative text appended *after* the block was inserted moves the block
  to the new stream end instead of leaving it floating above newer text; scroll-keep and the
  unread-marker behavior stay single-owner (design D5), so no new append path is created.
- Choice-point cards reuse the exact dock card renderer/component from the
  `webclient-options-surface` change (one card renderer, one click path): same DOM, same
  `ui_action` envelope, same rejection toasts, and the same "✕ 清除建議" dismiss control
  (`options.dismiss`, webclient doc §5) attached to the stream group.
- Both Node and browser suites cover the async race: look output, talk replies, and scene-flavor
  pushes that land after a `ready` commit move the block to the new end instead of stacking above
  or below it (webclient doc §4 text-after-update ordering).

**BREAKING**: none. This is a client-only presentation addition; no protocol field, panel
version, or player command changes (`options.dismiss` is already an OOB action from the dismiss
change).

## Capabilities

### New Capabilities
- `webclient-action-choicepoints`: the narrative-stream placement of AI action suggestions —
  generating/ready rendering at the stream end, in-place generation-to-ready replacement,
  removal on unavailable/dismiss/non-exploration states, degraded never in the stream, the
  movable end-block invariant (text appended later relocates the block), the shared dock card
  component and click path, and the stream dismiss control.

### Modified Capabilities
<!-- None: the markup pipeline (webclient-narrative-markup) and the input-line echo catalog
     (webclient-input-narrative) keep their exact requirement contracts; choice-points insert a
     fixed DOM block through the existing facade, never through the markup or echo paths. -->

## Impact

- **Code (client only)**:
  - `web/static/webclient/js/plugins/goldenlayout.js` — the `narrativeInput` facade grows a
    stream-end block API (attach/move/replace/remove) used by the choice-point layer, preserving
    the existing append/scroll/unread behavior.
  - `web/static/webclient/js/plugins/` (new choice-point module) — subscribes to the presentation
    store, owns the generating/ready in-place lifecycle, and renders cards through the shared
    component from `webclient-options-surface`.
  - `web/static/webclient/js/elosern/protocol.js` — untouched by this change (the suggestions
    payload is already part of the context_actions v5 contract from the surface change); the
    choice-point only reads committed panel state.
- **Tests**: Node tests in `web/static/webclient/js/tests/` (ordering, in-place replacement,
  removal, degraded exclusion, click envelope parity with the dock) and one browser test file
  that boots a shared server (no combat sessions — the combat-browser-server rule does not
  apply), following the repo's serial-owner and shard conventions.
- **Downstream**: depends on `context-actions-suggestions` (suggestions payload) and
  `webclient-options-surface` (shared card renderer + dock section); consumed by nobody else.
  `docs/game/commands.md` and `docs/game/command-reference.md` are unaffected (no player command
  changes). New main-spec requirements receive `covers_requirement` annotations per the
  spec-traceability workflow.