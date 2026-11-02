# Tasks

Ground rules:
- Change only these files, plus residual-pin test rewrites under the doc's "Residual pin rule":
  - new `content/maps/settlements/<id>.yaml` files for the 19 roster ids;
  - `content/maps/locations.yaml` cells that the D2 rule accepts;
  - `world/maps/data/district_partition.json`.
- Never touch `content/maps/settlements/capital_altoria.yaml`.
- Keep scratch files in the scratchpad.
- Never hand-edit generated YAML.
- Ask before writing if the map editor has one of these documents open.

## 1. Baseline and plan

- [ ] 1.1 Run `check_map_sources.py` and `uv run --locked python -m tools.settlement_synthesis lint`. Check: record both, and confirm the lint exits 0.
- [ ] 1.2 Run `uv run --locked evennia test --keepdb --settings settings.py world.maps.tests.test_bootstrap`. Check: record `Ran N tests in X s` as the D4 baseline.
- [ ] 1.3 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation altoria --plan-only`. Check: save the output, list the failed locations, and confirm `capital_altoria` is absent from the output because it already has a document.

## 2. Relocations (design D2 only)

- [ ] 2.1 Apply the D2 rule to each `water_gap` failure from 1.3, in roster order. Edit only the two integers of each accepted cell. Check: rerunning the plan-only batch shows no `water_gap` except the unresolved ones, and `place_sites.py --locations` reports every Altoria location ok with nation `altoria`.

## 3. Generate and name

- [ ] 3.1 Run `generate --missing --nation altoria`. Check:
  - the exit status is 0, or 1 only when an unresolved location remains;
  - each generated id has exactly one new file;
  - `lint` exits 0;
  - `git diff --quiet content/maps/settlements/capital_altoria.yaml` succeeds.
- [ ] 3.2 For each generated map, in roster order:
  1. run `brief <id>`;
  2. write `<scratchpad>/prose_<id>.json` following design D3;
  3. run `prose <id> <file>`.

  Check: every `brief` shows no empty description and no duplicate key.

## 4. Verification

- [ ] 4.1 Regenerate the partition, then run `check_map_sources.py`. Check: it exits 0 and reports partition, elevation and reference context as current.
- [ ] 4.2 Rerun `world.maps.tests.test_bootstrap`. Check: record `X_after` for the D4 hand-off. The timing never blocks the commit.
- [ ] 4.3 Run every module in `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command. Check: every one passes. Handle a failure with that doc section's "Residual pin rule", and list every rewritten test in the hand-off. Any other failure stops the change without a commit.
- [ ] 4.4 Capture the continent with `--hide partition`, plus the settlement views of `port_white_sail`, `city_border_bridge` and one town. Read the images. Check: the hand-off describes each map's water side and gates.
- [ ] 4.5 Run `tools.contract_gate` and `openspec validate altoria-settlement-maps --strict`. Check: both succeed. The hand-off lists the relocations, the unresolved ids and the D4 numbers.

## Workflow follow-up

- After merge, the user reviews the maps in the map editor and fine-fits them.
