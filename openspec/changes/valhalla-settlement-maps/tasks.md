# Tasks

Ground rules:
- Change only these files, plus residual-pin test rewrites under the doc's "Residual pin rule":
  - new `content/maps/settlements/<id>.yaml` files for the 18 roster ids;
  - `content/maps/districts.yaml` landmark cells that design D4's generator
    precondition accepts;
  - `content/maps/locations.yaml` cells that design D4 accepts;
  - current-tense documentation statements that count the mapped settlements;
  - `world/maps/data/district_partition.json`.
- Do not edit any other `content/maps/locations.yaml` cell.
- Keep scratch files in the scratchpad.
- Never hand-edit generated YAML.
- If the map editor has one of these documents open, ask before writing.

## 1. Baseline and plan

- [x] 1.1 Run `check_map_sources.py` and `uv run --locked python -m tools.settlement_synthesis lint`. Check: record both results, and confirm the lint exits 0.
  Baseline: `check_map_sources.py` exited 0 ("game-ready as far as static checks can tell") with 14 pre-existing `footprint_location_offset` advisories and a current partition; `lint` reported `fit: 0 errors, 0 warnings`.
- [x] 1.2 Run `uv run --locked evennia test --keepdb --settings settings.py world.maps.tests.test_bootstrap`. Check: record `Ran N tests in X s` as the D3 baseline.
  Recorded `Ran 50 tests in 1249.146s`, but that run is not usable as a baseline: the source edits landed while it was running, so two tests observed `stale_partition` and the timing is contaminated. The authoritative final-tree run is task 3.2.
- [x] 1.3 Run `generate --missing --nation valhalla --plan-only`. Check:
  - save the output;
  - every plan reports `settlement_class` as `beast_capital` or `beast_town` and `morphology` as `tribal_ring`;
  - no plan contains the slots `academy`, `inn_lane`, `temple_forecourt`, `palace_forecourt` or `quay`;
  - list any failed location.
  Baseline tree: 8 plans, 10 refusals (7 `location cell not walkable` own-landmark collisions, 3 `anchor_outside_footprint`). After design D4's approved remedies the same batch plans all 18 with exit 0 and no failed location; every plan is `beast_capital`/`beast_town` with `tribal_ring` and none carries a forbidden slot.

## 2. Generate and name

- [x] 2.1 Run `generate --missing --nation valhalla`. Check:
  - exit 0, or 1 only for locations that failed in 1.3;
  - one new file per generated id;
  - `lint` exits 0;
  - `git diff --quiet content/maps/locations.yaml` succeeds.
  Exit 0, exactly 18 new documents, one per roster id, `lint` 0 errors and 0 warnings. The `locations.yaml` diff holds only the three cells design D4 accepts.
- [x] 2.2 For each generated map, in roster order:
  1. run `brief <id>`;
  2. write `<scratchpad>/prose_<id>.json` per design D2;
  3. run `prose <id> <file>`.

  Check: every `brief` shows no empty description and no duplicate key.
  All 18 briefs show `desc_empty: true` before the pass, as generated. 174 nodes carry prose afterwards, every description non-empty and every key unique within its map; keys are 2-8 characters and no description names the settlement more than once.

## 3. Verification

- [x] 3.1 Regenerate the partition, then run `check_map_sources.py`. Check: exit 0, and partition, elevation and reference context are all current.
  `check_map_sources.py` exited 0 with "district partition: current", "wilderness elevation: current", "reference context: current", 0 cross-file problems and 15 advisories (the 14 inherited plus `town_stag_ferry`'s generated footprint offset).
- [x] 3.2 Rerun `world.maps.tests.test_bootstrap`. Check: record `X_after` for the D3 hand-off. The timing never blocks the commit.
  `Ran 50 tests in 1868.346s`, OK, on the final tree.
- [x] 3.3 Run every module in `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command. Check: all pass. Handle a failure with that doc section's "Residual pin rule", and list every rewritten test in the hand-off. Any other failure stops the change without a commit.
  Every label in the list ran on the final tree and passed; nothing was rewritten under the residual pin rule, so there is no rewritten-test hand-off. Batches stayed under the 100-discovered-test guard and ran with `--parallel 8 --noinput`, except the editor module. Results: primer `test_altoria_capital` 12; `typeclasses` exit pair 39; discovery + npc dialogue 65; webclient actions + `test_area_map` 97 (skipped=1); presentation part one 65; presentation part two 86; lore 76; maps part one 44; maps part two 69; wilderness trio 75; editor adoption 4; quest compile trio 87; quest scene set 87; quest definition pair 77; quest dispatch/story trio 64; rules lifecycle + guild 73; party follow pair 55; movement trio 74; party time + sight 79; travel plan + command help 44 (skipped=1). `tests.test_map_core_contract` under `python -m unittest` ran 4 with the documented standalone `ImproperlyConfigured` error in `test_game_adapters_read_their_declarations_through_the_core`; the other 3 passed.
- [x] 3.4 Capture the continent with `--hide partition`, plus the settlement views of `capital_valhalla`, `city_mutual_market` and `town_east_ford_camp`, and read the images. Check: the hand-off describes each ring layout and its gates.
  The capital is a radial ring: the plaza at the centre, four gates at S, SE, SW and NW with approach roads converging on it, the tribal hall and assembly ground east, the market west, the craft alley north and the ancestral altar far east. `city_mutual_market` is a compact two-cell town with a north gate toward the inland hills and a southwest gate on the 界橋城 road, its market and training ground south of the plaza. `town_east_ford_camp` is a six-node camp with its south gate on the ford and a northwest gate on the 獵鷹鎮 road, the market east of the plaza.
- [x] 3.5 Run `tools.contract_gate` and `openspec validate valhalla-settlement-maps --strict`. Check: both succeed. The hand-off lists any unresolved ids and the D3 numbers.
  `contract_gate` passed all six parts (reference-context up to date, 2693/2693 requirements covered, observability 0 violations, test-data 0 violations, manifests, 19 contract tests). `openspec validate --strict` reports the change valid with `skip_specs` accepted. No unresolved id. D3: baseline unusable per 1.2, final `50 tests / 1868.346s`.

## Workflow follow-up

- After merge, the user reviews the maps in the map editor and does the fine fitting.
