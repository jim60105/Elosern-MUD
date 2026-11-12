# Design: scene art producers use the gallery

## Context

- `world/art/service.py::ensure_scene_asset(archetype)` validates the
  archetype and calls `queue_ensure(subject, description_for(subject))`
  (classic), bounded by `log_warn("art_scene_ensure_skipped")`.
- `_sync_registry_subjects()` loops `SCENE_ARCHETYPE_REGISTRY` with
  `queue_ensure` and visual species with `_ensure_gallery_subject(subject)`.
- `_ensure_gallery_subject(subject)` → `_guarded_gallery_request(subject,
  None)`: requests one image only when the gallery is empty, no gallery job is
  in flight and no satisfying official default exists.
- Room hooks (`typeclasses/rooms.py` GridRoom/InstanceRoom
  `at_object_receive`) call `ensure_scene_asset` for `PlayerCharacter`
  arrivals.

## Goals / Non-Goals

**Goals:** both producers use the gallery ensure.

**Non-Goals:** converting classic records (done by `scene-asset-migration`,
which lands first); removing the generic classic queue/worker code, which no
producer reaches after this change but which still serves its specified
contract.

## Decisions

1. `ensure_scene_asset`: replace the two classic lines with
   `_ensure_gallery_subject(scene_subject_for(archetype))`; keep the guard and
   the bounded warning.
2. `_sync_registry_subjects`: the scene loop calls
   `_ensure_gallery_subject(scene_subject_for(archetype))`; update its
   docstring (no classic producer remains for any kind).
3. Official-default check for scenes (verified): `_official_default_satisfies`
   answers False for a bare `ArtSubject` with no entity ("a subject whose
   reference the caller cannot see answers False"), and both scene producers
   pass a bare subject, so scenes autogenerate exactly as the classic path
   did. No branch is needed; add one test that a scene whose archetype has an
   operator official image still receives its gallery request.

4. Scene chain: delete the classic branch that `scene-kind-gallery` kept
   behind `_scene_gallery_card` (the `_scene_generated_resource` call over the
   classic record, the classic generation state and the classic
   current/prior-output retention for scenes). A scene with no gallery card
   has no generated attempt; its generation state comes from gallery jobs and
   the gallery record's error only.
5. Deleted scenes stay deleted (planner decision, flagged): Specification 3
   says "Deleting returns the archetype to its bundled image", but the shared
   guard requests a new image whenever the gallery is empty, which would
   regenerate a deleted scene on the next entry. Both scene producers
   therefore first check `gallery_api.record_for(subject) is None` and skip
   the request when a record exists (a player's deletion leaves the empty
   record in place; `remove_card` never deletes the record). First-time
   archetypes have no record and still autogenerate.

## Risks / Trade-offs

- [A classic scene record created between the migration's startup run and this
  change's deploy] → impossible in practice (both land through startup), and
  the migration runs at every startup, so the next start converts it; this
  change's removal only stops reading it.
