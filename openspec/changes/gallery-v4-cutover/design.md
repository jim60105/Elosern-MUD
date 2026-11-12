# Design: cut the gallery wire over to version 4

## Context

After `gallery-v4-validators`, `gallery-v4-presenter` and
`gallery-category-select-action`:
- `gallery.py` holds v3 (`gallery_presenter`, `validate_gallery`,
  `gallery_subjects`) beside v4 (`build_gallery_v4`, `validate_gallery_v4`,
  `_selected_subject_fields`).
- `gallery_selection.py` holds `GallerySelection` (v3) beside
  `GalleryViewSelection` (v4); `PresentationContext` has both
  `gallery_subject` and `gallery_view`.
- The JS module exports `validateGalleryPanel` (v3) and
  `validateGalleryPanelV4`; `constants.js` `PANEL_ALLOWLIST.gallery === 3`.
- `GalleryPanel.vue` renders `model.subjects` as a `<nav>` and
  `GALLERY_FILTERS` tabs from `gallery-copy.js`.

## Goals / Non-Goals

**Goals:** one commit in which every consumer of the gallery wire speaks v4.

**Non-Goals:** admission (`gallery-mutation-admission`), wall-tile completion
refresh (`gallery-tile-completion-refresh`), the window and the deletion of
`GalleryPanel.vue` (`gallery-window-mount`), Storybook fixtures.

## Decisions

### D1. Rename, do not alias

- Rename the v3 functions to `gallery_presenter_v3` / `validate_gallery_v3`
  (dead, unregistered; deleted by `gallery-v3-removal`); `gallery_presenter`
  = former `build_gallery_v4`; `validate_gallery` = former
  `validate_gallery_v4`; `GALLERY_SCHEMA_VERSION = 4`. The registry
  registration keeps its import of `gallery_presenter`.
- JS: `validateGalleryPanel` = former v4 function; the v3 body becomes
  `validateGalleryPanelV3` (dead); `GALLERY_SCHEMA_VERSION = 4`;
  `PANEL_ALLOWLIST.gallery = 4`; `protocol.js` re-exports follow.
- Assert in a test that `gallery.GALLERY_CATEGORY_KEYS ==
  gallery_categories.CATEGORY_KEYS`.

### D2. Selection

- `gallery.subject.select` calls `select_gallery_subject_v4`; the v3 store
  stays until `gallery-v3-removal`.
- `web/webclient/presentation/art_push.py::_gallery_subject_keys` keeps reading
  `selected` only (wall refresh is `gallery-tile-completion-refresh`).

### D3. Transitional `GalleryPanel.vue` edit (smallest valid surface)

- Replace the subject `<nav>` with:
  - `<div role="group" aria-label="圖庫分類">` of buttons, one per
    `model.categories` entry, label from a client map
    `{mine:"我的角色", party:"隊友", people:"人物", monster:"魔物", scene:"背景"}`
    in `gallery-copy.js` (`GALLERY_CATEGORY_LABELS`), `aria-pressed` on
    `model.category`, `data-testid="gallery-category-<key>"`, disabled ones
    with `aria-disabled="true"` and `aria-describedby` pointing at a visually
    hidden span holding `reason`; pressing an enabled non-current one sends
    `gallery.category.select {category}`.
  - a flat button list of every subject of every expanded group
    (`data-testid="gallery-subject"`, `data-subject-key`), `aria-pressed` on
    `model.selected`, sending `gallery.subject.select`.
- Delete the filter tabs, the `最新優先` note, the grid/list toggle, `filter`
  and `layout` refs and `visibleCards` (cards render in payload order);
  delete `GALLERY_FILTERS` from `gallery-copy.js`.
- `send()` already excludes `gallery.subject.select` from card actions; add
  `gallery.category.select` to that exclusion.
- When `model.selected` is null, render the existing empty paragraph and no
  detail rail actions (`GalleryDetailRail` receives `card=null`).

### D4. Tests

- `test_gallery_panel.py`: tests that exercise the registered presenter
  read `payload["groups"]`; tests that select a companion first select
  `party`; rail/truncation/filter tests keep calling `gallery_presenter_v3`
  directly with their requirement annotations dropped (they are deleted in
  `gallery-v3-removal`). `test_vue_gallery_ui_evidence.py` line ~130 is
  retargeted to the ADDED gallery-ui requirement.
- Client fixtures: switch every importer listed in the proposal to
  `gallery-fixtures-v4.js` and delete `gallery-fixtures.js`.
- `test_art_push.py`: delete the `get_monster_visual_registry` patch (lines
  ~506–516); selection of a companion goes through `party`.
- Vitest `tests/components/gallery.test.js`: delete filter/toggle tests; add
  category-row tests for the three ADDED gallery-ui scenarios.
- Browser `test_browser_gallery_image_contract.py`: fixture records
  `monster:<key>` for the seeded species through
  `world.rules.lore_knowledge.record_species_sighting` before opening; the
  journey clicks `[data-testid="gallery-category-monster"]`, waits for the
  committed `category == "monster"`, clicks the subject button whose
  `data-subject-key` is that species, and asserts the image; replace
  `store_state(...)["filters"]` reads; retarget the decorators of removed
  requirements. Rebuild `dist` (`pnpm run build`) before the local browser run.

## Risks / Trade-offs

- [Seven-plus files change in one commit] → every edit is a rename or a
  deletion of code that the dependencies already replaced; the new logic was
  tested in earlier changes.
- [The transitional panel is plain] → it lives only until
  `gallery-window-mount`; its test ids are the window's.
