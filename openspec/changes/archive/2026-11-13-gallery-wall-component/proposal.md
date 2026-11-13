# Proposal: gallery wall with inline image tray

## Batch:

Gallery window programme, stage 1 (design D4 and the wall half of D9 of
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`; prototype
`docs/design/gallery-window/GalleryWall.vue`).

- depends-on: gallery-v4-validators
- conflict: new files only, plus `web/webclient-app/component-manifest.json`
  (also edited by `gallery-image-page`, `gallery-window-component`,
  `gallery-window-mount`: append-only lines, rebase trivially). May run in
  parallel with the server changes after its dependency.

## Why

The window's centre is a wall of aspect-true subject tiles with an inline tray
of the selected subject's images. It cannot reuse `TileWall` as is: tiles are
not square and the tray interrupts the grid. Building it as an unmounted
component with stories and tests keeps it reviewable before the window exists.

## What Changes

- New `web/webclient-app/components/GalleryWall.vue`: grouped tiles from the
  committed v4 `groups`, portrait 9:16 tiles (16:9 for scene subjects), name
  caption, image count when above one, 操作中 ribbon on the live character;
  a tray under the selected subject's row when its kind allows more than one
  card, listing its cards, a 生成新圖 tile and a 官方圖片（唯讀） run; state
  carried by shape and text; one listbox for the wall and one for the tray
  with the D9 keyboard contract.
- New pure helpers in `web/webclient-app/components/gallery-window-model.js`:
  `wallTiles(groups)`, `trayItems(cards, officialEntries)`, `trayOpen(capabilities)`,
  `tileShape(kind)`, `trayInsertIndex(ownerIndex, columns, groupLength)`.
- Story `Data/GalleryWall` (manifest entry) with v4 fixtures for mine, party,
  monster, empty, pending/failed/official states.
- Not mounted anywhere.

## Capabilities

### New Capabilities

- `webclient-gallery-wall`: the gallery wall's tiles, tray, states and
  keyboard contract.

### Modified Capabilities

None.

## Impact

- New: the component, the model module, `stories/Data/GalleryWall.stories.js`,
  fixtures in `stories/gallery-fixtures-v4.js` (v4 shape, validated by the v4
  validator that `gallery-v4-validators` exports),
  `tests/components/gallery_wall.test.js`; manifest line.
- Estimate: 7 hours (component and tray placement 3 h, keyboard and focus 1.5 h,
  model helpers 0.5 h, Vitest 1.5 h, stories and manifest 0.5 h).
- Review: tile and tray visual fidelity to the prototype is human-reviewed in
  Storybook at 1451×790 and 1920×1080 (see design "Review").
