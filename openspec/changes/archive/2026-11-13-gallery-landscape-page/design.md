# Design: the landscape gallery page for scenes

## Context

- `GalleryImagePage.vue` (`gallery-image-page`) renders the portrait layout,
  fact cells, letter box for a non-null `panel.description`, and a footer from
  `galleryFooter(selection, capabilities)`.
- `GalleryWall.vue` sizes tiles by `tileShape(kind)` (landscape for `scene`)
  and opens a tray only when `trayOpen(capabilities)`.
- The prototype's landscape grid: areas `"art art" "head cond" "letter cond"`
  (`docs/design/gallery-window/GalleryWindowPrototype.vue`, `.gwin--landscape`).
- `gallery-scene-category` supplies scene subjects whose tile artwork is the
  background in effect and `description` = scene sentence.

## Goals / Non-Goals

**Goals:** landscape page, scene labels, bundled-image empty state.

**Non-Goals:** any server change.

## Decisions

1. `pageShape(kind)` = `tileShape(kind)`; the page root gets
   `gallery-page--landscape` for scene subjects with grid areas
   `"art art" "head facts" "letter facts"`; the art box uses
   `aspect-ratio: 16 / 9` and `max-height` so the whole page fits the window
   body at the reference viewport without scrolling (facts column keeps
   `scrollbar-gutter: stable` as a fallback).
2. Empty selection for a scene (no card rows): the art box renders the
   committed `subject.artwork` through `ArtworkPreview`; 圖片 cell line
   官方內建圖, note 尚未生成專屬圖片。; footer from `galleryFooter` (生成新圖).
3. Stored scene card: 圖片 cell line 生成圖 (client vocabulary for the scene
   kind's single card; the committed row label is kept as the image's
   accessible name), note 只保留一張；刪除後回到官方內建圖。. The 狀態 cell is
   already omitted for one-card kinds.

## Review

Readability without scrolling at 1451×790 and 1920×1080 and resemblance to the
approved prototype's Scenes and SceneBundled stories are human-reviewed in
Storybook.

## Risks / Trade-offs

- [生成圖/官方內建圖 are chosen by kind] → layout and labelling vocabulary,
  not a capability; buttons stay capability-driven.
