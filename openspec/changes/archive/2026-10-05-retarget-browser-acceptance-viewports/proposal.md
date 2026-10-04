# Proposal: retarget-browser-acceptance-viewports

## Why

The browser acceptance contract pins its journeys to 1440x900 and 1280x720 (plus a handful of
1920x1080 pins). Those sizes were chosen as "supported desktop viewports" under the old
1920x1080 reference; the retarget (`retarget-desktop-viewport-contract`, which this change
depends on) makes 1451x790 the reference viewport and drops 1280x720 and 1440x900 from the
contract as required acceptance sizes. The acceptance matrix must follow the contract it
verifies, or CI keeps proving geometry the player never sees while the real viewport goes
untested.

## What Changes

- **BREAKING** The acceptance viewport pair becomes **1451x790** (the reference) and
  **2560x1440** (the chrome-factor cap): every "at 1440x900 and 1280x720" journey in the
  acceptance requirements runs at the new pair. 1741x948 (uncapped S = 1.2) replaces 1920x1080
  as the proportionality pin where a geometry-observing requirement needs an uncapped large
  viewport — such requirements are owned by the dependency change, not here.
- `web/tests/browser/browser_base.py`: `DEFAULT_VIEWPORT` (1440, 900) → (1451, 790).
- Every Playwright module iterating `((1920, 1080), (1440, 900), (1280, 720))` (≈43 files)
  iterates `((1451, 790), (1741, 948), (2560, 1440))`: the reference, an uncapped 1.2 display,
  and the capped large display. Size-driven assertions inside those modules (band height,
  island canvas, message font) are re-pointed to the values the dependency change's amended
  requirements state (220px band, 240px island, 18px default prose at reference scale).
- The acceptance requirements that carry only viewport enumerations — browser-verification's
  foundation journey, the four per-feature acceptance requirements, pointer parity, art-panel
  acceptance, and the creation-ui bounds requirement — are amended here. Requirements whose
  text mixes geometry with viewports are amended by the dependency change and MUST NOT be
  touched in this one.
- Desktop-only stance unchanged; no new test framework, per `openspec/config.yaml`.

## Capabilities

### New Capabilities

_(None)_

### Modified Capabilities

- `webclient-browser-verification`: "Browser acceptance covers foundation recovery and layout
  behavior" — surface visibility and anchor-overlap checks move to 1451x790 and 2560x1440; the
  dialogue stage journey's 1920x1080 pin moves to the reference viewport.
- `webclient-combat-menu`, `webclient-exploration-menu`, `webclient-service-menus`,
  `webclient-character-creation-ui` (both acceptance and bounded-desktop requirements),
  `webclient-pointer-activation`, `webclient-art-panel`: their keyboard-only / pointer-parity /
  art acceptance viewport enumerations move to the acceptance pair (1451x790, 2560x1440); the
  "focused disabled control" fit checks move from 1280x720 to the reference viewport, which is
  the tightest size in the contract and the only one below the old floor's chrome assumptions.

## Impact

- `web/tests/browser/browser_base.py` (`DEFAULT_VIEWPORT`) and every
  `web/tests/browser/test_*.py` carrying the viewport tuple (≈43 modules; grep
  `1920, 1080`).
- Size-driven assertions in those modules follow the amended reference geometry from
  `retarget-desktop-viewport-contract` (220px band at reference, 240px island canvas,
  16/18/20px prose steps). No assertion logic changes — only its reference values.
- `.github/evennia-shards.json` unchanged (no new test modules; tuples change in place).
- `docs/game` unaffected; `web/webclient-app` source untouched (dependency change owns it).
- Depends on: `retarget-desktop-viewport-contract` (the numbers the journeys assert).
