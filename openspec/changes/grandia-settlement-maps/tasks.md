# Tasks

Ground rules:
- Change only these files, plus residual-pin test rewrites under the doc's "Residual pin rule":
  - new `content/maps/settlements/<id>.yaml` files for the 22 roster ids;
  - `content/maps/locations.yaml` cells that the D2 rule accepts;
  - `world/maps/data/district_partition.json`.
- Keep scratch JSON and images in the scratchpad.
- Never hand-edit generated YAML. Use `prose`, and for anything else stop and report.
- Ask before writing if the map editor has one of these documents open.

## 1. Baseline and plan

- [ ] 1.0 Read `docs/development/settlement-synthesis.md` § Runtime cost. Check: its decision word is **proceed**. If it is **blocked** or missing, stop without changing anything and report.
- [ ] 1.1 Run `check_map_sources.py` and `uv run --locked python -m tools.settlement_synthesis lint`. Check: record both results. The lint must exit 0, because Altoria was fixed by `altoria-capital-river-rework`.
- [ ] 1.2 Run `uv run --locked evennia test --keepdb --settings settings.py world.maps.tests.test_bootstrap` once. Check: record its `Ran N tests in X s` line as the D4 baseline.
- [ ] 1.3 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation grandia --plan-only`. Check: save the output. List every location whose plan failed, and the morphology of `capital_grandia`.

## 2. Relocations (design D2 only)

- [ ] 2.1 Apply the D2 rule to each trigger from 1.3, in roster order, editing only the two integers of each accepted cell in `content/maps/locations.yaml`. Check: rerunning `generate --missing --nation grandia --plan-only` has no `water_gap` except the reported unresolved ones. `place_sites.py --locations` reports every Grandia location as ok with nation `grandia`.

## 3. Generate and name

- [ ] 3.1 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation grandia`. Check:
  - exit 0, or 1 only for the locations reported unresolved in 2.1;
  - one new file per generated id;
  - `uv run --locked python -m tools.settlement_synthesis lint` exits 0.
- [ ] 3.2 For each generated map, in roster order:
  1. run `brief <id>` and save it;
  2. write `<scratchpad>/prose_<id>.json` per design D3;
  3. run `prose <id> <file>`.

  Check: for every generated map, `brief` shows no `"desc_empty": true` and no duplicate key within the map.

## 4. Verification

- [ ] 4.1 Regenerate the partition, then run `check_map_sources.py`. Check: exit 0, with partition, elevation and reference context all `current`.
- [ ] 4.2 Rerun `world.maps.tests.test_bootstrap` as in 1.2 and apply the D4 gate. Check: `X_after ≤ 2.5 × X_baseline` and `X_after ≤ 600`. Otherwise stop, do not commit, and report.
- [ ] 4.3 Run every module in `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command, and also `uv run --locked python -m unittest tests.test_map_authoring_contract tests.test_map_partition_independence`. Check: all pass. Handle a failure with the "Residual pin rule" in that same doc section, and list every rewritten test in the hand-off. Any other failure stops the change without a commit.
- [ ] 4.4 Capture a continent overview with `--hide partition` and the settlement views of `capital_grandia`, `port_golden_sheaf` and one town. Read the images. Check: the hand-off describes each map's water side and gates.
- [ ] 4.5 Run `uv run --locked python -m tools.contract_gate` and `openspec validate grandia-settlement-maps --strict`. Check: both succeed. The hand-off lists every relocation, every unresolved location and the D4 numbers.

## Workflow follow-up

- The user reviews the maps in the map editor and does the fine fitting after merge.
