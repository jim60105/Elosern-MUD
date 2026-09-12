# Tasks: gallery-card-update-api

## 1. Card writers

- [x] 1.1 `update_card_face_rect(subject, image_id, face_rect)` in
  `world/art/gallery.py`: `gallery_lock`, tolerant-read lookup,
  `validate_face_rect`, verbatim in-place field write, typed miss error in the
  `remove_card` form, one `gallery_card_updated` event; no file/other-field
  writes.
- [x] 1.2 `update_card_binding(subject, image_id, binding)`: same discipline;
  `validate_binding` plus the kind capability gate (capability-naming typed
  refusal; `None` unbinds); no file writes; one event.

## 2. Subject-key resolver

- [x] 2.1 `resolve_gallery_subject_by_key(subject_key)` in
  `world/art/service.py`: parse serialized kind prefix, registry kinds through
  `monster_subject_for`, character kind through the existing stable-key
  live-entity lookup + `character_subject_for`; typed `ArtSubjectError` on any
  miss; read-only.

## 3. Tests

- [x] 3.1 New `world/art/tests/test_gallery_updates.py` (writers: exact verbatim
  update, order/default stability, malformed-entry refusal, capability gate,
  event emission; resolver: live character, monster tier, dead entity, bad
  prefix) owned by `.github/evennia-shards.json` in this change through the
  shard's existing `world.art` prefix label (the exactly-once shard contract
  forbids an additional explicit label);
  `@covers_requirement` on both new requirements.
