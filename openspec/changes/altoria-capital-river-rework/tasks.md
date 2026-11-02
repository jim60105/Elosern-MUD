# Tasks

Ground rules:
- Change only the files listed in proposal.md Impact, plus the residual-pin test rewrites that task 4.2 allows.
- Never rename or delete an existing Altoria node id: the D2 binding table binds all 21.
- Keep scratch files (bind and prose JSON, captures) in the session scratchpad. They are never committed.
- If the map editor is open on `capital_altoria.yaml` or `locations.yaml`, ask before writing (skill "Working alongside the editor").
- If the user has rejected design D1 option A, stop and report. Do not choose another option yourself.

## 1. Baseline

- [ ] 1.1 Run `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` and `uv run --locked python -m tools.settlement_synthesis lint capital_altoria`. Check: note the result of the first command. The second must report `fit_water_role_dry` for `quay` and `riverbank_road`, which is the known mismatch. Anything else is inherited; record it.

## 2. Relocate and regenerate

- [ ] 2.1 In `content/maps/locations.yaml`, under `capital_altoria:` → `cell:`, change `cell_x: 850` to `cell_x: 861` and `cell_y: 1024` to `cell_y: 1042`. Change nothing else. Check: `git diff --stat content/maps/locations.yaml` shows 2 changed lines, and `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/place_sites.py --locations` lists `capital_altoria` as ok, `nation=altoria`.
- [ ] 2.2 Write the D2 binding file. Run `uv run --locked python -m tools.settlement_synthesis generate capital_altoria --replace --bind <scratchpad>/altoria_bind.json --gates s,e --plan-only`. Check:
  - the report says `"morphology": "river_crossing"`;
  - it has 28 slots;
  - `bound` holds all 21 ids;
  - `dropped` is empty;
  - the slots include `ford_crossing`, `river_quay` and `riverbank`;
  - the warnings contain nothing but `footprint_location_offset`, `loop_shortfall:*` or `direction_deviation:*`. A `footprint_location_offset` warning is acceptable: record it in the hand-off.

  If the plan fails or differs, stop and report the JSON. Do not edit the binding table.
- [ ] 2.3 Run the same command without `--plan-only`. Check:
  - `git diff --stat content/maps/settlements/capital_altoria.yaml` shows the file rewritten, with its header comment lines still present;
  - `uv run --locked python -m tools.settlement_synthesis lint capital_altoria` exits 0;
  - in the written YAML, `wilderness_entry.gates` contains `return_direction: n` with `destination_node: south_gate` and `return_direction: w` with `destination_node: east_gate`;
  - `city_gate.node` is `south_gate`;
  - `uv run --locked python -m tools.settlement_synthesis site capital_altoria` lists `capital_river` within 3 cells;
  - computed with `elosern_map_core.authoring.gate_approach_cell` on the written document's geometry, the approach of the `n` gate is a cell with `cell_y < 1040`, south of the ford row. That puts it on the south bank. If it is not, stop and report.

## 3. Prose and lore doc

- [ ] 3.1 Run `uv run --locked python -m tools.settlement_synthesis brief capital_altoria` and save the output in the scratchpad. Write `<scratchpad>/altoria_prose.json` per design D3 and `docs/development/settlement-synthesis.md` § Prose pass. Apply it with `uv run --locked python -m tools.settlement_synthesis prose capital_altoria <scratchpad>/altoria_prose.json`. Check: rerunning `brief` shows `"desc_empty": false` for every node, and the node keys are unique.
- [ ] 3.2 Apply the two D4 replacements in `docs/lore/settlement-locations.md` with the Edit tool. Add this sentence to the end of the first paragraph of `docs/development/sparse-settlement-graphs.md`: "Coordinates quoted here are historical design examples; the current Altoria graph lives in `content/maps/settlements/capital_altoria.yaml`." Check: `grep -n "二十一間房\|二十六條連結\|經南大道與大道北段" docs/lore/settlement-locations.md` prints nothing.

## 4. Verification

- [ ] 4.1 Regenerate the partition with `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`, then run `check_map_sources.py`. Check: exit 0, `district partition: current`, `reference context: current`.
- [ ] 4.2 Run every module in the list in `docs/development/settlement-synthesis.md` § "Settlement-sensitive test modules" on this real data, one module per command. That section was written by `settlement-sync-cost-probe`. Check: each module passes.
  - A failure is a residual pin when two things hold: the module passes on the pre-change tree (`git stash`, rerun, `git stash pop`), and the cause is a copied settlement value such as a literal coordinate, count, duration, node key, cell or gate direction. Rewrite a residual pin in place:
    - derive the expected value from `world.maps.map_data.current().settlements[...]`, `world.maps.geography.current().locations` or `elosern_map_core.authoring.gate_approach_cell`;
    - keep the module's `@covers_requirement` IDs and its `Data-contract test:` docstring line;
    - change nothing else in the test.
  - Any other failure stops the change: report it and do not commit.
  - List every rewritten test in the hand-off.
- [ ] 4.3 Run `uv run --locked --env-file=<file containing MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb world.maps.tests.test_editor_final_yaml_adoption`. Check: it passes.
- [ ] 4.4 Capture `--view settlement --map capital_altoria --format png`, and a continent crop `--bounds 840 1025 885 1060 --hide partition --format png`, with `capture_map.py` (see skill "Seeing a map"). Read both images. Check: the hand-off describes where the quay, riverbank, ford and gates sit relative to the river.
- [ ] 4.5 Run `uv run --locked python -m tools.contract_gate` and `openspec validate altoria-capital-river-rework --strict`. Check: both succeed.

## Workflow follow-up

- The user reviews the result in the map editor (fine fitting: bends, bridge placement, district shape) after merge.
