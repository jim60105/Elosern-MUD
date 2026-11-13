# Proposal: the dream stories and documents follow the wish stages

## Batch: dream proposal co-editing

Stage 8 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Browser Surface" Storybook requirement, "Player-Facing Wording").

- depends-on: dream-wish-stage-panel
- conflict: `web/webclient-app/stories/World/DreamPanel.stories.js` is
  rewritten again by `dream-wish-change-report` and `dream-farewell-beat`;
  `world/narrative/dream_surface.py` (`OPENING`) and
  `world/narrative/tests/test_dream_surface.py` are shared with the server
  stages; `docs/game/command-reference.md` and `docs/game/commands.md` are
  shared with `dream-wish-text-commands`. Apply in batch order.
- declares `skip_specs: true`: this change alters the review surface, one
  already-documented copy sentence and the documents; it changes no specified
  behavior.

## Why

The server, the wire and the panel now follow the stages, but the Storybook
story that is the visual review surface still plays the old flow, and the two
command documents still describe the 念頭 sheet. The `OPENING` narration also
still says the player came to 商談故事方向.

## What Changes

- New story fixtures in `stories/fixtures/dream_wish.js` (threads, opening,
  scripted turns) and a rewritten `stories/World/DreamPanel.stories.js` that
  plays the staged server: stage values `conversing` / `finalized`, the wish
  edits, the thread choice, the finalize confirmation and the edit sheet.
  Every existing export keeps its meaning and six stage states are added.
- The `OPENING` sentence becomes `你可以在這裡向她訴說願望，也可以隨時醒來。`
- `docs/game/command-reference.md` and `docs/game/commands.md` describe the
  staged panel and drop the retired 念頭 wording.
- **Human-reviewed:** the stories and the documents are reviewed by a person
  against Storybook `Design/DreamWish` and the source design's
  "Player-Facing Wording" table.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: no specified behavior changes (`skip_specs: true`).

## Impact

- Code and docs: `web/webclient-app/stories/fixtures/dream_wish.js` (new),
  `web/webclient-app/stories/World/DreamPanel.stories.js`,
  `world/narrative/dream_surface.py` (`OPENING`),
  `docs/game/command-reference.md`, `docs/game/commands.md`, rebuilt `dist`.
- No component, test, wire, action or server-rule change.
- Estimate: 2 hours (stories and fixtures 1 h, copy and documents 0.5 h,
  gates 0.5 h).
