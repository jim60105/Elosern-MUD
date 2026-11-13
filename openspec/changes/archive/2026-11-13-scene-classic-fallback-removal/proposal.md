# Proposal: remove the classic fallback from the scene chain

## Batch:

Gallery window programme, stage 3 ("The generated step of the background chain
reads the scene gallery's default card").

- depends-on: scene-asset-migration
- conflict: `world/art/presenter.py` (scene chain), the browser scene
  support `web/browser_support/unified_image_transitions.py`, the browser
  seeds `web/tests/browser/seed/art_fixture.py` and `exploration_fixture.py`,
  `web/tests/browser/test_browser_unified_scenes.py`,
  `web/tests/browser/test_browser_art.py`.

## Why

After `scene-asset-migration` every classic scene output is a gallery card and
no producer writes classic scene records, but the scene chain still reads the
classic record after the gallery card. Removing that fallback makes the scene
gallery the only generated source, as the design states.

## What Changes

- The scene chain's classic branch kept by `scene-kind-gallery` (classic
  `done` output, classic generation state, classic current/prior-output
  retention) is deleted for scenes; generation state and retention read only
  the scene gallery.
- The browser scene staging (`pending_scene`, `failed_scene`, `done_scene`,
  `move_scene`) and the browser seeds stage scene gallery jobs and cards
  instead of classic records; the two browser scene journeys keep passing.
- The generic classic queue/worker code stays (it still serves its specified
  contract; no producer reaches it for scenes).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scene-artwork-presentation`: the generated position is the scene gallery
  default card only.

## Impact

- Estimate: 7 hours (chain branch removal 1 h, presenter tests 1.5 h, browser
  support and seeds 2.5 h, two browser journeys run and fixed 1 h, dist
  rebuild and gates 1 h).
