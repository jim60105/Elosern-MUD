# Design: the gallery window component

## Context

- `GalleryPanel.vue` (after `gallery-v4-cutover`) holds the editor lifecycle:
  `editor`/`entryEditor` refs, `pending {id, editor, official}`, `rejected`,
  `openEditor`, `openOfficialEditor`, `closeEditor` (focus back to opener),
  `send`, `sendOfficial`, `submitOfficialGeometry` (untouched official saves
  never cross the wire), the watch that closes an editor only after its own
  result and declared presentation revision commit, the minute clock, and the
  teleported `GalleryGenerateDrawer`, `GalleryBindingDrawer`,
  `GalleryFaceRectModal`, `GalleryStageTransformModal`.
- `HudDrawer.vue` provides the drawer chrome (title, glyph, close, focus trap,
  Escape, motion); the prototype wraps its body in `HudDrawer`.
- `handbook/LoreCodexTab.vue` grid:
  `var(--quest-drawer-rail-w) minmax(360px*scale, .82fr) minmax(0, 1.18fr)`.
- `IconTabs` supports `orientation="vertical"`, `show-labels`, tabs with
  `disabled` and `reason` (aria-disabled, focusable).
- Category glyph keys from the prototype: mine `emblem_race`, party `party`,
  people `emblem_nation`, monster `emblem_monster`, scene `emblem_region`
  (all present in `dock-icons.js`; verify, and add none if they exist).

## Goals / Non-Goals

**Goals:** an unmounted window with the full interaction contract.

**Non-Goals:** mounting, nav entry, removal of old components
(`gallery-window-mount`); collapsible groups (`gallery-people-client`);
landscape page (`gallery-landscape-page`).

## Decisions

### D1. Contract (verbatim)

```js
// GalleryWindow.vue
props: {
  model:    { type: Object, default: null },   // committed gallery panel
  disabled: { type: Boolean, default: false }, // connected/locked/in-flight gate
  dispatch: { type: Function, default: null }, // (actionId, payload) -> requestId | null
  result:   { type: Object, default: null },   // store.view.lastActionResult
  revision: { type: Number, default: 0 },
}
emits: ["close", "character", "log"]
```

Unavailable model: the body shows the committed reason (or
`圖庫目前無法使用。`) and every control is locked.

### D2. Composition

`HudDrawer :open="true" title="圖庫" icon="gallery" drawer-key="gallery"
body-flush` → `<section class="gallery-window">` grid
`calc(132px * var(--ui-scale)) minmax(calc(360px*var(--ui-scale)), .82fr) minmax(0, 1.18fr)`:
rail (`IconTabs` vertical, `aria-label="圖庫分類"`), `GalleryWall`,
`GalleryImagePage`. Tabs: `{key, label: GALLERY_CATEGORY_LABELS[key], glyph,
count, disabled: !enabled, reason}` from `model.categories`.

### D3. Pending category

`pendingCategory` ref set on press after a successful `dispatch(...)`
returning a request id; `IconTabs :model-value="pendingCategory ?? model.category"`;
cleared when a panel commits with `category === pendingCategory` or when the
correlated result is non-success.

### D4. Selection

`selectedImage` ref (card `image_id`, official `identity`, or `null` for
empty) chosen by the requirement's rule in a pure
`initialImage(cards, officialEntries)` added to `gallery-window-model.js`;
re-run on `model.selected` change and whenever the current id is no longer
listed (closing editors as `GalleryPanel` does today).

### D5. Press mapping

| key | effect |
| --- | --- |
| delete | `send("gallery.card.delete")` |
| default | `send("gallery.default.set")` |
| face / stage / binding | `openEditor(...)` |
| generate / regenerate | `openEditor("generate")` |
| official-select | `sendOfficial("gallery.official.select")` |
| official-clear-selection | `sendOfficial("gallery.official.clear_selection")` |
| official-geometry-clear | `sendOfficial("gallery.official.geometry.clear")` |
| official-face / official-stage | `openOfficialEditor(...)` |

`send`/`sendOfficial`/editor code moves verbatim from `GalleryPanel.vue`,
reading `model.selected` as the subject key and `selectedImage` as the card.

### D6. Focus

Wall `focus-lost` → `railRef.focusSelected()` (IconTabs exposes focus of the
model-value tab; add a small exposed method if missing). Escape: the wall's
tray stops propagation; otherwise `HudDrawer` closes and restores the opener.

### D7. Motion

Tray and page transitions use `--motion-*` tokens; under
`prefers-reduced-motion: reduce` or the root `data-motion="off"` they are
disabled (same mechanism the party window uses; reuse its CSS selector).

## Review

Window proportions, rail width and visual match with the approved prototype
are human-reviewed in Storybook (`Overlays/GalleryWindow`) at both viewports.

## Risks / Trade-offs

- [Two copies of the editor lifecycle until the mount deletes
  `GalleryPanel.vue`] → the copy is mechanical; the mount change deletes the
  original in the next step.
