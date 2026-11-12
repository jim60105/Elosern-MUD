# Design: the scene kind becomes gallery-bearing

## Context

- `gallery_kinds._CAPABILITIES_BY_KIND_VALUE["scene"]`: `has_gallery=False`,
  `store_directory=None`, everything else False (plus the three facts from
  `gallery-kind-card-capabilities`, all False).
- `world/art/presenter.py::describe_scene(target)` builds the scene chain:
  room official → generated (`_scene_generated_resource(subject, record)` over
  the classic `ArtAssetRecord` from `_record_for(subject)`) → operator
  archetype official → bundled → terminal; retention from
  `_scene_retention_sources` using `_scene_retained_output_identity(record)`
  (current, else prior output). Generation state comes from the classic record.
- Portrait chain precedent: `_enumerate_portrait` tries the gallery default
  card (through `gallery_api.cards_for`/`record_for` and `_card_artwork`
  helpers) before the classic `done` record; `_generation_facts(subject,
  record, cards, pending)` in `web/webclient/presentation/gallery.py` derives
  pending/failed from `pending_gallery_jobs(subject)` and `last_error_code`.
- The SD worker already renders scene size and the scene prompt for a scene
  subject (`sd_worker.py` branches on `ArtSubjectKind.SCENE`); the alpha
  cutout `applies_to(kind)` excludes scenes; gallery jobs publish to
  `gallery/<directory>/<key>/<image_id><ext>`.
- `commands/art.py` routes `requeue`/`retry` by `gallery_kinds.has_gallery`.

## Goals / Non-Goals

**Goals:** declaration flip; scene chain reads the gallery first; staff
commands follow.

**Non-Goals:** producers (`scene-asset-migration`); migrating classic
records and removing the classic step (`scene-asset-migration`); listing
scenes in the window (`gallery-scene-category`).

## Decisions

### D1. Declaration

Scene record: `has_gallery=True`, `store_directory="scene"`, `max_cards=1`,
`supports_bindings=False`, `requires_age_precondition=False`,
`supports_field_selection=False`, `supports_free_text=False`,
`supports_face_rect=False`, `supports_stage=False`,
`supports_card_delete=True`. Update the module docstring (no kind is
gallery-less now; the gallery-less machinery stays and is tested with a
patched declaration). Replace the literal message
`"scene subjects have no gallery"` in `gallery.record_for` and
`queue.enqueue_gallery_job` with `f"subject kind {kind!r} declares no gallery"`.

### D2. Generated position (gallery first)

In `describe_scene`, for a resolved scene subject:
1. `cards = gallery_api.cards_for(subject)`; `record = gallery_api.record_for(subject)`;
   the default card is the one whose `image_id == record.db.default_image_id`
   (a one-card kind always has it as default after append).
2. A default card with a presentable stored identity → the generated resource
   is that card's original (`descriptors.resource(...)` with the card's
   `stored_identity`, version = card `image_id`, runtime origin, empty
   geometry), source id `descriptors.scene_generated_source_id(subject.full())`.
3. Else fall back to today's classic branch (`_scene_generated_resource`).
4. Generation state: pending when `pending_gallery_jobs(subject)` is non-empty,
   failed when the gallery record carries `last_error_code`, else the classic
   record's state as today.
5. Retention: `_scene_retained_output_identity` returns the default card's
   `stored_identity` when presentable, else today's classic current/prior
   output.

Extract a small helper `_scene_gallery_card(subject) -> dict | None` so
`scene-asset-migration` can delete the classic branch in one place.

### D3. Staff commands

No code change in `commands/art.py`; tests change: `@art requeue scene:<key>`
now calls `requeue_gallery_subject`; `@art retry` re-drives scene gallery
failures through the gallery arm.

## Risks / Trade-offs

- [Seed root folders under `scene/` now synchronize as scene cards] → the seed
  sync's existing registry check must refuse unregistered archetypes; add a
  test with an unregistered folder (it uses `scene_subject_for`, which
  validates the registry).
- [Two generated sources coexist until migration] → the gallery card wins;
  the classic record is only read when no card exists.
