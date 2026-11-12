# Proposal: cut the gallery wire over to version 4

## Batch:

Gallery window programme, stage 1. This is the single wire cutover: server
presenter, both validators, `PANEL_ALLOWLIST` and the mounted client surface
switch together in one commit.

- depends-on: gallery-v4-presenter
- depends-on: gallery-category-select-action
- conflict: `web/webclient/presentation/gallery.py`, `gallery_selection.py`,
  `context.py`, `ingress.py`, `web/static/webclient/js/elosern/protocol/panels/gallery.js`,
  `protocol/constants.js`, `web/webclient-app/components/GalleryPanel.vue`,
  `web/webclient-app/tests/components/gallery.test.js`,
  `web/webclient/presentation/tests/test_gallery_panel.py`, `test_art_push.py`,
  `web/tests/browser/test_browser_gallery_image_contract.py`. Must land after
  the two dependencies and before `gallery-mutation-admission`,
  `gallery-tile-completion-refresh` and `gallery-window-mount`.

## Why

The 24-row rail is the defect (handoff `tmp/gallery-rail-species-budget-handoff.md`):
no companion or NPC gallery can be opened and most species are unreachable.
Everything needed for version 4 now exists additively; this change switches
the registered panel to it and removes the version-3 rail, filters and their
validators, while keeping the existing panel component usable with the
smallest possible edit until the window replaces it.

## What Changes

- The registered `gallery` presenter becomes the v4 builder;
  `GALLERY_SCHEMA_VERSION = 4`; `validate_gallery` becomes the v4 validator;
  the JS `validateGalleryPanel` becomes the v4 mirror; `PANEL_ALLOWLIST`
  holds `gallery: 4`.
- `gallery.subject.select` writes the v4 store (membership of the selected
  category).
- The v3 presenter, validators and store are left in place but unregistered
  and unreachable; `gallery-v3-removal` deletes them right after this change so
  this one stays within a working day. Tests annotated with the removed v3
  requirements lose those annotations here.
- The registry patch in `test_art_push.py` is removed.
- Every client test and story that feeds a gallery panel switches from the v3
  `stories/gallery-fixtures.js` to `stories/gallery-fixtures-v4.js`
  (`app_client_gallery`, `app_client_drawers`, `app_client_party_window`,
  `app_client_presence_rail`, `drawer_content_polish`,
  `gallery_original_editors`, `stage_transform`, `reference_surface_frame`,
  `tests/components/gallery.test.js`, `stories/Data/GalleryPanel.stories.js`,
  `stories/Data/GalleryDetailRail.stories.js` and the gallery entries of
  `stories/fixtures/*_panels.js`); the v3 fixture file is deleted.
- `web/webclient/tests/test_vue_gallery_ui_evidence.py` retargets its
  annotation of the removed "renders only committed panel facts" requirement.
- **Transitional client edit** in `GalleryPanel.vue`: the subject `<nav>` is
  replaced by a category button row (`data-testid="gallery-category-<key>"`,
  disabled ones `aria-disabled` with their reason) and a flat list of the
  selected category's subjects (`data-testid="gallery-subject"` with
  `data-subject-key`); the filter tabs and the grid/list toggle are removed.
  `GalleryPanel.vue` itself is deleted by `gallery-window-mount`.
- The browser journey opens the gallery, selects the 魔物 category, selects
  a sighted species and asserts its image; its fixture records the sighting.
  The same test ids are kept by the window so the journey survives the mount.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-panel`: schema 4 registered; rail and filter
  requirements removed; selection rules move to categories.
- `webclient-gallery-management-actions`: subject selection validates
  category membership.
- `webclient-gallery-ui`: the surface renders categories and subjects, no
  filter tabs.
- `webclient-art-panel`: completion-push scenarios stop mentioning filter
  counts (text only; qualification is unchanged here).

## Impact

- Code and tests listed above.
- Estimate: 8 hours (registration swap both sides 0.5 h, subject select on
  the v4 store 0.5 h, Python presenter/push test migration 2 h, transitional
  panel edit 1 h, client fixture switch across suites and stories 2 h, browser
  journey 1 h, evidence retarget, dist rebuild and gates 1 h). Deleting the
  dead v3 code moved to `gallery-v3-removal` to stay within the cap.
