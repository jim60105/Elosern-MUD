# Proposal: the gallery window component

## Batch:

Gallery window programme, stage 1 (design D8, D9 and the window row of
"Components" in `docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: gallery-wall-component
- depends-on: gallery-image-page
- conflict: `component-manifest.json` (append-only). New files otherwise.

## Why

The gallery becomes its own book-style window: a vertical category rail, the
wall and the image page, on the shared drawer chrome, with the four existing
editors reopened from the page footer. Composing it unmounted, with the editor
lifecycle moved out of `GalleryPanel.vue`, keeps the mount change small.

## What Changes

- New `web/webclient-app/components/GalleryWindow.vue` on `HudDrawer`
  (drawer key `gallery`, glyph `gallery`, title 圖庫): the codex tab's book
  grid with a wider rail (`IconTabs` vertical with labels), `GalleryWall`,
  `GalleryImagePage`; the generate drawer, binding drawer, face-rect modal and
  stage-transform modal teleported as today.
- Client-local image selection and the press-key → action/editor mapping, the
  single dispatch entry with its gates, the correlated editor closure and
  rejection feedback moved from `GalleryPanel.vue`.
- Rail: the pressed category is marked immediately while its
  `gallery.category.select` is in flight; disabled categories announce their
  committed reason. Focus rescue to the rail's selected tab.
- Story `Overlays/GalleryWindow` with v4 fixtures; not mounted.

## Capabilities

### New Capabilities

- `webclient-gallery-window`: the gallery window's composition, rail,
  dispatch mapping, selection and focus contract.

### Modified Capabilities

None.

## Impact

- New: component, `stories/Overlays/GalleryWindow.stories.js`,
  `tests/components/gallery_window.test.js`, manifest line; `gallery-copy.js`
  gains `GALLERY_CATEGORY_LABELS`/glyph map if `gallery-v4-cutover` has not
  added it.
- Estimate: 6 hours (composition and rail 1.5 h, press mapping and editor
  lifecycle 2 h, focus/escape 0.5 h, Vitest 1.5 h, stories 0.5 h).
- Review: overall window composition and proportions against the prototype
  are human-reviewed in Storybook.
