# Design: mount the gallery window and remove the old panel

## Context

- `stores/elosern/hud.js`: `HUD_DRAWER_NAMES = {"shop","quest","party",
  "npc_persona","letters"}`, `FRAMELESS_DRAWER_NAMES` (same set),
  `HUD_OVERLAY_NAMES = {"map","settings","help","gallery"}`;
  `openHudDrawer(name)` closes the overlay and stores the drawer.
- `components/nav-tools.js` `NAV_TOOLS` entry
  `{ key: "gallery", label: "角色肖像圖庫", testid: "gallery-opener" }`;
  `DesktopNavigation.vue` emits `drawer` for entries with `drawer`, else
  `overlay`; the gallery tool renders only while the panel is available.
- `AppClient.vue` mounts `PartyWindow`/`ShopWindow` by `hudDrawer` and
  excludes them from the generic `HudDrawer`; `GalleryPanel` is rendered in
  `OverlayHost` (`openName === 'gallery'`); `FullLogOverlay` gets
  `zIndex: 3100` while `hudOverlay === 'gallery'` so the log opens above
  the gallery's nested editors.
- `components/OverlayHost.vue` maps `gallery` to a glyph and subtitle
  (`記錄不同的你，也是旅途的一部分。`) and a body style override.

## Goals / Non-Goals

**Goals:** mounted window, renamed tool, no old surface.

**Non-Goals:** any behaviour of the window itself (built in
`gallery-window-component`); people and scene categories.

## Decisions

1. `hud.js`: add `"gallery"` to `HUD_DRAWER_NAMES` and
   `FRAMELESS_DRAWER_NAMES`; remove it from `HUD_OVERLAY_NAMES`; update the
   comment at line ~14 and `stores/elosern/view.js` comment (~334).
2. `nav-tools.js`: `{ key: "gallery", label: "圖庫", testid: "gallery-opener",
   drawer: "gallery" }`; update the header comment.
3. `AppClient.vue`: mount
   `<GalleryWindow v-if="store.view.hudDrawer === 'gallery'" :model="panel('gallery')"
   :disabled="!store.view.connected || store.view.mutationsLocked || store.view.dispatch.inFlight !== null"
   :dispatch="dispatchIntent" :result="store.view.lastActionResult"
   :revision="store.view.revision" @character="store.openHudDrawer('status')"
   @log="openFullLog" @close="onHudDrawerClose" />` next to `ShopWindow`;
   add `'gallery'` to the generic `HudDrawer` exclusion; delete the
   `GalleryPanel` import and branch; change the `FullLogOverlay` z-index
   condition to `store.view.hudDrawer === 'gallery'`.
4. `OverlayHost.vue`: delete the `gallery` glyph/subtitle mapping and the
   `[data-elosern-overlay="gallery"]` style; grep `styles/app-shell.css` for
   `.elosern-root .gallery-panel` duplicates and delete them (AGENTS styling
   pitfall).
5. Delete `components/GalleryPanel.vue`, `components/GalleryDetailRail.vue`,
   `stories/Data/GalleryPanel.stories.js`,
   `stories/Data/GalleryDetailRail.stories.js`; remove their manifest titles;
   re-point `tests/components/gallery.test.js` cases that cover still-present
   behaviour (editors' correlated closure, official geometry untouched-save)
   to mount `GalleryWindow`, delete the rest. `lib/artwork.js` and
   `protocol/envelope.js` comments that name `GalleryPanel` are updated.
6. Tests naming the label: `tests/desktop_navigation.test.js`,
   `tests/reference_surface_frame.test.js`,
   `stories/Core/DrawerHeader.stories.js` switch to 圖庫 where they assert the
   gallery tool.
7. Browser: `test_browser_gallery_image_contract.py` opens with
   `gallery-opener`, presses the rail tab whose accessible name starts with
   魔物 (`[role="tab"]`), waits for the committed `category == "monster"`,
   clicks `[data-subject-key="<species subject key>"]`, asserts the image;
   rebuild `dist` first.
8. `web/webclient-app/AGENTS.md`: the navigation paragraph lists 圖庫 (the
   gallery window) instead of 角色肖像圖庫; add a short "Gallery window"
   paragraph naming `GalleryWindow`, `GalleryWall`, `GalleryImagePage`,
   `gallery-window-model.js` and the `gallery` drawer key.

## Review

The mounted window is human-reviewed in the live client at 1451×790 and
2560×1440 against the approved prototype (layout, rail width, tile and tray
appearance, page legibility).

## Risks / Trade-offs

- [`webclient-contextual-hud` still lists 角色肖像圖庫 in a scenario about
  what the combat bar must not contain] → the statement stays true (no such
  control exists anywhere); left unchanged.
