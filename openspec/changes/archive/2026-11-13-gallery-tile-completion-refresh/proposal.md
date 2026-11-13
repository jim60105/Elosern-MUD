# Proposal: refresh gallery wall tiles on art completion

## Batch:

Gallery window programme, stage 1 (design D6: "Each subject tile carries the
artwork descriptor of that subject's resolved default image").

- depends-on: gallery-v4-cutover
- conflict: `web/webclient/presentation/art_push.py` only; the
  `webclient-art-panel` completion requirement was last modified by
  `gallery-v4-cutover` (text only), so land after it.

## Why

Version 4 tiles show each listed subject's resolved default image. The
completion push qualifies a gallery update only when the completed subject is
the selected one, so a tile on the wall keeps a stale image (or a spinner
count) until something else re-renders the panel.

## What Changes

- `art_push._gallery_subject_keys(payload)` returns the rendered `selected`
  key plus every `groups[*].subjects[*].subject_key`, so a completion for any
  listed subject republishes the gallery panel.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-art-panel`: a subject listed on the rendered gallery wall
  qualifies a gallery update.

## Impact

- Code: `web/webclient/presentation/art_push.py`.
- Tests: `web/webclient/presentation/tests/test_art_push.py`.
- Estimate: 3 hours (function change 0.5 h, push tests for the listed and the
  unlisted case 2 h, gates 0.5 h).
