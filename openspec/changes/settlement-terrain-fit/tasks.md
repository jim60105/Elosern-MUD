# Tasks

Ground rules:
- Create or edit only the files a task names.
- Do not touch `content/`, `world/`, `packages/`, `tools/map-editor/` or any existing test. The new test may load `tools/map-editor/tests/synthetic_workspace.py` by file path, and that is the only use of that directory.
- Copy every signature, constant and rule from design.md D1–D5 verbatim. Do not invent new parameters.
- No numpy, scipy or new dependency. Standard library and `elosern_map_core` only.
- Do not add `@covers_requirement` decorators for `settlement-terrain-fit::*`. Those IDs do not exist until archive (see Workflow follow-up).
- Run top-level tests as one standalone command: `uv run --locked python -m unittest tests.test_settlement_terrain_fit`. Use no pipes or redirects.

## 1. Geometry and terrain view

- [ ] 1.1 Create `tools/settlement_synthesis/__init__.py`. It contains a single module docstring, "Read-only settlement site analysis, size budget and terrain-fit lint (settlement-terrain-fit)." Create `tools/settlement_synthesis/geometry.py` with exactly the D1 `geometry.py` contents, plus `from __future__ import annotations` and `import math`. Check: `uv run --locked python -c "from tools.settlement_synthesis.geometry import bearing; print(bearing(3,0), bearing(0,-20), bearing(-1,1), bearing(0,0))"` prints `e s nw None`.
- [ ] 1.2 Create `tools/settlement_synthesis/terrain_view.py` with the D1 `GridTerrain` dataclass and its five methods. Check: in a `python -c` snippet, a 3×3 window with `land` = all cells except `(0,0)` and `inland_water={(1,1)}` gives these results: `is_sea((0,0))` True, `is_water((1,1))` True, `walkable((1,1))` False, `walkable((2,2))` True, `contains((5,5))` False.

## 2. Site context

- [ ] 2.1 Create `tools/settlement_synthesis/site.py` with `SettlementRef`, `WaterContact`, `PointFeature`, `SiteContext` and `analyse_site`, following the D1 rules exactly. Import `NATIONAL_KINDS` from `budget.py`, so do task 3.1 first or in the same sitting.
- [ ] 2.2 Create `tests/test_settlement_terrain_fit.py` with class `SiteContextTests(unittest.TestCase)` covering the four scenarios of the "Site context" requirement. All fixtures are in-memory `GridTerrain` values over window `(0,0,20,20)`.
  - **River contact:** a river `r` with route `((13,20),(13,0))` and `waterway_cells` x=13, y=0..20. Assert distance 3, bearing `e`, downstream `s`.
  - **Sea:** `land` = cells with x≥7. Assert sea distance 4 and bearing `w`. Use a second window with no sea and no river to assert `rivers == ()` and `sea is None`.
  - **Uphill:** bands = y. Assert uphill `n` and relief 6 for `relief_radius=3` (bands 7..13 around y=10). With all bands equal, assert uphill None and relief 0.
  - **Neighbours and capital bearing:** a roster of a capital at (10,16) with the same nation (6 cells away), a town `nb_b` at (2,10) and a city `nb_a` at (18,10), both 8 cells away, plus an `elven_village` at (11,11). Assert:
    - the order is the capital, then `nb_a`, then `nb_b`, because the tie at 8 is broken by id;
    - the village is excluded;
    - `capital_bearing == "n"`;
    - for the capital's own site, `capital_bearing is None`.

  Use synthetic ids such as `site_a` and `cap_x`. Check: `uv run --locked python -m unittest tests.test_settlement_terrain_fit` passes.

## 3. Size budget

- [ ] 3.1 Create `tools/settlement_synthesis/budget.py` with the D1 contents and rules: `NATIONAL_KINDS`, `Tier`, `BudgetConfig` (with `__post_init__` validation), `DEFAULT_BUDGET`, `SizeBudget`, `BudgetError` and `size_budget`.
- [ ] 3.2 Add `SizeBudgetTests` covering the four scenarios. Every case uses a synthetic `BudgetConfig`, never `DEFAULT_BUDGET`:
  - **Exponent:** reference 10,000, 100/ha, exponent 0.5; population 40,000 gives area `== 2.0`, footprint 2 and radius `round(1000*math.sqrt(2/math.pi))`.
  - **Floor:** choose populations giving 0.3 km² and 3.2 km² with exponent 1.0, so area is linear. The footprints are 2 and 4.
  - **Tier boundaries:** a synthetic table `(Tier(100,5,3,0.5), Tier(0,3,2,0.1))`. Population 99 gives 3 nodes, 100 gives 5 and 101 gives 5. A `capital` kind at population 1 gets the synthetic `capital_tier`.
  - **Rejection:** `elven_village`, `dungeon`, population 0 and population None each raise `BudgetError`, and the message contains the location id.
  - **Config validation:** `BudgetConfig(... min_footprint_cells=1 ...)` raises `ValueError`.

  Check: the module passes.

## 4. Terrain-fit lint

- [ ] 4.1 Create `tools/settlement_synthesis/fit_lint.py` with the D4 contents and the full rule table. Build road polylines from `road.source`, each `(bend.x_m, bend.y_m)` and `road.destination`, converted with `world_position`. Get the footprint geometry with `document.wilderness_geometry(location_cell)`. Treat `None` as "no footprint checks".
- [ ] 4.2 Add a test helper `_document(nodes, roads, shape, offset, gates)` that builds a `SettlementDocument` with `elosern_map_core.codec.document_from_data("content/maps/settlements/fit_case.yaml", data)`. `data` uses `id: fit_case`, `location_ref: fit_place`, `city_gate: None` and the given parts. Every node carries every field: `key` non-empty, `desc` `""`, `typeclass` None, `scene_archetype` None.
- [ ] 4.3 Add `WaterAndCrossingLintTests` covering the three scenarios.
  - Use a window `(0,0,20,20)` with all land. Inland water is the column x=12, y=0..20, except a ford at (12,5). Put the location cell at (10,10) and the anchor node at local (2000,500), which is world (10500,10500). Set `wilderness_entry` to `None`, so no footprint checks run.
  - **Water edge:**
    - a `quay` node at local (3200,500) is world (11700,10500), 300 m from the cell x=12 edge at 12000, so it is not reported;
    - a `riverbank_road` node at local (2000,1500) is world (10500,11500), 1,500 m from that edge, so it is reported.
  - **Crossings:**
    - a plain-node road across x=12 at y≈10 is reported;
    - the same road from a `bridge` node is not reported;
    - a road crossing at y=5, over the ford cell, is not reported.
  - **Whole words:** `words("quayside")` has no water word, and `words("old_ford_lane")` contains `ford`.
- [ ] 4.4 Add `FootprintAndGateLintTests` covering the three scenarios.
  - The two-cell footprint is `["##"]` at offset (0,0), at cell (10,10) and (11,10).
  - **Containment and water:** a node at (9,10), an adjacent land cell, is reported outside. A node in the water cell (12,10) is reported in water.
  - **Gate side:** a gate with `return_direction: w` (outward `e`) targets a node west of the anchor, which gives a `warning`. A second gate's approach cell is in `impassable`, which gives an `error`.
  - **Point entry:** the same nodes with shape `["#"]` give no containment and no gate-side findings, and the water node is still reported.
- [ ] 4.5 Add `DirectionDriftLintTests`. One source node has three roads whose first segment points due east. Note that the schema forbids two outgoing roads with the same direction from one node, so use three source nodes. The roads are authored `e`, `ne` and `n`. Only the `n` road yields `fit_direction_drift`, at severity `warning`, and the `document.data` before and after are equal. Check: the module passes.

## 5. Workspace adapter, CLI and command tests

- [ ] 5.1 Create `tools/settlement_synthesis/workspace.py` (D5) and `tools/settlement_synthesis/__main__.py`. The CLI uses argparse subcommands `site`, `budget` and `lint`, with the D5 output formats and exit codes. Check: `uv run --locked python -m tools.settlement_synthesis budget capital_altoria` prints JSON with `"footprint_cells": 13` and `"node_count": 28`, and `uv run --locked python -m tools.settlement_synthesis site port_white_sail` prints a river contact named `capital_river`. These shipped-data checks are manual evidence only. Never put them in a test.
- [ ] 5.2 Run `uv run --locked python -m tools.settlement_synthesis lint`. Check: it exits 1 and reports `fit_water_role_dry` for `capital_altoria` `quay` and `riverbank_road`, which is the known mismatch. It reports no `fit_node_outside_footprint` for `capital_altoria`. If it does, record the ids in the hand-off for `altoria-capital-river-rework`. `git status --porcelain` is unchanged by the run.
- [ ] 5.3 Add `CommandTests`. Load `synthetic_workspace` by file path, the same way `tests/test_map_image_capture.py` `_load` does. Then:
  - (a) Write the workspace, run `lint --root tmp` and expect exit 0, with an unchanged `tree_digest`.
  - (b) Add a node `quay` at local (300,0) to `synthetic_town`. Write it back with `synthetic_workspace.yaml_text`, plus a road pair `gate`→`quay` direction `e` and `quay`→`gate` direction `w`. Expect exit 1 and an output line containing `fit_water_role_dry synthetic_town quay`.
  - (c) Make `synthetic_town.yaml` a duplicate-key YAML. Expect exit 2.
  - (d) Write a `--lore` file `{"synthetic_place": {"nation": null, "population": 20000}}`. `budget synthetic_place --root tmp --lore f` exits 0 with JSON containing `footprint_cells`. `site synthetic_place --root tmp --lore f` exits 0 and lists river `synthetic_river`. `site no_such_place` exits 2.

  Every run leaves `tree_digest` unchanged. Check: the module passes.
- [ ] 5.4 Add `"tests.test_settlement_terrain_fit"` to the `labels` list of shard `index` 4 in `.github/top-level-shards.json`. Check: `uv run --locked --env-file=<file containing MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` passes.

## 6. Documentation

- [ ] 6.1 Create `docs/development/settlement-synthesis.md` in English with these sections:
  - "Scales": D3, verbatim in substance;
  - "Size budget": the D2 assumptions with their sources, the illustrative table, and a note that the capitals are explained constraints;
  - "Site context" and "Terrain-fit lint": the rule table from D4, with codes;
  - "Commands": D5;
  - "Human review": a checklist. Does a 2-cell town and a 13-cell capital look right on the continent capture? Do walking times between gates and plaza feel right for the tier? Is the density anchor acceptable?

  Check: the file exists and every lint code in D4 appears in it.
- [ ] 6.2 Edit `.agents/skills/map-data-authoring/references/settlements.md`. Add a section "Terrain fit and size" after "Wilderness entry (footprint and gates)". It explains the scale rule (D3), the water-edge and crossing words, and the `site`, `budget` and `lint` commands, and links `docs/development/settlement-synthesis.md`.
- [ ] 6.3 Edit `.agents/skills/map-data-authoring/references/verification.md`. Under "Commands", add the three commands in the game environment. Note that the lint is read-only, exits 0, 1 or 2, and that `capital_altoria` fails it until its rework lands.
- [ ] 6.4 Edit `.agents/skills/map-data-authoring/SKILL.md`. In "Workflow" step 3 (Check), add a bullet: "after any settlement edit, also run `uv run --locked python -m tools.settlement_synthesis lint <map_id>` and fix its errors (warnings are review prompts)". Use the Edit tool, not a shell heredoc. The test guard rejects files whose text contains test commands written through the shell. Check: `grep -n "settlement_synthesis lint" .agents/skills/map-data-authoring/SKILL.md` prints a line.

## 7. Gates

- [ ] 7.1 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`. Check: all exit 0.
- [ ] 7.2 Run `openspec validate settlement-terrain-fit --strict`. Check: it prints `is valid`.

## Workflow follow-up

- At archive, after the delta syncs into `openspec/specs/settlement-terrain-fit/spec.md`, decorate each test class's test methods with `@covers_requirement("<ID>")` using the design D6 mapping, and rerun `tools.spec_traceability check` (expect `0 uncovered`).
