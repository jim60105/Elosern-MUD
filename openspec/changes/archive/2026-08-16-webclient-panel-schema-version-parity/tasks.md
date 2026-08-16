## 1. Server-side single source (D1, D2)

- [x] 1.1 Add `STATUS_SCHEMA_VERSION = 1` to `web/webclient/presentation/status.py` (alongside the module docstring, matching the other presenter modules) and replace the hardcoded `"schema_version": 1` in the returned payload at status.py:53 with the constant
- [x] 1.2 In `web/webclient/presentation/registry.py`, amend `build_production_registry()` to lazily import the eight `<PANEL>_SCHEMA_VERSION` constants from their presenter modules (inside the function body, next to the existing lazy presenter imports — never at module level, to avoid the circular import with `registry.PanelUnavailableError`) and pass each constant as `schema_version=` in the matching `PresenterSpec` registration; the `character` panel thereby registers at 3

## 2. Client cleanup (D3)

- [x] 2.1 Remove the dead `available === false` branch from `validateStatusPanel` (protocol.js ~549-570); `validatePanel` → `validateUnavailablePanel` already owns the unavailable path with the allowlist version
- [x] 2.2 Remove the dead `available === false` branch from `validateContextActionsPanel` (protocol.js ~842) and `validateLocalMapPanel` (protocol.js ~1107), which inline their own version pins
- [x] 2.3 Remove the dead `available === false` branches that delegate to `validateStatusPanel` from `validateServicesPanel` (~1592), `validateCreationPanel` (~2166), `validateExplorationPanel` (~2499), `validateCharacterPanel` (~2746), and `validateArtPanel` (~2959), including their misleading "validateStatusPanel handles it" comments
- [x] 2.4 Keep the reachable per-panel available-form `schema_version` re-checks intact (defense in depth; mirror the Python validators) — do not touch them

## 3. JavaScript tests (D5)

- [x] 3.1 Reroute every unavailable-form assertion in `web/static/webclient/js/tests/protocol.test.js` that calls a per-panel validator directly (status ~225-240, local_map ~1389-1392, services ~1719-1729, creation ~2272-2278, and the art/exploration/character/context_actions equivalents) through `validatePanel(name, PANEL_ALLOWLIST[name], payload)` (or `validateCommonMetadata` for whole-message cases) so the tests exercise the real dispatch path; note that the character fixture built from `unavailableStatusPanel()` carries `schema_version: 1` and must be bumped to `schema_version: 3` when rerouted (3.3 re-pins this at the validator level)
- [x] 3.2 Complete the `PANEL_ALLOWLIST` mirror assertions in `protocol.test.js` to cover all eight panels — `status` and `local_map` are missing today; keep the existing six assertions (context_actions ~1057, services ~2034, art ~2103, creation ~2509, exploration/character ~2919-2920)
- [x] 3.3 Add a regression test: a character unavailable payload carrying `schema_version: 3` validates through `validatePanel` with the allowlist, and the identical payload with `schema_version: 2` is rejected; add a store-level case via the store receive path (snapshot with `character` unavailable at version 3 plus a healthy `status` panel is accepted with the `status` panel intact, and the identical snapshot at version 2 is rejected with no panel replaced or merged)

## 4. Python tests (D4)

- [x] 4.1 In `web/webclient/presentation/tests/test_registry.py`, add a test asserting `build_production_registry().spec(name).schema_version` equals the imported module constant for all eight panels, and that `build_unavailable("character")` carries `schema_version: 3`; annotate the test with the literal requirement ID `webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only` (and a second test for `webclient-oob-protocol::every-panel-payload-has-an-exact-availability-discriminator` asserting the unavailable builder stamps the character registered version)
- [x] 4.2 Create `tests/test_panel_schema_version_parity_contract.py` (plain `unittest.TestCase`, no imports of game modules — top-level discovery runs without Evennia settings): for all eight panels, extract via anchored regex the registry's `schema_version=<CONST>` reference from `registry.py` (identifier-only pattern — a numeric literal must fail), the `<CONST> = N` value from the presenter module (panel → module map: `context_actions` → `combat_panel.py`, the rest are name-matched), the `name: N` value anchored to the `PANEL_ALLOWLIST` block in `protocol.js`, and the per-panel available-form re-check literal (`payload.schema_version !== N` anchored to each validator function); assert all four are equal; annotate with `covers_requirement` for both modified `webclient-oob-protocol` requirement IDs

## 5. Verification

- [x] 5.1 Run `node --test web/static/webclient/js/tests/*.test.js` and confirm the full suite passes
- [x] 5.2 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation` and `uv run --locked -m unittest discover -s tests -t .`; both pass
- [x] 5.3 Run `uv run --locked python -m tools.spec_traceability check` and confirm no main-spec requirement lost coverage
- [x] 5.4 Run `openspec validate webclient-panel-schema-version-parity --strict` and `git diff --check`; both clean
- [x] 5.5 Confirmed via `git diff` that the change touches only the files listed in the proposal (no player commands, schemas, or stored data); the managed browser suite (which exercises protocol.js end to end) remains a final-handoff run per AGENTS.md