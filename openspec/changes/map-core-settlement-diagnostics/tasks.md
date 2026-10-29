# Tasks

One engineer-day, approximately 8 hours including focused verification. Apply before `map-location-relative-placement`; this proposal authorizes no implementation by itself.

## 1. Shared core rules (3 hours)

- [x] 1.1 Extract the design D2 anchor, location-ownership and interior room/doorway rules into candidate-scoped core structure/semantic diagnostics; verify missing-anchor and empty-graph WIP and stable provenance with the matrix tests in 1.3.
- [x] 1.2 Move the complete existing wilderness mask/terrain/gate rule set into the same core boundary, including point hash cells versus obstacle cells, per-direction neighbor validity, global approach and destination collisions; verify the matrix retains existing schema checks without duplicate diagnostics.
- [x] 1.3 Add independent synthetic core cases and valid controls in `packages/map-core/tests/test_authoring.py` for every D2 matrix row and the pre-existing wilderness malformed cases, asserting code/category/owner and load-versus-runtime effect.
- [x] 1.4 Update `docs/development/map-authoring-documents.md` validation ownership and human-review its category descriptions against the D2 matrix and approved editor design.

## 2. Consumer cutover and agreement (3 hours)

- [ ] 2.1 Make `world/maps/runtime.py`, `map_data.py`, `geography.py` and `interiors.py` use the shared diagnostics before publication; migrate startup `world/lore/sync.py`, delete the game-local `validate_wilderness_entries` implementation and every obsolete caller, and retain actual runtime entry geometry helpers and external-reference checks. Leave the two binding-equality checks until the dependent schema cutover.
- [ ] 2.2 Delete the moved checks from `.agents/skills/map-data-authoring/scripts/check_map_sources.py`; consume core categories/codes and preserve unrelated external/district checks and failure status, verified by the checker/core agreement cases. Update the skill `SKILL.md` invariant table/check descriptions and human-review against the handoff, retaining still-current binding instructions for this intermediate slice.
- [ ] 2.3 Extend `tests/test_map_authoring_contract.py`, `world/maps/tests/test_settlement_sources.py`, `test_interior_sources.py` and the lore wilderness boundary tests with the independently invalid core-versus-game matrix, no-publication/no-persistence assertions and a valid control. Migrate pure validator cases to core tests without replacing real game-boundary evidence.
- [ ] 2.4 Import `covers_requirement` from `tools.spec_traceability` on discoverable substantively matching tests using design D3's existing canonical IDs; update shard ownership only if adding or moving registered tests.
- [ ] 2.5 Regenerate and commit `content/map-reference-context.json` after final core/lore changes, using design D5's valid temporary repository copy because the protected live sources still contain the reproduction. Run `uv run --locked python -m tools.map_reference_context` and its `--check` there, verify the source manifest matches the actual changed code, and copy back only this generated index. Existing reference-context freshness/deletion tests must retain current-index behavior; never weaken the dependency closure or touch the live source/partition files.

## 3. Focused integrated verification (2 hours)

- [ ] 3.1 Run focused core authoring and contract tests plus affected settlement/interior/lore game test labels. Use `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb <labels>` with `MUD_TEST_SETTINGS=1` in the env file. Exercise checker delegation on a valid temporary workspace; do not repair the live reproduction here.
- [ ] 3.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate` in the same valid isolated candidate and `openspec validate map-core-settlement-diagnostics --strict`; document the candidate root and exercised results and inspect that all removed validator callsites were migrated. Do not claim root-world acceptance while the live reproduction remains invalid. Full managed browser/evidence runs remain CI-owned.
