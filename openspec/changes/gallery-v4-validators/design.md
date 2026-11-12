# Design: mirrored version-4 gallery panel validators

## Context

- `web/webclient/presentation/gallery.py::validate_gallery` (v3) checks the
  exact panel field set, the 1–24 row rail, cards, official entries, filters,
  warnings, equipment and envelope size, using helpers `_exact`, `_text`,
  `_number`, `_integer`, `_uuid`, `_validate_card_artwork(row, selected)`,
  `_validate_official_entries`, `_validate_equipment`, `check_json_safety`,
  `json_byte_size`, `MAX_CANONICAL_JSON_BYTES`, `MAX_PENDING_GALLERY_JOBS`.
- The JS mirror `validateGalleryPanel` in
  `web/static/webclient/js/elosern/protocol/panels/gallery.js` uses the same
  structure; `validateGalleryActionPayload(actionId, payload)` validates client
  action payloads.
- `test_gallery_panel.py::test_bidirectional_boundary_parity` runs cases
  through `node -e` against the JS module and through Python.
- Any presenter exception becomes the common unavailable form with a
  `log_error` (`web/webclient/presentation/registry.py` render isolation).

## Goals / Non-Goals

**Goals:** exact v4 validators on both sides, additive, with parity tests.

**Non-Goals:** registering v4, changing `PANEL_ALLOWLIST`, producing v4
payloads (`gallery-v4-presenter`), client rendering.

## Decisions

### D1. Verbatim v4 contract

```
{
  schema_version: 4, available: true, kind: "gallery",
  categories: [ {key, count, enabled, reason} ] x5,   // keys exactly
                 // ["mine","party","people","monster","scene"] in order;
                 // count int 0..256; enabled bool;
                 // reason null when enabled, else text 1..64 code points
  category: <key of an enabled category>,
  groups: [ {key, label, seen, total, expanded, count, subjects} ] 0..64,
                 // key: /^[a-z0-9_:.-]{1,96}$/, unique
                 // label: null | text 1..64
                 // seen, total: both null, or ints with 0 <= seen <= total <= 256
                 // expanded: bool; count: int 0..256
                 // expanded true  -> len(subjects) == count
                 // expanded false -> subjects == []
  subjects[i]: {subject_key, kind, display_name, is_current, card_count, artwork},
                 // subject_key: validate_gallery_subject_key; kind == parsed kind
                 // unique across all groups; display_name text 1..64
                 // is_current bool, at most one true in the payload
                 // card_count int 0..MAX_LIST_ITEMS
                 // artwork: null | validate_artwork(...) (shared descriptor)
  selected: null | <subject_key listed in an expanded group>,
  description: null | text 1..512,     // non-null only when selected is set
  cards, official_entries, equipment_summary, binding_warnings, error_state:
                 // v3 rules unchanged, with filters removed: at most one
                 // default row, at most MAX_PENDING_GALLERY_JOBS pending rows,
                 // at most one failed row, failed row present <=> error_state
  capabilities: null | {supports_bindings, supports_field_selection,
                 supports_free_text, supports_personal_official_preferences,
                 supports_face_rect, supports_stage, supports_card_delete,
                 max_cards}             // bools; max_cards null or 1
}
```

- sum(group.count) == categories[category].count.
- total listed subjects <= `GALLERY_MAX_PANEL_SUBJECTS = 256`.
- `selected is None` iff no expanded group lists a subject. Then cards == [],
  official_entries == [], binding_warnings == [], equipment_summary is None,
  capabilities is None, error_state is None, description is None.
- Envelope: `check_json_safety` and `json_byte_size(payload) <= MAX_CANONICAL_JSON_BYTES`.

### D2. `description` (planner decision, flagged)

D5 puts a scene's description on the landscape page, but D6's shape has no
field for it. A nullable top-level `description` (the selected subject's
`SceneArchetype.scene_sentence`, bounded 512) keeps the panel shape fixed
across specifications. It is always null until `gallery-scene-category`.

### D3. Constants and names

Python: `GALLERY_V4_SCHEMA_VERSION = 4`, `GALLERY_CATEGORY_KEYS` (import from
`gallery_categories.CATEGORY_KEYS` would create no cycle: categories does not
import gallery.py — but to keep this change independent of
`gallery-category-sources`, declare the tuple here and let the cutover assert
equality), `GALLERY_MAX_PANEL_SUBJECTS = 256`, `GALLERY_MAX_GROUPS = 64`,
`GALLERY_MAX_REASON = 64`, `GALLERY_MAX_DESCRIPTION = 512`,
`V4_PANEL_FIELDS`, `V4_GROUP_FIELDS`, `V4_SUBJECT_FIELDS`,
`V4_CAPABILITY_FIELDS`. JS mirrors with identical names in camel-free
upper-snake form and exports `validateGalleryPanelV4` plus the constants
through `protocol.js`.

### D4. Action payloads (client side only)

`validateGalleryActionPayload` accepts `gallery.category.select` with exactly
`{category}` (one of the five keys) and `gallery.group.select` with exactly
`{group}` (the group key grammar). Server-side registration happens in
`gallery-v4-cutover` and `gallery-people-category`.

### D5. Parity

Add `GalleryV4ParityTests` in `test_gallery_panel.py` reusing the existing
node harness: one accept fixture (mine category, one subject selected, one
card) plus one reject case per D1 bullet, plus the ceiling pair (256 accepted,
257 rejected). Node gate: a `protocol_gallery_v4.test.js` running the same
fixture shapes.

## Risks / Trade-offs

- [The envelope bound is reached before the subject ceiling when many species
  with descriptors are sighted] → validators fail closed (unavailable form);
  `gallery-v4-presenter` records the shipped payload size as a non-blocking
  note so the risk is visible before cutover.
- [Two v4 rule copies drift] → parity cases are the single acceptance gate.
