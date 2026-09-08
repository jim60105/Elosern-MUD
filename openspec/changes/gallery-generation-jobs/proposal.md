## Why

`gallery-card-model` gives every art subject a card list, but nothing can put an
image in it. The existing pipeline can produce exactly one image per subject:
`ensure` collapses every request for a subject into one record, and the worker
writes to one fixed identity, `portrait/character/<key>.<ext>`. A player asking
for "another take" has nowhere for that take to go.

This change adds the generation half of the gallery: a per-image job that shares
the existing queue, lock, worker slot, sd-webui client, and path confinement, and
settles by appending a card instead of overwriting a record's single output.

## What Changes

- New service seam `world/art/service.py::request_gallery_image(entity, *, binding=None, face_rect=None)`:
  validates the subject, binding, and face rect, mints an `image_id`, and enqueues
  one job. It is the only gameplay-reachable entry point for gallery generation.
- New queue helper `enqueue_gallery_job(...)` creating one record per requested
  image under `art:<full-subject-key>:gen:<image-id>`. Two requests for one subject
  produce two independent jobs; the subject-keyed `ensure` path is untouched.
- `ArtAssetRecord` gains the gallery job fields: `gallery_image_id`,
  `gallery_binding`, `gallery_face_rect`, `gallery_requested_fields`.
- `world/art/queue.py` settle paths resolve the record by its own job key instead
  of re-deriving it from the subject, so a gallery job and its subject's classic
  record can never settle onto each other.
- `world/art/worker.py` derives the expected identity from the record: the classic
  fixed identity for a subject job, `gallery/<kind>/<subject-key>/<image-id><ext>`
  for a gallery job. A successful gallery settle appends exactly one card through
  the `world/art/gallery.py` API — file write first, card append second — and
  deletes the spent job record. A failed one appends nothing and records the
  bounded error code on the `GalleryRecord`.
- New startup prune reclaiming orphan gallery files (written by a job that was
  interrupted before its card append) and stale gallery job records.
- New boundary events `gallery_generate` and `gallery_settle` through the
  `world.observability` facade.
- `failed_keys()` and the `@art retry` set exclude gallery job records: a gallery
  retry is a new request, not a re-enqueue.

**Deviation from the design document, deliberate.** Design §4.4 sketches
`request_gallery_image` probing sd-webui availability before queueing. That would
require a `world/art/` module other than `connectivity.py` to import
`world.art.connectivity`, which the `art-service-connectivity-surface`
requirement forbids and an import-boundary test enforces. This change delivers
D13's actual guarantee instead: a request while SD is offline enqueues, settles
`failed` with the existing bounded named error code, appends no card, and surfaces
that code on the gallery record — a *reported* unavailable outcome that leaves the
resolution chain and offline playability untouched.

No backward compatibility or data migration: no released users, no gallery data.

## Capabilities

### New Capabilities

- `art-gallery-generation`: the per-image gallery request seam, its validation and
  failure reporting, the orphan prune, and the gallery generation boundary events.

### Modified Capabilities

- `art-queue-worker`: the record contract admits gallery job records; the
  subject-keyed idempotent `ensure` requirement gains the separate per-image
  gallery enqueue that shares the one lock and worker slot; the worker contract
  derives the expected identity from the record and publishes a gallery job as a
  card append rather than a record field transition.

## Impact

- `world/art/store.py` — four new nullable `AttributeProperty` fields.
- `world/art/queue.py` — `enqueue_gallery_job`, job-key-resolved settle,
  gallery-aware `failed_keys()`.
- `world/art/worker.py` — record-derived expected identity, gallery settle branch,
  spent-job deletion, `gallery_settle` event.
- `world/art/service.py` — `request_gallery_image`, `prune_gallery_orphans`,
  `gallery_generate` event.
- `server/conf/at_server_startstop.py` — one new startup step for the prune.
- `world/art/tests/` — queue, worker, and service coverage.
- Unaffected: the sd-webui client seam and its request builder, `formats.py`,
  scene and monster classic jobs, the presenter, the media route, every webclient
  payload, and every player-facing command.
