# Proposal: delete the unregistered version-3 gallery code

## Batch:

Gallery window programme, stage 1 (follow-up of `gallery-v4-cutover`).

- depends-on: gallery-v4-cutover
- conflict: `web/webclient/presentation/gallery.py`, `gallery_selection.py`,
  `context.py`, `ingress.py`, `web/static/webclient/js/elosern/protocol/panels/gallery.js`,
  `web/webclient/presentation/tests/test_gallery_panel.py`; later changes
  that edit `gallery.py` or `gallery_selection.py` (`gallery-people-category`)
  land after it.

## Why

To keep the cutover inside one working day, it left the version-3 presenter,
validators and selection store in place, renamed and unregistered. They are
dead code; this change deletes them. No behaviour changes, so no spec delta
(`skip_specs: true`).

## What Changes

- Delete `gallery_presenter_v3`, `validate_gallery_v3`, `gallery_subjects`,
  `_character_subject`, `GALLERY_MAX_SUBJECTS`, `_filters`, the v3
  `PANEL_FIELDS`, and rename the `V4_*` constants to plain names in
  `web/webclient/presentation/gallery.py`.
- Delete `validateGalleryPanelV3` and the v3 `GALLERY_MAX_SUBJECTS` from the
  JS module and its `protocol.js` re-exports.
- Delete `GallerySelection`, `gallery_selection_snapshot` and the v3
  `select_gallery_subject`; rename `select_gallery_subject_v4` to
  `select_gallery_subject`; drop `PresentationContext.gallery_subject` and its
  `ingress.py` fill; `retire_gallery_selection` clears only `ndb.gallery_view`.
- Delete the tests that called only the v3 functions (their requirement
  annotations were already dropped by the cutover).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (dead-code removal).

## Impact

- Estimate: 3 hours (deletions both sides 1 h, test deletion and renames
  1 h, gates 1 h).
