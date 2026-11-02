# Tasks

Ground rules:
- Change only two kinds of files:
  - new `content/maps/settlements/<id>.yaml` files for the 18 roster ids;
  - `world/maps/data/district_partition.json`.
- Do not edit `content/maps/locations.yaml`.
- Keep scratch files in the scratchpad.
- Never hand-edit generated YAML.
- If the map editor has one of these documents open, ask before writing.

## 1. Baseline and plan

- [ ] 1.1 Run `check_map_sources.py` and `uv run --locked python -m tools.settlement_synthesis lint`. Check: record both results, and confirm the lint exits 0.
- [ ] 1.2 Run `uv run --locked evennia test --keepdb --settings settings.py world.maps.tests.test_bootstrap`. Check: record `Ran N tests in X s` as the D3 baseline.
- [ ] 1.3 Run `generate --missing --nation valhalla --plan-only`. Check:
  - save the output;
  - every plan reports `settlement_class` as `beast_capital` or `beast_town` and `morphology` as `tribal_ring`;
  - no plan contains the slots `academy`, `inn_lane`, `temple_forecourt`, `palace_forecourt` or `quay`;
  - list any failed location.

## 2. Generate and name

- [ ] 2.1 Run `generate --missing --nation valhalla`. Check:
  - exit 0, or 1 only for locations that failed in 1.3;
  - one new file per generated id;
  - `lint` exits 0;
  - `git diff --quiet content/maps/locations.yaml` succeeds.
- [ ] 2.2 For each generated map, in roster order:
  1. run `brief <id>`;
  2. write `<scratchpad>/prose_<id>.json` per design D2;
  3. run `prose <id> <file>`.

  Check: every `brief` shows no empty description and no duplicate key.

## 3. Verification

- [ ] 3.1 Regenerate the partition, then run `check_map_sources.py`. Check: exit 0, and partition, elevation and reference context are all current.
- [ ] 3.2 Rerun `world.maps.tests.test_bootstrap` and apply the D3 gate. Check: the gate passes. If it does not, stop, do not commit, and report.
- [ ] 3.3 Run the test labels in `grandia-settlement-maps` tasks.md 4.3, one per command. Check: all pass.
- [ ] 3.4 Capture the continent with `--hide partition`, plus the settlement views of `capital_valhalla`, `city_mutual_market` and `town_east_ford_camp`, and read the images. Check: the hand-off describes each ring layout and its gates.
- [ ] 3.5 Run `tools.contract_gate` and `openspec validate valhalla-settlement-maps --strict`. Check: both succeed. The hand-off lists any unresolved ids and the D3 numbers.

## Workflow follow-up

- After merge, the user reviews the maps in the map editor and does the fine fitting.
