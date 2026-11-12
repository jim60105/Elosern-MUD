# Design: version-4 gallery projection and stored selection

## Context

- `gallery_presenter(context)` (v3, `web/webclient/presentation/gallery.py`
  ~line 796) checks exploration mode, picks the selected rail entry, then
  builds `cards`, `official_entries`, `equipment_summary`, `capabilities`,
  `binding_warnings`, `error_state` from `pending_gallery_jobs`,
  `gallery_api.record_for/cards_for`, `_generation_facts`, `_alpha_terminal`,
  `_card_artwork`, `_synthetic`, `_official_entries`.
- `gallery_selection.py` stores `GallerySelection(owner_actor_id, epoch,
  subject_key)` on `session.ndb.gallery_selection`, retired on unpuppet
  (signal) and sequence reset; `gallery_selection_snapshot` copies it into
  `PresentationContext.gallery_subject` in `ingress.py`.
- `world/art/presenter.describe_portrait(subject, entity=None)` returns the
  canonical descriptor of one subject's ordered attempts (gallery default card
  first); `web/webclient/presentation/artwork.validate_artwork` validates it.
- `gallery_categories` (from `gallery-category-sources`) supplies
  `gallery_owner`, `gallery_categories`, `category_groups`.

## Goals / Non-Goals

**Goals:** a v4 builder and store, testable in isolation; v3 untouched in
behaviour.

**Non-Goals:** registering v4, actions, push qualification, admission,
client.

## Decisions

### D1. Shared selected-subject helper

Extract the body of `gallery_presenter` from `capability = ...` to the
`binding_warnings`/`error_state` construction into
`_selected_subject_fields(subject, entity) -> dict` returning the keys
`cards`, `official_entries`, `equipment_summary`, `capabilities`,
`binding_warnings`, `error_state`, plus `filters` (v3 only consumes it). v3
calls it and keeps its exact output (its tests must stay green unchanged).
`capabilities` gains no new keys in v3; the v4 builder adds
`supports_face_rect`, `supports_stage`, `supports_card_delete` from
`capabilities_for(subject.kind.value)`.

### D2. Store (verbatim)

```python
@dataclass(frozen=True)
class GalleryViewSelection:
    owner_id: int                 # gallery_owner(actor).pk
    epoch: str                    # coordinator epoch
    category: str
    subjects: tuple[tuple[str, str], ...]   # (category, subject_key) pairs

def gallery_view_snapshot(session, actor) -> GalleryViewSelection | None
def select_gallery_category(session, actor, category) -> dict
def select_gallery_subject_v4(session, actor, subject_key) -> dict
```

- Stored on `session.ndb.gallery_view`; `retire_gallery_selection` also clears
  it (same unpuppet signal and sequence reset).
- Snapshot is valid only when `session.puppet is actor`, `owner_id ==
  gallery_owner(actor).pk` and `epoch == coordinator.epoch`.
- `select_gallery_category`: rejects `{"outcome":"rejected","code":
  "unknown_category","message":"找不到此圖庫分類"}` unless the key is an enabled
  category; on success keeps the subject map and sets `category`; logs
  `gallery_category_selected` (info) only when it changed; returns
  `{"outcome":"success","code":"gallery_category_selected","message":"已切換圖庫分類"}`.
- `select_gallery_subject_v4`: rejects `unknown_subject` (`找不到此圖庫對象`)
  unless the key is listed in the currently resolved category's expanded
  groups; on success records `(category, subject_key)` replacing that
  category's entry; returns `gallery_selected` / `已切換圖庫對象`.
- Both apply the same session gates as today's `select_gallery_subject`
  (webclient session, puppet is actor, coordinator present).

### D3. Resolution with fallbacks

`_resolve_view(actor, view) -> (category, subject_ref | None, groups)`:
1. category = `view.category` if view and that category is enabled, else
   `"mine"`.
2. groups = `category_groups(actor, category)`.
3. remembered = subject for `category` in `view.subjects`; if it is listed,
   select it; else the `is_current` subject; else the first listed; else None.

### D4. Builder

`build_gallery_v4(context)`:
- Exploration mode only (as v3), else `PanelUnavailableError`.
- `GalleryCategoryError` → `PanelUnavailableError`.
- `context.gallery_view` (new `PresentationContext` field, default `None`,
  filled in `ingress.py` via `gallery_view_snapshot`).
- Subject row: `subject_key`, `kind`, `display_name`, `is_current`,
  `card_count = len(gallery_api.cards_for(subject))`, `artwork =
  validate_artwork(describe_portrait(subject, ref.entity))`; any exception
  there sets `artwork: None` and logs `gallery_tile_artwork_failed` (warn) —
  one bad tile never degrades the panel.
- Group row: `key`, `label`, `seen`, `total`, `expanded: True`, `count =
  len(subjects)`.
- Selected-subject fields from D1, or the empty set of D1 of
  `gallery-v4-validators` when nothing is selected; `description: None`.
- Return `validate_gallery_v4(payload)`.

### D5. Size note (non-blocking)

After tests pass, build the projection for the `monster` category with every
shipped species sighted in a scratch script and record its JSON byte size in
the apply report. This is information for the cutover, not a gate and not a
test.

## Risks / Trade-offs

- [Helper extraction changes v3 output] → v3 tests in `test_gallery_panel.py`
  run unchanged as the guard.
- [`describe_portrait` per tile is the costliest read] → bounded by the
  category size; no wall-clock assertion is added.
