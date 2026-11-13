# Proposal: the dream panel follows the wish stages

## Batch: dream proposal co-editing

Stage 6 of 8 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Browser Surface" except the change line, changed-field marks, editable
requirement rows and the farewell; "Player-Facing Wording").

- depends-on: dream-wish-text-commands
- conflict: `web/webclient-app/components/DreamPanel.vue`,
  `web/webclient-app/tests/dream.test.js`,
  `web/webclient-app/stories/World/DreamPanel.stories.js` and
  `web/webclient/tests/test_vue_dream_stage_evidence.py` are touched again by
  `dream-wish-change-report` and `dream-farewell-beat`; apply in batch order.
  `openspec/specs/webclient-dream-stage` is rewritten here: requirement "The
  dream is a full-stage AVG scene over its official artwork" was last
  modified by `dream-wish-stages`.
- interim (ended by the next stage): the panel still receives the schema-3
  keys it no longer reads; `dream-wish-change-report` removes them. Requirement
  rows are shown read-only in the edit sheet and the keepsake card has no
  change line until that stage.

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
- The opening narration's last sentence and the web paragraph of the command
  reference follow the new wording.
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
  `web/webclient-app/stories/World/DreamPanel.stories.js`,
  `web/webclient-app/stories/fixtures/dream_wish.js` (new),
  `web/webclient/tests/test_vue_dream_stage_evidence.py`,
  `world/narrative/dream_surface.py` (`OPENING`, one sentence),
  `docs/game/command-reference.md` and `docs/game/commands.md` (web
  paragraphs), rebuilt `dist`.
- No wire change, no action change, no migration.
- Estimate: 8 hours (port 2.5 h, Vitest rewrite 3.5 h, stories 1 h, evidence
  bridge, documents and gates 1 h).
