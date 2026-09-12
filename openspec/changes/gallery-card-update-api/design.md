# Design: gallery-card-update-api

## D1 — In-place updates inside the existing single-writer boundary

Each writer: take `gallery_lock`, tolerant-read the subject's cards, find the
raw entry by `image_id` (miss → typed `GalleryRecordError("no card with
image_id …")` mirroring `remove_card`), validate the incoming value through the
existing validators (`validate_face_rect` / `validate_binding` + the kind's
capability declaration), rewrite that one entry in the copied list, commit
`record.db.cards`. Files are never touched; ordering, `default_image_id`, and
every other card field are byte-stable. A malformed entry matching the id is
`unknown_card` (the tolerant read already refuses to surface it — updating it
would launder corruption).

## D2 — Binding updates obey the same capability gate as creation

`update_card_binding` refuses a kind whose declaration supports no bindings
with the same capability-naming typed error the service seam raises, so a
monster card can never gain a binding through the update path that creation
refused. An explicit `None` binding unbinds (legal — `binding` is nullable).

## D3 — The resolver publishes the lookup the service already has

`resolve_gallery_subject_by_key(subject_key)` parses the serialized
`kind:key` full subject form, routes registry kinds through
`monster_subject_for` (re-validated, never trusted from the key alone), and
character-kind keys through the existing private stable-key live-entity
lookup, then `character_subject_for(entity)` — returning `(subject, entity)`.
Unknown kind prefix, unresolvable key, or dead entity → typed
`ArtSubjectError`. Read-only; no age check, no gallery read (preconditions stay
where they are).
