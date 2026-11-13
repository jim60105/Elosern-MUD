# Proposal: the dream panel follows the wish stages

## Batch: dream proposal co-editing

Stage 7 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Browser Surface" except the change line, changed-field marks, editable
requirement rows, the farewell, the Storybook stories and the documents;
"Player-Facing Wording").

- depends-on: dream-wish-text-commands
- conflict: `web/webclient-app/components/DreamPanel.vue`,
  `web/webclient-app/tests/dream.test.js` and
  `web/webclient/tests/test_vue_dream_stage_evidence.py` are touched again by
  `dream-wish-change-report` and `dream-farewell-beat`;
  `web/webclient-app/stories/World/DreamPanel.stories.js` is rewritten by
  `dream-wish-stage-stories`. Apply in batch order.
  `openspec/specs/webclient-dream-stage` requirement "The dream is a
  full-stage AVG scene over its official artwork" was last modified by
  `dream-wish-stage-wire`.
- interim (ended by the next stage): the existing stories still describe the
  old panel states; `dream-wish-stage-stories` rewrites them. The panel still
  receives the schema-3 keys it no longer reads; `dream-wish-change-report`
  removes them. Requirement rows are shown read-only in the edit sheet and
  the keepsake card has no change line until that stage.

## Why

The server has thread choice, the model-edited wish and the two stages, but
the browser panel still treats the player's last words as the direction,
lets the form be edited at any time and confirms without finalizing, so the
server refuses most of what it sends.

## What Changes

- `DreamPanel.vue` is ported from the approved prototype
  (`docs/design/dream-proposal-coediting/DreamWishPrototype.vue`) for:
  - the stage-specific keepsake rows (view or edit, finalize or confirm,
    draft, awaken) and the stage indicator;
  - the read-only whole-wish view while conversing;
  - the finalize confirmation with default focus on staying;
  - the inline thread choice above the reply bar before the first message;
  - the edit sheet available only in the finalized stage, with the thread
    shown as fixed;
  - draft without content while conversing, the form when finalized;
  - the awaken check and every label in the design's wording.
- `tests/dream.test.js` is rewritten for the new contract and the evidence
  bridge follows the surviving and new requirements.
- **BREAKING** (player-visible): the panel no longer confirms before
  finalize and no longer edits the form while conversing.
- **Human-reviewed:** layout, visual polish and Traditional Chinese wording
  are reviewed by a person against the Storybook story `Design/DreamWish` and
  the source design's "Player-Facing Wording" table. Tests establish state,
  dispatch, focus and gating only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-dream-stage`: keepsake rows, sheet, confirmation, awaken check,
  rehydration and requirement display follow the stages; adds the whole-wish
  view, the finalize confirmation and the thread choice.
- `dream-sleep-surface`: the public surface requirement names the
  stage-dependent choices.

## Impact

- Code: `web/webclient-app/components/DreamPanel.vue`,
  `web/webclient-app/tests/dream.test.js`,
  `web/webclient/tests/test_vue_dream_stage_evidence.py`, rebuilt `dist`.
- No wire change, no action change, no story, fixture, document or server
  change.
- Estimate: 6.5 hours (port 2.5 h, Vitest rewrite 3.5 h, evidence bridge
  0.5 h).
