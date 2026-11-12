# Proposal: scene art producers use the gallery

## Batch:

Gallery window programme, stage 3 ("Generation, pending and failed states,
deletion and pushes go through the gallery path the other kinds use").

- depends-on: scene-kind-gallery
- conflict: `world/art/service.py` (`ensure_scene_asset`,
  `_sync_registry_subjects`); `scene-asset-migration` edits the same module
  next.

## Why

After `scene-kind-gallery` the scene kind has a gallery and the chain reads it,
but room entry and startup still write classic scene records. Switching both
producers to the shared automatic gallery ensure makes every new scene image a
gallery card.

## What Changes

- `ensure_scene_asset(archetype)` and the scene loop of
  `_sync_registry_subjects` call `_ensure_gallery_subject(scene_subject_for(archetype))`
  (one gallery request when the scene gallery holds no card and no in-flight
  job) instead of the classic `queue_ensure`.
- Existing classic scene records stay readable through the chain's classic
  fallback until `scene-asset-migration` converts them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-asset-lifecycle`: startup and room entry request scene gallery art; no
  classic scene record is created.

## Impact

- Code: `world/art/service.py`.
- Tests: the startup sync and room-entry test modules
  (`rg -ln "ensure_scene_asset|art_sync_all" world typeclasses --glob '*tests*'`).
- Estimate: 4 hours (two producer switches 0.5 h, guard behaviour check for
  scenes 0.5 h, tests 2.5 h, gates 0.5 h).
