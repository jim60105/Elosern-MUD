# Design: migrate classic scene assets to scene gallery cards

## Context

- Classic records: `ArtAssetRecord` with `db.kind == "scene"`,
  `db.subject_key`, `db.status` (`missing|pending|in_progress|done|failed`),
  `db.output_identity` (e.g. `scene/<key>.webp`), `db.prior_output_identity`,
  `db.source_description`; `queue.is_gallery_job(record)` is False for them.
- `presenter._validated_output_identity(subject, identity)` decides
  presentability (confined, closed extension, file exists).
- `gallery.append_card(subject, **card_fields)` validates the card contract
  (`image_id`, `stored_identity` under `gallery/scene/<key>/`, `prompt`
  (`None` or `{positive, negative}`), `seed`, `checkpoint`,
  `requested_fields`, `face_rect`, `image_size` (from verified bytes),
  `stage`, `binding`, `source` in `{"generated","seed"}`, `created_at`) and
  for a one-card kind installs the card as sole default.
- The worker's publication writes files through
  `world/art/store.resolved_under_store_root` and the publication gate
  (`world/art/publication.py`); the gallery seed copies files the same way
  (`world/art/gallery_seed.py`, never-overwrite, image-size read from bytes).
- Startup order: `art_gallery_prune`, `art_seed_sync`, `art_official_catalog`,
  `art_sync_all` (`server/conf/at_server_startstop.py` step catalog).

## Goals / Non-Goals

**Goals:** convert settled classic scene outputs; delete every classic scene
record and file; idempotent.

**Non-Goals:** touching monster or character classic records; removing the
scene chain's classic fallback (`scene-classic-fallback-removal`).

## Decisions

### D1. Per-record procedure

For each classic scene record (sorted by `db_key` for determinism):
1. `pending`/`in_progress` → skip.
2. Resolve `subject = scene_subject_for(subject_key)`; an unregistered
   archetype → delete record and its confined output files (step 5).
3. `done` with presentable `output_identity` and `gallery_api.cards_for(subject)`
   empty → copy the bytes to `gallery/scene/<key>/<new uuid4><same ext>` with
   the seed sync's never-overwrite copy helper (reuse it; do not hand-roll),
   read the image size from the copied bytes the way the seed sync does, then
   `append_card(subject, image_id=<uuid>, stored_identity=<new identity>,
   prompt=None, seed=None, checkpoint=None, requested_fields=[],
   face_rect=None, image_size=<size>, stage=None, binding=None,
   source="generated", created_at=<record.db.completed_at or file mtime>)`
   (`None` geometry takes the defaults at append).
4. Any other case (card already present, `failed`, `missing`, `done` without a
   presentable output) → no card.
5. Delete the record (`record.delete()`), then unlink each existing confined
   file among `output_identity` and `prior_output_identity` that no gallery
   card references.

Exceptions per record → `log_warn("art_scene_migration_failed", context=
{"record": db_key}, exc=...)` and continue. Return counts
`{"converted", "dropped", "skipped"}`; emit `art_scene_migration` info.

### D2. Ordering and orphans

Running before `art_gallery_prune` means a copy whose `append_card` failed is
an unreferenced `gallery/` file that the prune deletes in the same startup;
a record whose deletion failed is retried next startup; the classic file is
unlinked only after its record is deleted. The step name
`art_scene_migration` is inserted before `art_gallery_prune` in the catalog
tuple and wired with `_startup_step(..., lambda: _late("world.art.service",
"migrate_classic_scene_records"))`.

### D3. Producers switch in the same change

Converting classic records while the producers still write them would delete
and requeue every scene at each startup. So this change also:
1. `ensure_scene_asset`: replace the classic `queue_ensure` lines with the
   gallery ensure below; keep the archetype guard and the bounded warning.
2. `_sync_registry_subjects`: the scene loop uses the same gallery ensure;
   update the docstring.
3. Gallery ensure for scenes: `record = gallery_api.record_for(subject)`; skip
   when `record is not None and not gallery_api.cards_for(subject) and
   record.db.last_error_code is None` (the empty record a deletion leaves:
   `remove_card` keeps the record); otherwise call
   `_ensure_gallery_subject(subject)`. A failed first generation leaves a
   record with an error (`record_error` creates it), so it is retried.
4. Verified: `_official_default_satisfies` answers False for a bare
   `ArtSubject`, so scenes with an operator archetype image still
   autogenerate as the classic path did.
5. The deletion rule is a planner decision: Specification 3 says deleting
   returns the archetype to its bundled image, which the shared guard alone
   would undo on the next entry.

## Risks / Trade-offs

- [The classic `created_at` field name differs] → read the record's actual
  completion timestamp attribute (inspect `ArtAssetRecord` in
  `world/art/queue.py`); fall back to the file's mtime.
- [Large scene files copied at startup] → once per archetype, then never.
