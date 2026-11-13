# Proposal: the dream panel shows what changed and edits requirement rows

## Batch: dream proposal co-editing

Stage 9 of 10 of `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`
("Keepsake card" change line, "Read-only view" changed-field marks,
"Finalize" requirement rows).

- depends-on: dream-wish-stage-stories
- conflict: `web/webclient-app/components/DreamPanel.vue`,
  `tests/dream.test.js`, `stories/fixtures/dream_wish.js` and
  `stories/World/DreamPanel.stories.js`,
  `test_vue_dream_stage_evidence.py` (shared with `dream-wish-stage-panel`
  and `dream-farewell-beat`); `world/narrative/dream_surface.py`,
  `web/webclient/presentation/dream.py`, `protocol/panels/dream.js`,
  `protocol/constants.js`, `protocol_dream.test.js` (shared with
  `dream-wish-stage-wire`); apply in batch order.

## Why

The goddess now edits the wish while the player reads her answer, and a
removal leaves nothing on screen to notice. The panel has to say what she
changed each turn, and once the player takes the form over they need to edit
its requirement rows, which the panel still shows read-only. The wire also
still carries four schema-3 keys nothing reads.

## What Changes

- The keepsake card shows a change line from the server's change report:
  which fields changed, with counts of added and removed items, or that
  nothing changed. It updates only after the goddess's line has finished
  revealing, stays until the next exchange settles, and is announced through
  the live region.
- The whole-wish view marks changed fields, marks added items and lists
  removed items by name under their field.
- In the finalized edit sheet requirement rows can be added (kind from the
  closed set), edited and removed, with a count against the limit of eight
  and an error on a row whose text is blank.
- Panel schema 5 removes `direction_parts`, `draft_preferences`,
  `requirements` and `requirement_version`.
- **BREAKING** (wire): schema 4 payloads are rejected.
- **Human-reviewed:** the visual treatment of the change line and marks and
  their wording are reviewed by a person against Storybook `Design/DreamWish`
  (stories `ChangedWish`, `NothingChanged`, `WholeWish`, `OwnHand`) and the
  source design's "Player-Facing Wording" table.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-dream-stage`: adds the change line, the changed-field marks and
  editable requirement rows.

## Impact

- Code: `web/webclient-app/components/DreamPanel.vue`,
  `web/webclient-app/tests/dream.test.js`,
  `stories/World/DreamPanel.stories.js`,
  `web/webclient/tests/test_vue_dream_stage_evidence.py`,
  `world/narrative/dream_surface.py` (`dream_state`),
  `web/webclient/presentation/dream.py`,
  `web/static/webclient/js/elosern/protocol/panels/dream.js`,
  `protocol/constants.js`, `web/static/webclient/js/tests/protocol_dream.test.js`,
  `world/narrative/tests/test_dream_surface.py`,
  `web/webclient/presentation/tests/test_dream_artwork.py`, rebuilt `dist`.
- Estimate: 8 hours (change line and marks 2 h, requirement rows 1.5 h, wire
  cleanup 1 h, tests 2.5 h, stories and gates 1 h).
