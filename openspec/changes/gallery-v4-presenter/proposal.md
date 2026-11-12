# Proposal: version-4 gallery projection and stored selection

## Batch:

Gallery window programme, stage 1 (design D6 "Stored selection" and the panel
build of `docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: gallery-category-sources
- depends-on: gallery-v4-validators
- conflict: edits `web/webclient/presentation/gallery.py`,
  `gallery_selection.py`, `context.py`, `ingress.py` additively;
  `gallery-v4-cutover` then removes the v3 paths from the same files.

## Why

The v4 panel must be built from the category sources, carry one category's
groups with each tile's resolved default artwork, and restore a remembered
category and per-category subject with the design's fallbacks. Building it
additively behind the v4 validator keeps master on v3 until the cutover.

## What Changes

- `build_gallery_v4(context)` in `web/webclient/presentation/gallery.py`:
  categories, the selected category's groups (every group expanded,
  `count == len(subjects)`), per-subject `card_count` and resolved default
  `artwork`, the selected subject's cards/official entries/equipment/
  capabilities/warnings/error (shared with v3 through one extracted helper),
  `description: null`, validated by `validate_gallery_v4`. Not registered.
- A v4 session selection store in `gallery_selection.py`: one category and one
  subject per category, bound to the owning character (so possession keeps
  it), retired with the presentation sequence like today; write functions
  `select_gallery_category` and `select_gallery_subject_v4` that validate
  against the category sources. Not called by any action yet.
- `PresentationContext.gallery_view` carries an immutable snapshot of that
  store, copied in `ingress.py` beside the existing `gallery_subject`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-panel`: adds the version-4 projection rules and the
  version-4 stored selection with its fallbacks.

## Impact

- Code: `web/webclient/presentation/gallery.py`, `gallery_selection.py`,
  `context.py`, `ingress.py`.
- Tests: new `web/webclient/presentation/tests/test_gallery_v4_presenter.py`
  (registered in `.github/evennia-shards.json`).
- Estimate: 7 hours (helper extraction 1 h, v4 builder 2 h, store and
  fallbacks 1.5 h, synthetic tests 2 h, gates 0.5 h).
