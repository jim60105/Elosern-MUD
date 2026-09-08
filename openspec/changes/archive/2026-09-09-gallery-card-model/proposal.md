## Why

The art pipeline stores exactly one image per subject: one `ArtAssetRecord`, one
fixed output identity (`portrait/character/<key>.<ext>`), one description. A
player who dislikes the generated portrait has no second image to fall back on,
no way to keep several looks for one character, and no way to tell the client
where the face sits inside a 3:4 portrait so a 1:1 avatar frame can crop to it.
Equipment — which visibly changes how a character looks — is never consulted by
any art path.

The approved design (`docs/superpowers/specs/2026-09-08-character-gallery-art-design.md`)
answers all of that with a per-subject *gallery* of image cards. This change
lands the data layer alone: the record, the card contract, and the validated
write API every later change calls. It ships no generation, no resolution, and
no presentation, so it can be reviewed as a pure model.

## What Changes

- New `world/art/gallery.py`: a `GalleryRecord` Evennia `DefaultScript` keyed
  `gallery:<full-subject-key>`, holding an append-ordered list of image-card
  dicts, a `default_image_id`, and the last generation error for the subject.
- New card contract (D3/D4/D5/D9 of the design): `image_id`, `stored_identity`,
  `prompt`, `seed`, `checkpoint`, `requested_fields`, `face_rect`, `binding`,
  `source`, `created_at`, with validation at every write boundary.
- New `DEFAULT_FACE_RECT` constant and normalized `{x, y, w, h}` validation
  (`x+w ≤ 1`, `y+h ≤ 1`, `w > 0`, `h > 0`).
- New binding contract: a non-empty mask over `weapon_main`, `weapon_off`,
  `armor`, `accessories` plus a normalized equipment snapshot over exactly the
  masked slots. An all-empty snapshot ("wearing nothing") is a legal binding;
  `binding = None` (unbound) is legal too.
- New equipment-snapshot reader that reads `entity.db.equipment` directly and
  fails closed to the empty snapshot, so no gallery path ever materializes an
  `EquipmentHandler` or writes equipment state.
- Monster subjects are capped at one card: appending replaces.
- New `world/art/paths.py`: the single store-root confinement helper
  (`resolved_under_store_root`), used by card deletion here and adopted by the
  queue, worker, presenter, and media route in later changes.
- Records are created lazily. A subject with no record is a legal, silent state.

No backward compatibility or data migration: the project has no released users
and no gallery data exists.

## Capabilities

### New Capabilities

- `art-gallery-model`: the per-subject gallery record, the image-card contract,
  face-rect and binding validation, the monster one-card cap, the single-writer
  boundary, and tolerant reads of malformed stored cards.

### Modified Capabilities

None. `ArtAssetRecord`, the queue, the worker, the presenter, and every existing
art requirement are untouched by this change.

## Impact

- `world/art/gallery.py` — new module: record typeclass, card validation,
  `append_card` / `remove_card` / `set_default` / `cards_for` / `record_for`.
- `world/art/paths.py` — new module: store-root confinement helper.
- `world/art/tests/test_gallery.py` — new pure `unittest`/Evennia coverage
  (already inside the `world.art` shard label).
- Reads `world/skills/equipment.py` slot vocabulary and `entity.db.equipment`
  storage; writes neither.
- Unaffected: `world/art/queue.py`, `worker.py`, `service.py`, `presenter.py`,
  `sd_worker.py`, `web/art_media.py`, every webclient payload, and every
  player-facing command.
