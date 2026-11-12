# Proposal: scene art producers use the gallery

## Batch:

Gallery window programme, stage 3 ("Generation, pending and failed states,
deletion and pushes go through the gallery path the other kinds use").

- depends-on: scene-asset-migration
- conflict: `world/art/service.py` (`ensure_scene_asset`,
  `_sync_registry_subjects`), `world/art/presenter.py` (scene chain); lands
  after `scene-asset-migration`, which edits the same modules.

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
- The scene chain's classic fallback (the classic `done` record read after the
  gallery card, and its prior-output retention) is removed: every classic
  scene output was converted to a gallery card by `scene-asset-migration` at
  startup, and no producer writes a classic scene record any more.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-asset-lifecycle`: startup and room entry request scene gallery art; no
  classic scene record is created.
- `scene-artwork-presentation`: the generated position is the scene gallery
  default card only.

## Impact

- Code: `world/art/service.py`, `world/art/presenter.py`.
- Tests: the startup sync and room-entry test modules
  (`rg -ln "ensure_scene_asset|art_sync_all" world typeclasses --glob '*tests*'`).
- Estimate: 6 hours (two producer switches 0.5 h, classic fallback removal
  in the scene chain 1 h, tests 3.5 h, spec and gates 1 h).
