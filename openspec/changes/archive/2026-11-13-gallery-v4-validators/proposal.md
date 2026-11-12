# Proposal: mirrored version-4 gallery panel validators

## Batch:

Gallery window programme, stage 1 (design D6 of
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: gallery-kind-card-capabilities
- conflict: edits `web/webclient/presentation/gallery.py` and
  `web/static/webclient/js/elosern/protocol/panels/gallery.js` additively;
  `gallery-v4-presenter` and `gallery-v4-cutover` edit the same files later.
  Must land before both.

## Why

The v4 panel carries one category at a time. Both validator mirrors must
enforce its exact shape, fail closed, and keep a hard subject ceiling that
turns a programming error into the common unavailable form instead of a
truncated list. Building them additively first, while v3 stays registered,
lets the presenter and the client components be developed and tested against
a real contract before the wire cuts over.

## What Changes

- Python `validate_gallery_v4(payload)` in
  `web/webclient/presentation/gallery.py` and its exact JavaScript mirror
  `validateGalleryPanelV4(payload)` in
  `web/static/webclient/js/elosern/protocol/panels/gallery.js`, both exported
  but NOT registered: `PANEL_ALLOWLIST` keeps `gallery: 3` and the registry
  keeps the v3 presenter until `gallery-v4-cutover`.
- The v4 shape of design D6 plus two decisions recorded in design.md: a
  nullable top-level `description` (the selected scene's sentence; null for
  every other kind) and three capability booleans from
  `gallery-kind-card-capabilities`.
- Group expansion: a group with `expanded: false` carries `count` and no
  subjects; validators accept it now so the people category needs no wire
  change.
- A hard ceiling of 256 subjects per panel.
- The JavaScript action-payload validator accepts `gallery.category.select
  {category}` and `gallery.group.select {group}` so the client can send them
  once the server registers them.
- Dual-direction parity cases for every v4 rule.
- New shared client fixtures `web/webclient-app/stories/gallery-fixtures-v4.js`
  (synthetic v4 panels: mine with a tray subject, party, monster tiers,
  empty category, pending/failed/official rows, collapsed people groups) with a
  Node test that every exported panel passes `validateGalleryPanelV4`. The v3
  `gallery-fixtures.js` stays until `gallery-v4-cutover`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-panel`: adds the version-4 payload contract and its
  mirrored validators (not yet the registered version).

## Impact

- Code: the two validator files and `web/static/webclient/js/elosern/protocol.js`
  (re-export the new function and constants).
- Tests: `web/webclient/presentation/tests/test_gallery_panel.py` (new v4
  parity test class) and `web/static/webclient/js/tests/protocol_gallery_artwork.test.js`
  or a new `protocol_gallery_v4.test.js` (Node gate).
- Estimate: 8 hours (Python validator 2 h, JS mirror 2 h, parity cases and Node
  tests 2 h, v4 client fixtures with validity test 1.5 h, spec and gates 0.5 h).
