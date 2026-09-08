## 1. Gallery job record fields

- [ ] 1.1 Add `gallery_image_id` (str, default `""`), `gallery_binding`, `gallery_face_rect`, `gallery_requested_fields` `AttributeProperty` fields to `ArtAssetRecord` in `world/art/store.py`
- [ ] 1.2 Add an `is_gallery_job(record)` predicate (non-empty `gallery_image_id`) used by every branch below

## 2. Queue: per-image enqueue and job-key-resolved settle

- [ ] 2.1 Add `gallery_record_key(subject, image_id) -> "art:<full-subject-key>:gen:<image-id>"` and `enqueue_gallery_job(subject, description, *, image_id, binding, face_rect, requested_fields)` creating one record per call under the shared `queue_lock`
- [ ] 2.2 Set `source_description`, `source_hash`, `prompt_digest`, `aspect_ratio`, `status=pending`, and `enqueued_at` on the new job record exactly as `ensure` does, with no find-or-create and no consolidation
- [ ] 2.3 Replace the subject-derived record lookup in `settle` and `settle_generated` with a lookup by the record's own `db_key`, keeping the classic call sites behaviourally identical
- [ ] 2.4 Add `settle_gallery_generated(...)`: under the lock, verify the claim's generation token and `in_progress` status, atomically replace the temp file onto the gallery identity, append exactly one card through `world/art/gallery.py`, then delete the job record — file write before card append
- [ ] 2.5 Add the gallery failure settle: record the bounded error code on the `GalleryRecord`, append no card, delete the job record
- [ ] 2.6 Exclude gallery job records from `failed_keys()`
- [ ] 2.7 Filter gallery job records out of `commands/art.py::CmdArtStatus` listings and `CmdArtHealth` queue counts, so the staff surfaces keep reporting the classic subject queue only
- [ ] 2.8 Confirm `claim`, `reclaim_expired_leases`, the single `queue_lock`, and the single worker slot are shared unchanged by both job kinds

## 3. Worker: record-derived identity and gallery publication

- [ ] 3.1 Add `output_identity_for(record)` returning `expected_output_identity(subject)` for a subject job and `gallery/<kind-dir>/<subject-key>/<image-id><ext>` for a gallery job; keep `expected_output_identity` unchanged for classic callers
- [ ] 3.2 Branch `_settle_one` to route a gallery job through `settle_gallery_generated`, carrying the `GeneratedImage` prompt pair, seed, and the configured checkpoint (or `None`) onto the card
- [ ] 3.3 Never delete a prior file and never touch a classic record's committed output on a gallery path
- [ ] 3.4 Capture the record key and image id BEFORE the settle so the post-settle event can be logged after the job record is deleted
- [ ] 3.5 Emit `gallery_settle` with `subject`, `image_id`, `kind`, `status`, and the bounded `reason`; keep `sd_job_claim`/`sd_job_settled` behaviour for classic jobs unchanged
- [ ] 3.6 Keep emitting `asset_completed` for a settled gallery job's subject so the existing targeted panel push still fires

## 4. Service seam and startup prune

- [ ] 4.1 Add `request_gallery_image(entity, *, binding=None, face_rect=None)`: subject derivation, canonical-age re-check, binding and face-rect validation through `world/art/gallery.py`, uuid mint, enqueue, `gallery_generate` event
- [ ] 4.2 Raise typed service-boundary errors for every rejection, leaving no record, file, or card behind
- [ ] 4.3 Wrap gameplay-reachable use in the existing failure-isolation pattern so an art failure never rolls back gameplay
- [ ] 4.4 Add `prune_gallery_orphans()`: delete unreferenced files under `gallery/` and unclaimable gallery job records, every path resolved through `world/art/paths.py::resolved_under_store_root`, bounded on failure
- [ ] 4.5 Register the prune as a named startup step in `server/conf/at_server_startstop.py`
- [ ] 4.6 Add no import of `world.art.connectivity` anywhere in this change

## 5. Tests

- [ ] 5.1 `world/art/tests/test_queue.py`: two requests for one subject yield two distinct job keys; `ensure`, requeue, and consolidation never see a gallery job; `failed_keys()` excludes gallery jobs
- [ ] 5.2 `world/art/tests/test_worker.py`: a successful gallery job writes the per-image identity and appends exactly one card carrying the returned prompt pair, seed, and checkpoint
- [ ] 5.3 `world/art/tests/test_worker.py`: a failed gallery job appends no card, records the bounded code on the gallery record, leaves existing cards intact, and deletes no file
- [ ] 5.4 `world/art/tests/test_worker.py`: a stale claim (requeued or lease-reclaimed mid-flight) publishes no card and removes its temp file
- [ ] 5.5 `world/art/tests/test_service.py`: validation rejections produce no record and no prompt; an offline server settles `failed` with the named code and reports it on the gallery record
- [ ] 5.6 `world/art/tests/test_service.py`: the prune deletes an orphan file, spares every referenced file, is idempotent, and survives an unreadable tree
- [ ] 5.7 `world/art/tests/test_art_observability.py`: the `gallery_generate` / `gallery_settle` pair carries subject, image id, kind, status, and reason
- [ ] 5.8 Confirm the classic scene, monster, and character job paths are byte-for-byte unchanged by re-running the existing worker and queue suites
- [ ] 5.9 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art`
- [ ] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands.tests` (staff `@art` surfaces still behave)
- [ ] 6.3 `uv run --locked python -m tools.observability_lint check`
- [ ] 6.4 `uv run --locked python -m tools.spec_traceability check`
- [ ] 6.5 `openspec validate gallery-generation-jobs --strict`
