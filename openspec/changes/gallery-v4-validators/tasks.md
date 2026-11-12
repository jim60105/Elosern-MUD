# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Python validator

- [ ] 1.1 Add `validate_gallery_v4` and the D3 constants to `web/webclient/presentation/gallery.py` implementing design D1 exactly, reusing the v3 card/official/equipment/warning helpers; do not change `validate_gallery` or the registry. Verify by 3.1.

## 2. JavaScript mirror

- [ ] 2.1 Add `validateGalleryPanelV4` and the mirrored constants to `web/static/webclient/js/elosern/protocol/panels/gallery.js`, re-export them from `web/static/webclient/js/elosern/protocol.js`, and extend `validateGalleryActionPayload` per design D4; leave `PANEL_ALLOWLIST` at `gallery: 3`. Verify `node --test web/static/webclient/js/tests/protocol_gallery_v4.test.js` (new file) passes.

## 3. Parity

- [ ] 3.1 Add `GalleryV4ParityTests` to `web/webclient/presentation/tests/test_gallery_panel.py` per design D5, one test per ADDED scenario decorated with its requirement ID. Verify `<prefix> web.webclient.presentation.tests.test_gallery_panel` passes and `node --test web/static/webclient/js/tests/*.test.js` passes.

## 4. Client fixtures

- [ ] 4.1 Create `web/webclient-app/stories/gallery-fixtures-v4.js` per the proposal and `web/static/webclient/js/tests/gallery_fixtures_v4.test.js` validating every exported panel with `validateGalleryPanelV4`. Verify `node --test web/static/webclient/js/tests/gallery_fixtures_v4.test.js` passes.

## 5. Gates

- [ ] 5.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change gallery-v4-validators`; both pass.
- [ ] 5.2 Run `openspec validate gallery-v4-validators --strict`; it passes.
