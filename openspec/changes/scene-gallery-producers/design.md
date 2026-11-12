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

**Non-Goals:** classic record migration or removal (`scene-asset-migration`).

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

## Risks / Trade-offs

- [Archetypes with a classic `done` record get a fresh gallery request on the
  first entry after this change] → intended: the gallery card then wins; the
  classic output stays as fallback until migration, which converts instead of
  regenerating where a classic output exists.
