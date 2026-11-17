# Tasks

## 1. Pure preview construction

- [ ] 1.1 Extract the explicit-value band resolver in `world/art/gallery_fallback.py` and keep entity-based callers unchanged. Extend `world/art/tests/test_gallery_fallback.py` with synthetic actor identities and interval boundaries; the focused fallback command in design must pass with parity for `other` and no policy/identity write.
- [ ] 1.2 Add preset/silhouette descriptor builders in `world/art/presenter.py`, calling the documented preset official-reference seam and existing descriptor geometry primitives. Add synthetic catalog/no-catalog tests alongside presenter tests; assert only the card’s own official default can be attempted, generation fields are null, terminal always exists, and no gallery/job/file/character write occurs.

## 2. Schema cutover

- [ ] 2.1 Extend `web/webclient/presentation/creation.py` serialization and validation and the mirror `protocol/panels/creation.js` to schema 7, required card artwork and exact silhouette entries. Extend `test_creation_panel/test_validation_core.py` and `protocol_creation.test.js` with identical malformed cases (missing/null artwork, URL violations, empty/oversize table, unknown sex, noninteger/reversed/out-of-range endpoints, coverage gaps/overlaps and invalid descriptor semantics); both focused commands in design must reject every case.
- [ ] 2.2 Update all affected synthetic creation panel builders, including `stories/fixtures/creation_panels.js` and Node protocol fixtures, without introducing a shipped roster/copy assertion. Update `docs/development/webclient-synchronization.md` with schema 7, actor-specific hashing and the single-source version rule; presenter/Node focused commands in design must pass and the existing envelope limit must remain unchanged.

## 3. Delivery acceptance

- [ ] 3.1 Run each focused command in design independently, then `openspec validate creation-panel-artwork --strict`; expect no failures or warnings. Record test-to-delta-scenario evidence without inventing canonical ids for ADDED requirements.
- [ ] 3.2 If tests are added/moved as modules, run `uv run --locked python -m tools.shard_register fix`; run `uv run --locked python -m tools.contract_gate` once after integration and retain all unrelated registrations. Expected state is registered real tests, no waiver and no shipped-data pin.
