# Proposal: gallery image page and capability-driven footer

## Batch:

Gallery window programme, stage 1 (design D5 of
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`; prototype page
in `docs/design/gallery-window/GalleryWindowPrototype.vue`).

- depends-on: gallery-v4-validators
- depends-on: gallery-kind-card-capabilities
- conflict: `web/webclient-app/components/gallery-window-model.js` (created by
  `gallery-wall-component`; this change appends functions — if it lands first
  it creates the file) and `component-manifest.json` (append-only).

## Why

The window's right page belongs to one selected image: art at its true aspect,
the facts on the quest detail's cell grid, and a footer whose buttons are what
the declared kind capabilities produce. Building it unmounted with a pure
footer descriptor makes the button table testable without a kind comparison.

## What Changes

- New `web/webclient-app/components/GalleryImagePage.vue`: portrait layout
  (art fills the page height at 9:16, facts beside it); ribbon
  `<category>` or `<category>・<group>`; subject name; fact cells 圖片,
  生成時間, 狀態 (multi-card kinds only), 標記 and 綁定條件 (spanning both
  columns); a letter box only for a non-null committed `description`;
  `DetailFooter` with a two-step 刪除 confirmation.
- New pure `galleryFooter(selection, capabilities)` and `galleryRibbon(...)`
  in `gallery-window-model.js`.
- Story `Data/GalleryImagePage` (manifest entry).
- Not mounted.

## Capabilities

### New Capabilities

- `webclient-gallery-image-page`: the image page's facts and its
  capability-driven footer.

### Modified Capabilities

None.

## Impact

- New: component, model functions, `stories/Data/GalleryImagePage.stories.js`,
  `tests/components/gallery_image_page.test.js`, manifest line.
- Estimate: 6 hours (page and fact cells 2 h, footer descriptor 1 h, delete
  arming 0.5 h, Vitest 1.5 h, stories 1 h).
- Review: page tone, spacing and fidelity to the approved fact layout are
  human-reviewed in Storybook (see design "Review").
