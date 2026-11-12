# Proposal: migrate classic scene assets to scene gallery cards

## Batch:

Gallery window programme, stage 3 ("Existing scene asset records and image
files migrate to gallery records. The migration is idempotent and leaves no
orphan file or record.").

- depends-on: scene-kind-gallery
- conflict: `world/art/service.py` (new function),
  `server/conf/at_server_startstop.py` (new startup step before
  `art_gallery_prune`); `scene-gallery-producers` edits `service.py` next.

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
- Runs at every startup, so a classic scene record that settles before
  `scene-gallery-producers` lands is converted at the next start.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-asset-lifecycle`: startup conversion of classic scene outputs.

## Impact

- Code: `world/art/service.py`, `server/conf/at_server_startstop.py` and its
  step-catalog test.
- Tests: a new test class beside the prune tests.
- Estimate: 6 hours (conversion function 2 h, startup wiring 0.5 h, tests for
  six scenarios with real files under a temporary store root 3 h, gates 0.5 h).
