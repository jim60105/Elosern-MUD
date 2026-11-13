# Proposal: expand one people place at a time

## Batch:

Gallery window programme, stage 2 ("Grouping and paging":
`gallery.group.select {group}` and clickable place headings).

- depends-on: gallery-people-category
- conflict: `web/webclient/actions/gallery_actions.py`, `registry.py`,
  `gallery_selection.py`, `components/GalleryWall.vue`,
  `components/GalleryWindow.vue`. The `webclient-action-dispatch` registry
  requirement is the one `gallery-category-select-action` last modified.

## Why

The people category shows exactly one place expanded. The player needs to
switch which place is expanded; the design makes it one server round trip,
like a category switch, with place headings as buttons and tier headings
staying plain.

## What Changes

- Server: `select_gallery_group(session, actor, group)` in
  `gallery_selection.py` writes the expanded group of the selected category
  (only `people` pages by group); adapter `gallery.group.select` with an
  exact `{group}` payload, three-panel publication, `gallery_action` event.
- Client: `GalleryWall.vue` renders labelled headings as buttons with
  `aria-expanded` when any committed group is collapsed and emits
  `expand-group`; `GalleryWindow.vue` sends `gallery.group.select` and marks
  the heading busy until the commit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-management-actions`: the group selection action.
- `webclient-action-dispatch`: registry enumeration includes
  `gallery.group.select`.
- `webclient-gallery-wall`: collapsible headings.
- `webclient-gallery-window`: group expansion round trip.

## Impact

- Estimate: 7 hours (store function and adapter 1.5 h, server tests 1.5 h,
  wall headings 1.5 h, window wiring 0.5 h, Vitest and stories (People story
  on `Overlays/GalleryWindow` and `Data/GalleryWall`) 1.5 h, dist rebuild and
  gates 0.5 h).
