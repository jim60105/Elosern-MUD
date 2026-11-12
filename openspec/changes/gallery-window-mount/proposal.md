# Proposal: mount the gallery window and remove the old panel

## Batch:

Gallery window programme, stage 1, last change (design D7, D8 of
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`). Resolves the
handoff `tmp/gallery-rail-species-budget-handoff.md` end to end.

- depends-on: gallery-window-component
- depends-on: gallery-v4-cutover
- conflict: `web/webclient-app/AppClient.vue`, `stores/elosern/hud.js`,
  `components/nav-tools.js`, `components/OverlayHost.vue`,
  `component-manifest.json`, `web/webclient-app/AGENTS.md`,
  `web/tests/browser/test_browser_gallery_image_contract.py`. The
  `webclient-gallery-ui` requirements modified here were last modified by
  `gallery-v4-cutover`.

## Why

The window is built and the wire speaks version 4; the old overlay panel is
the last thing between the player and the new gallery. This change mounts the
window like the party and shop windows, renames the tool, and deletes
`GalleryPanel.vue` and `GalleryDetailRail.vue` so no second surface remains.

## What Changes

- `gallery` becomes a drawer-keyed window: added to `HUD_DRAWER_NAMES` and
  `FRAMELESS_DRAWER_NAMES`, removed from `HUD_OVERLAY_NAMES`; `AppClient.vue`
  mounts `GalleryWindow` when `store.view.hudDrawer === 'gallery'`; the
  OverlayHost gallery branch, title/subtitle mapping and z-index special case
  are removed.
- The tool entry is renamed 角色肖像圖庫 → 圖庫 and opens the drawer
  (`drawer: "gallery"` in `nav-tools.js`); its test id stays `gallery-opener`.
- Deleted: `GalleryPanel.vue`, `GalleryDetailRail.vue`, their stories
  (`Data/GalleryPanel`, `Data/GalleryDetailRail`) and manifest titles; tests
  that mounted them re-pointed to the window or deleted when duplicated.
- The browser journey's selectors move to the window (rail tab 魔物, wall
  tile by `data-subject-key`).
- `web/webclient-app/AGENTS.md` navigation paragraph names 圖庫 and the
  window.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-window`: the tool opens the window; unavailable panel
  locks it.
- `webclient-desktop-shell`: the tool group carries 圖庫 for the gallery
  window.
- `webclient-gallery-ui`: storyboard moves to the window; official
  affordance names follow the page footer; the detail rail requirement is
  removed.
- `webclient-component-showcase`: the gallery family named in the governed
  route is the window family.

## Impact

- Estimate: 6 hours (mount and store keys 1.5 h, nav rename with tests 0.5 h,
  deletions and test re-pointing 2 h, browser selectors 0.5 h, docs, dist
  rebuild and gates 1.5 h).
- Review: the live window at 1451×790 and 2560×1440 is human-reviewed against
  the approved prototype (design "Review").
