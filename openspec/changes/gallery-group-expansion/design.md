# Design: expand one people place at a time

## Context

- `gallery_selection.GalleryViewSelection.expanded` and
  `remembered_group(view, category)` exist (`gallery-people-category`); the
  projection expands the remembered people group, else the most recent.
- `select_gallery_category` / `select_gallery_subject` show the store-write
  pattern (session gates, `unknown_*` rejections, info event on change).
- `gallery.category.select` adapter shows the action pattern; the JS
  action-payload validator already accepts `gallery.group.select {group}`
  (`gallery-v4-validators`).
- `GalleryWall.vue` renders collapsed groups as plain headings with counts.

## Goals / Non-Goals

**Goals:** the action, the store write, clickable headings, window wiring.

**Non-Goals:** expanding several groups; paging other categories.

## Decisions

1. `PAGED_CATEGORIES = frozenset({"people"})` in `gallery_selection.py`.
   `select_gallery_group(session, actor, group)`: same session gates as the
   other writers; resolve the current category with the existing fallbacks;
   reject `{"outcome":"rejected","code":"unknown_group","message":"找不到此分組"}`
   unless the category is in `PAGED_CATEGORIES` and `group` is a current group
   key of it; on success replace that category's `expanded` pair, log
   `gallery_group_selected` when changed, return
   `{"outcome":"success","code":"gallery_group_selected","message":"已切換分組"}`.
2. Adapter `_gallery_group_select_adapter` and
   `validate_gallery_group_select_payload` (`_payload(payload, ("group",))`
   plus the group-key grammar `^[a-z0-9_:.-]{1,96}$`), registered beside the
   other selection actions; context `{"group": ..., "action_id": ...}`.
3. Wall: `const collapsible = computed(() => groups.some((g) => !g.expanded))`;
   when true, a labelled heading renders
   `<button type="button" :aria-expanded="String(group.expanded)"
   :aria-busy="pendingGroup === group.key || undefined">` containing the label
   and count; activating a collapsed heading emits `expand-group(key)`;
   activating the expanded one does nothing. New prop
   `pendingGroup: { type: String, default: null }`. Heading buttons sit outside
   the listbox (`role="listbox"` wraps only the tiles), so each is an ordinary
   tab stop with normal button semantics.
4. Window: `pendingGroup` ref set when `dispatch("gallery.group.select",
   {group})` returns an id; cleared when a panel commits with that group
   expanded or the correlated result is non-success.

## Risks / Trade-offs

- [Headings outside the listbox add tab stops in the people category] → one
  per place, acceptable and explicit; tier headings stay plain.
