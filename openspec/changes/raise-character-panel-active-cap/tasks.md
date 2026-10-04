# Tasks — raise-character-panel-active-cap

## 1. Server bound

- [ ] 1.1 Set `MAX_ACTIVE_ROWS = 96` in `web/webclient/presentation/character.py` and update the comment block at the "Exact shared bounds (design D10) — must stay equal in the JS validator" header to record that the actives bound is deliberately wider than `MAX_PASSIVE_ROWS` (96 vs 32: actives absorb the act-catalogue unlock flood, passives do not), keeping every other constant (including `MAX_PASSIVE_ROWS = 32`) untouched; verify `uv run --locked python -c "from web.webclient.presentation.character import MAX_ACTIVE_ROWS, MAX_PASSIVE_ROWS; print(MAX_ACTIVE_ROWS, MAX_PASSIVE_ROWS)"` prints `96 32`.

## 2. JS wire-validator mirror

- [ ] 2.1 Set `var CHARACTER_MAX_ACTIVE_ROWS = 96;` in `web/static/webclient/js/elosern/protocol/panels/character.js` (leave `CHARACTER_MAX_PASSIVE_ROWS` at 32); the re-export in `web/static/webclient/js/elosern/protocol.js` is name-based and needs no edit; verify `node --test web/static/webclient/js/tests/*.test.js` passes (no character test pins the literal 32 — they are constant-driven) and that the Vitest suite `web/webclient-app/tests/` passes unchanged.
- [ ] 2.2 Run the Python↔JS parity gate and verify it is green with both sides at 96: `uv run --locked python -m unittest tests.test_exploration_parity_contract` (verified: the module extracts both literals from source via regex and asserts equality — no numeric pin to edit).

## 3. Frozen-contract audit surface

- [ ] 3.1 Confirm `docs/development/webclient-vue-frozen-contract-audit.md` enumerates only the constant name `CHARACTER_MAX_ACTIVE_ROWS` (verified at proposal time: no numeric pin there) and search for any audit manifest under `tools/` (e.g. the frozen-contract/audit tooling) that pins the numeric value; if one exists, update it to 96 in this change, otherwise record in the PR description that no numeric audit pin exists and no audit artifact edit is required.

## 4. Python tests

- [ ] 4.1 Add an explicit boundary test to `web/webclient/presentation/tests/test_character_panel/test_schema_envelope.py` asserting `validate_character` accepts an `actives` payload with exactly `MAX_ACTIVE_ROWS` (96) flattened rows across the eight category groups, rejects 97, and still rejects a 33-row `passives` payload under `MAX_PASSIVE_ROWS`; annotate with `@covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")`; verify with `MUD_TEST_SETTINGS=1 uv run --locked python -m evennia test --settings test_settings.py --noinput web.webclient.presentation.tests.test_character_panel` (the CI evennia-shard invocation).
- [ ] 4.2 Reconcile the constant-driven bound tests so every actives rejection exercises 97 rows and every actives acceptance exercises 96: `test_flattened_row_count_bound_applies_not_the_category_group_count` (uses `bound + 1` and two `bound // 2` halves — 48+48=96 must stay accepted; confirm), `test_worst_case_legal_payload_fits_the_envelope` (actives section now spans 96 rows; assert the full payload still satisfies `assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)` — measured 31,575 bytes, so no threshold change), and the `MAX_ACTIVE_ROWS`-sized fixtures in `test_schema_detail_fields.py` (rows-at-bound acceptance) and its wide-label payload; verify the whole `test_character_panel` package passes.
- [ ] 4.3 Add a presenter regression to `web/webclient/presentation/tests/test_character_panel/test_presenter.py` proving the bug class is closed: for an actor whose read model legitimately assembles more than 32 active skill rows (e.g. 61 — stored keys plus unlocked act-catalogue keys via `unlocked_act_keys_for`, or the smallest kit-faithful roster above 32), the registry renders the `character` panel with `available: true` and every active row present in the grouped shape, never an internal-unavailable payload; annotate with `@covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")`; verify it fails on 32 (temporarily revert the constant locally to confirm) and passes on 96.

## 5. Traceability and gates

- [ ] 5.1 Run spec traceability and verify the amended requirement is covered with literal IDs: `uv run --locked python -m tools.spec_traceability list` (the amended requirement shows the new boundary/regression tests) then `uv run --locked python -m tools.spec_traceability check` green.
- [ ] 5.2 Run `openspec validate raise-character-panel-active-cap --strict` (and `openspec validate --all --strict`) green for the delta; after the change is archived, `openspec validate --all --strict` must be green with the amended bound merged into `openspec/specs/webclient-exploration-menu/spec.md`.
- [ ] 5.3 Run `contract_gate` (repo contract gate) and verify green, including the exploration parity contract; verify no other presentation capability's bounds moved (`MAX_TRAIT_ROWS`, `MAX_EQUIPMENT_ROWS`, `MAX_DISPLAYED_ROWS`, `MAX_PASSIVE_ROWS`, `MAX_CATEGORY_GROUPS` all unchanged).

## 6. Explicit non-touches

- [ ] 6.1 Verify `docs/game/commands.md` and `docs/game/command-reference.md` are untouched in the diff (no player-command surface change), and that `.github/evennia-shards.json` is unchanged unless task 4.x added or renamed a test *module* (new tests inside existing modules require no manifest change; if a new module is added, register its shard entry in the same commit).
