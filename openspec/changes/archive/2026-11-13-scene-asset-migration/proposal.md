# Proposal: migrate classic scene assets to scene gallery cards

## Batch:

Gallery window programme, stage 3 ("Existing scene asset records and image
files migrate to gallery records. The migration is idempotent and leaves no
orphan file or record.").

- depends-on: scene-kind-gallery
- conflict: `world/art/service.py` (new function, `ensure_scene_asset`,
  `_sync_registry_subjects`), `server/conf/at_server_startstop.py` (new
  startup step before `art_gallery_prune`); `scene-classic-fallback-removal`
  edits the scene chain next.

## Why

Generated backgrounds that players already see are classic records. The
design requires them to become scene gallery cards so the gallery is the only
generated source, without regenerating images that already exist. This is the
one migration the programme explicitly asks for (the project otherwise adds
no migrations pre-release).

## What Changes

- New `world/art/service.py::migrate_classic_scene_records() -> dict`, run as
  startup step `art_scene_migration` immediately before `art_gallery_prune`:
  converts each settled classic scene record per the ADDED requirement, using
  `world/art/gallery.py::append_card` (sole gallery writer) and deleting the
  classic record (service.py is the sole asset-record writer).
- The two scene producers switch in the same change, so no classic scene
  record is created after the conversion: `ensure_scene_asset` and the scene
  loop of `_sync_registry_subjects` call
  `_ensure_gallery_subject(scene_subject_for(archetype))`, skipping an
  archetype whose gallery record exists without a card and without a
  recorded error (a player's deletion), so a deletion is not undone while a
  failed first generation is still retried.
- Runs at every startup, so a classic record still pending at one start is
  converted at a later one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-asset-lifecycle`: startup conversion of classic scene outputs;
  startup and room entry request scene gallery art instead of classic
  records.

## Impact

- Code: `world/art/service.py`, `server/conf/at_server_startstop.py` and its
  step-catalog test.
- Tests: a new test class beside the prune tests.
- Estimate: 8 hours (conversion function 2 h, startup wiring 0.5 h,
  conversion tests with real files 2.5 h, producer switch with the deletion
  rule 1 h, producer tests 1.5 h, gates 0.5 h).
