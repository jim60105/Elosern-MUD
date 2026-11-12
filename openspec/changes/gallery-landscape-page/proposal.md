# Proposal: the landscape gallery page for scenes

## Batch:

Gallery window programme, stage 3, last change (D5 "Landscape (scenes)" and
Specification 3 "Tiles are 16:9; the page puts the art above the facts").

- depends-on: gallery-image-page
- depends-on: gallery-group-expansion
- conflict: `components/GalleryImagePage.vue`, `components/GalleryWall.vue`,
  `components/gallery-window-model.js`, the gallery stories; `gallery-group-expansion`
  edits `GalleryWall.vue` first.

## Why

Scene images are 16:9 (1536×864). The page must place the art above the name,
description and facts so it reads without scrolling at 1451×790 and
1920×1080, say whether the image in effect is generated or bundled, and offer
the scene footer.

## What Changes

- `GalleryImagePage.vue`: landscape layout for scene subjects; the empty
  selection of a scene shows the committed tile artwork labelled 官方內建圖;
  a stored scene card is labelled 生成圖; note texts `只保留一張；刪除後回到官方內建圖。`
  and `尚未生成專屬圖片。`.
- `gallery-window-model.js`: `pageShape(kind)` and the empty-selection image
  for scenes; the footer already yields 刪除 · 重新生成 from the scene
  capabilities and 生成新圖 for no card.
- `GalleryWall.vue`: landscape tiles already supported; verified by test.
- Built on v4 scene fixtures (added to `stories/gallery-fixtures-v4.js`), so it
  lands before `gallery-scene-category` enables 背景 and the live window
  never shows scene art in the portrait layout.
- Stories: Scenes and SceneBundled (both viewports) on `Data/GalleryImagePage`
  and `Overlays/GalleryWindow`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-image-page`: landscape scene page.
- `webclient-gallery-wall`: scene tiles open no tray.

## Impact

- Estimate: 5 hours (layout 2 h, labels and empty-state image 0.5 h, Vitest
  1.5 h, stories and dist rebuild 1 h).
- Review: the landscape page's readability without scrolling at 1451×790 and
  1920×1080 and its fidelity to the prototype are human-reviewed in Storybook
  (design "Review").
