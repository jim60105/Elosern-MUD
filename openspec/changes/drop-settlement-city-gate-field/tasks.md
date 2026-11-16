# Tasks

Precondition: `retire-limbo-city-gates` is archived on master, and no other in-flight
change edits `content/maps/settlements/`. Test commands follow AGENTS.md: run each
command on its own. `EV` stands for
`uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`.

## 1. Map-core (design D1)

- [ ] 1.1 Remove `city_gate` from `packages/map-core/elosern_map_core/schema.py`,
  `documents.py` and `authoring.py`, as in D1.
- [ ] 1.2 Update the map-core tests: delete gate-specific cases and drop `city_gate` keys
  from fixtures in `packages/map-core/tests/{authoring_fixtures,test_authoring,test_reference_context,test_references,test_settlement_preview,test_yaml_codec}.py`.
  Add one test (`test_yaml_codec.py` or wherever settlement schema rejection is already
  tested) where a synthetic settlement carrying `city_gate: null` is rejected with
  `unknown_field` at the path `city_gate`. Also add the same rejection test to
  `world/maps/tests/test_settlement_sources.py`, annotated with
  `map-settlement-sources::settlement-documents-own-complete-local-map-declarations`,
  because map-core pytest tests are outside the traceability scan.
  Acceptance: the map-core pytest suite (`uv run --locked python -m pytest`, run from
  `packages/map-core`) passes.

## 2. Synthesis tools (design D4)

- [ ] 2.1 Edit `tools/settlement_synthesis/generate.py` and `rework.py`.
- [ ] 2.2 Update `tests/test_settlement_map_rework.py` and
  `tests/test_settlement_terrain_fit.py`. Drop the city-gate binding from the protected
  set and from the inline documents, and keep the `settlement-map-rework` annotation on
  the "Bound identities survive" test.
  Acceptance: `uv run --locked python -m unittest tests.test_settlement_map_rework` and
  `uv run --locked python -m unittest tests.test_settlement_terrain_fit` pass.

## 3. Data (design D2)

- [ ] 3.1 Run the scratchpad strip script from D2 and do every check D2 lists. Delete
  `city_gate:` keys from the inline YAML in
  `world/maps/tests/test_settlement_reload.py` and `test_settlement_sources.py`, and the
  `self.document.city_gate` assertions in `world/maps/tests/test_village_ciaran.py`.
  Acceptance: `EV world.maps.tests.test_settlement_sources`,
  `EV world.maps.tests.test_settlement_reload` and
  `EV world.maps.tests.test_village_ciaran` pass.
- [ ] 3.2 Regenerate `world/maps/data/district_partition.json`,
  `world/maps/data/road_network.json` and `content/map-reference-context.json` in that
  order, and commit whatever changed.

## 4. Map editor (design D3)

- [ ] 4.1 Backend edits from D3. Update
  `tools/map-editor/tests/{synthetic_workspace,test_geography,test_history,test_relationships,test_settlements}.py`
  and `tests/test_map_editor_relationships.py`: delete `set_city_gate` cases and drop
  `city_gate` keys from fixtures. Add one test that the command registry has no
  `set_city_gate`. Annotate it with
  `map-editor-relationships::cross-layer-relationships-edit-one-owner-and-expose-both-meanings`.
  Acceptance: the map-editor pytest suite (`uv run --locked python -m pytest`, run from
  `tools/map-editor`) passes, and `uv run --locked python -m unittest tests.test_map_editor_relationships`
  passes.
- [ ] 4.2 Frontend edits from D3. Update
  `tools/map-editor/frontend/tests/{capture,interaction,map_scene,monster_spawns,relationships,settlement}.test.mjs`.
  Delete the `city_gate` expectations, including the `"city_gate:town"` refs in
  `settlement.test.mjs`. Acceptance: `pnpm --dir tools/map-editor/frontend test` and
  `pnpm --dir tools/map-editor/frontend run test:boundary` pass.
- [ ] 4.3 `rg -n "city_gate|cityGate|CityGate|起始房間入口" tools packages content world web`
  prints nothing.
- [ ] 4.4 Build the editor frontend as `docs/development/map-editor.md` describes, then run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_relationships`.
  Remove any step that selects `kind-city_gate`. It must pass.

## 5. Docs and gates

- [ ] 5.1 Remove the `city_gate` field from
  `docs/development/{map-authoring-documents,map-editor,metric-settlements,settlement-synthesis,sparse-settlement-graphs}.md`,
  `docs/lore/settlement-locations.md` and
  `.agents/skills/map-data-authoring/{SKILL.md,references/settlements.md}`.
- [ ] 5.2 `uv run --locked python -m tools.shard_register fix`, then
  `uv run --locked python -m tools.contract_gate --change drop-settlement-city-gate-field`.
  It must exit 0.
- [ ] 5.3 `openspec validate drop-settlement-city-gate-field --strict` passes.
