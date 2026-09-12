# Proposal: gallery-card-update-api

## Why

The gallery management UI batch (`webclient-gallery-panel`,
`webclient-gallery-actions`, `webclient-gallery-ui`) needs two mutations the
shipped backend does not have: re-marking an existing card's `face_rect`
(臉部框選 儲存框選) and re-saving an existing card's `binding` (裝備綁定
儲存綁定). `world/art/gallery.py` today mutates only whole-list/card lifecycle
state — `append_card`, `remove_card`, `set_default`, `record_error`,
`clear_error` — and the sole-writer contract forbids any other module from
touching cards. Without in-place card writers the binding/face-rect actions
would either fail or force an append-remove replace (new `image_id`, lost
provenance, replaced default). The management adapters also need one public
seam to resolve a rail `subject_key` back to its live entity — today that
lookup is private to `world/art/service.py`, while the presenter rail and the
adapters both need it (companions and other-character subjects cannot reach
`request_gallery_image` without their entity's declared age precondition).

## What Changes

- Two new single-writer card updates in `world/art/gallery.py`, each under
  `gallery_lock`, each re-reading through the tolerant card read (a malformed
  or missing entry is `unknown_card`, typed):
  - `update_card_face_rect(subject, image_id, face_rect)` — validates through
    the shared `validate_face_rect`, stores the rect verbatim (no crop, no
    file write, no second image — D9), leaves order/default/other fields
    untouched.
  - `update_card_binding(subject, image_id, binding)` — validates through
    `validate_binding` (mask/snapshot coherence) AND the kind's capability
    declaration (a kind declaring no binding support raises the typed
    capability error), stores verbatim, never touches files.
  One `gallery_card_updated` facade event each (context `subject`, `image_id`,
  `kind`, field name).
- One public read-only resolver in `world/art/service.py`:
  `resolve_gallery_subject_by_key(subject_key)` returning
  `(subject, entity_or_None)` — registry kinds through the typed producer,
  entity-derived kinds through the existing stable-key live-entity lookup
  (published, not duplicated); unknown/unresolvable keys raise the existing
  typed `ArtSubjectError`. It mutates nothing; the webclient presenter rail
  enrichment and the gallery management adapters are its only new callers.
- No wire, no webclient, no queue/worker behavior changes.

## Capabilities

### New Capabilities

(None — the writers extend the shipped `art-gallery-model` writer contract.)

### Modified Capabilities

- `art-gallery-model`: gains the two in-place card-update requirements inside
  the existing sole-writer boundary, and the public subject-key resolver
  requirement (the resolver is an `art-subject-model` surface read published
  from the service module — declared here to keep this one backend change).

## Impact

- `world/art/gallery.py` (two writers + events), `world/art/service.py` (one
  published resolver) — this change exclusively owns the batch's `world/art/`
  hunks.
- New test module owned by `.github/evennia-shards.json` through the shard's
  existing `world.art` prefix label (the exactly-once shard contract forbids
  an additional explicit label);
  `@covers_requirement` on the new requirements.
- Unblocks `webclient-gallery-actions` (depends-on).

## Batch:

- depends-on: (none — backend-only, rides today's shipped model)
- Code-conflict notes: owns `world/art/gallery.py` and the
  `world/art/service.py` resolver hunk; no overlap with the webclient changes.
  `webclient-gallery-actions` now lists this change in its own Batch section.
  Scope note: well under one engineer-day (two narrow writers + one resolver).
