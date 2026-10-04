# Tasks — raise-character-panel-active-cap

## 1. Server bound

- [x] 1.1 Set `MAX_ACTIVE_ROWS = 96` in `web/webclient/presentation/character.py` and update the comment block at the "Exact shared bounds (design D10) — must stay equal in the JS validator" header to record that the actives bound is deliberately wider than `MAX_PASSIVE_ROWS` (96 vs 32: actives absorb the act-catalogue unlock flood, passives do not), keeping every other constant (including `MAX_PASSIVE_ROWS = 32`) untouched; verify `uv run --locked python -c "from web.webclient.presentation.character import MAX_ACTIVE_ROWS, MAX_PASSIVE_ROWS; print(MAX_ACTIVE_ROWS, MAX_PASSIVE_ROWS)"` prints `96 32`.

## 2. JS wire-validator mirror

- [x] 2.1 Set `var CHARACTER_MAX_ACTIVE_ROWS = 96;` in `web/static/webclient/js/elosern/protocol/panels/character.js` (leave `CHARACTER_MAX_PASSIVE_ROWS` at 32); the re-export in `web/static/webclient/js/elosern/protocol.js` is name-based and needs no edit; verify `node --test web/static/webclient/js/tests/*.test.js` passes (no character test pins the literal 32 — they are constant-driven) and that the Vitest suite `web/webclient-app/tests/` passes unchanged.
- [x] 2.2 Run the Python↔JS parity gate and verify it is green with both sides at 96: `uv run --locked python -m unittest tests.test_exploration_parity_contract` (verified: the module extracts both literals from source via regex and asserts equality — no numeric pin to edit).

## 3. Frozen-contract audit surface

- [x] 3.1 Confirm `docs/development/webclient-vue-frozen-contract-audit.md` enumerates only the constant name `CHARACTER_MAX_ACTIVE_ROWS` (verified at proposal time: no numeric pin there) and search for any audit manifest under `tools/` (e.g. the frozen-contract/audit tooling) that pins the numeric value; if one exists, update it to 96 in this change, otherwise record in the PR description that no numeric audit pin exists and no audit artifact edit is required.

## 4. Python tests

- [x] 4.1 Add an explicit boundary test to `web/webclient/presentation/tests/test_character_panel/test_schema_envelope.py` asserting `validate_character` accepts an `actives` payload with exactly `MAX_ACTIVE_ROWS` (96) flattened rows across the eight category groups, rejects 97, and still rejects a 33-row `passives` payload under `MAX_PASSIVE_ROWS`; annotate with `@covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")`; verify with `MUD_TEST_SETTINGS=1 uv run --locked python -m evennia test --settings test_settings.py --noinput web.webclient.presentation.tests.test_character_panel` (the CI evennia-shard invocation).
- [x] 4.2 Reconcile the constant-driven bound tests so every actives rejection exercises 97 rows and every actives acceptance exercises 96: `test_flattened_row_count_bound_applies_not_the_category_group_count` (uses `bound + 1` and two `bound // 2` halves — 48+48=96 must stay accepted; confirm), `test_worst_case_legal_payload_fits_the_envelope` (actives section now spans 96 rows; assert the full payload still satisfies `assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)` — measured 31,575 bytes, so no threshold change), and the `MAX_ACTIVE_ROWS`-sized fixtures in `test_schema_detail_fields.py` (rows-at-bound acceptance) and its wide-label payload; verify the whole `test_character_panel` package passes.
- [x] 4.3 Add a presenter regression to `web/webclient/presentation/tests/test_character_panel/test_presenter.py` proving the bug class is closed: for an actor whose read model legitimately assembles more than 32 active skill rows (e.g. 61 — stored keys plus unlocked act-catalogue keys via `unlocked_act_keys_for`, or the smallest kit-faithful roster above 32), the registry renders the `character` panel with `available: true` and every active row present in the grouped shape, never an internal-unavailable payload; annotate with `@covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")`; verify it fails on 32 (temporarily revert the constant locally to confirm) and passes on 96.

## 5. Traceability and gates

- [x] 5.1 Run spec traceability and verify the amended requirement is covered with literal IDs: `uv run --locked python -m tools.spec_traceability list` (the amended requirement shows the new boundary/regression tests) then `uv run --locked python -m tools.spec_traceability check` green.
- [x] 5.2 Run `openspec validate raise-character-panel-active-cap --strict` (and `openspec validate --all --strict`) green for the delta; after the change is archived, `openspec validate --all --strict` must be green with the amended bound merged into `openspec/specs/webclient-exploration-menu/spec.md`.
- [x] 5.3 Run `contract_gate` (repo contract gate) and verify green, including the exploration parity contract; verify no other presentation capability's bounds moved (`MAX_TRAIT_ROWS`, `MAX_EQUIPMENT_ROWS`, `MAX_DISPLAYED_ROWS`, `MAX_PASSIVE_ROWS`, `MAX_CATEGORY_GROUPS` all unchanged).

## 6. Explicit non-touches

- [x] 6.1 Verify `docs/game/commands.md` and `docs/game/command-reference.md` are untouched in the diff (no player-command surface change), and that `.github/evennia-shards.json` is unchanged unless task 4.x added or renamed a test *module* (new tests inside existing modules require no manifest change; if a new module is added, register its shard entry in the same commit).

## Apply notes

Verified on `feat/raise-character-panel-active-cap` (base `96845a9d`). No merge/rebase/archive; the main spec is amended only through the delta at archive time.

- 1.1 `MAX_ACTIVE_ROWS = 96`, `MAX_PASSIVE_ROWS = 32` confirmed by source extraction (regex read of the module prints `96 32`); a bare `uv run ... python -c "from web.webclient... import ..."` cannot import the module, because `server/conf/test_settings.py` and the presenter's Evennia imports require the `evennia test` process (the guard rejects `MUD_TEST_SETTINGS=1 python -c`). `tools.spec_traceability`/`contract_gate` and the focused evennia run below exercise the real import.
- 2.1 `node --test web/static/webclient/js/tests/*.test.js`: 479 pass / 0 fail. `pnpm test` (Vitest, `web/webclient-app/tests/`): 136 files, 1529 pass / 0 fail.
- 2.2 `uv run --locked python -m unittest tests.test_exploration_parity_contract`: OK, 5 tests (both literals 96).
- 3.1 No numeric audit pin exists: `docs/development/webclient-vue-frozen-contract-audit.md` enumerates only the constant name `CHARACTER_MAX_ACTIVE_ROWS` (line 102), and no file under `tools/` references `CHARACTER_MAX_ACTIVE_ROWS`/`MAX_ACTIVE_ROWS`. No audit artifact edit required, and no audit manifest changed.
- 4.1 New `test_actives_boundary_admits_96_rows_and_rejects_97` (96 accepted across the eight category groups / 97 rejected / 33-row passives rejected), annotated with the amended requirement id.
- 4.2 Constant-driven tests reconcile automatically (`bound + 1` rejects, two `bound // 2` halves = 96 accept; the envelope tests keep their thresholds). Only a stale "32 active rows" comment was refreshed in `test_schema_detail_fields.py`. Full `test_character_panel` package: 51 tests OK.
- 4.3 New `test_progressed_active_roster_above_32_renders_the_available_panel` (43-row roster: 40 stored synthetic active rows + 2 innate grants + the unlock-free catalogue act) renders `available: true` with every row present and enriched. Negative check: with `MAX_ACTIVE_ROWS` temporarily reverted to 32 the regression fails (`available` False — the reported bug class), and passes at 96.
- 5.1 `tools.spec_traceability check`: 1865 requirements, 7331 associations, 1865 covered, 0 uncovered, 0 errors; the amended requirement lists the new boundary and regression tests (plus the existing grouping tests).
- 5.2 `openspec validate raise-character-panel-active-cap --strict` → valid; `openspec validate --all --strict` → 283 passed, 0 failed.
- 5.3 `uv run --locked python -m tools.contract_gate` → passed (traceability, observability, test-data, manifests, contracts). `MAX_TRAIT_ROWS`, `MAX_EQUIPMENT_ROWS`, `MAX_DISPLAYED_ROWS`, `MAX_PASSIVE_ROWS`, `MAX_CATEGORY_GROUPS` unchanged.
- 6.1 `git diff --name-only` touches no `docs/game/*` file and no `.github/evennia-shards.json` (no test module added or renamed).

### Review

Post-implementation `rubber-duck` review over the finished diff: **no blocking findings**. Advisory
dispositions: (a) no direct JS accept-96/reject-97 assert pair exists — the Python boundary test
covers the shared bound, the JS tests are constant-driven, and the parity contract keeps the two
literals equal, so no JS test was added; (b) the D3 passive-cap rationale was qualified and given
the same re-derive note D1 carries; (c) the fixture-coupled enrichment assertion mirrors the
existing sibling test and was kept.
