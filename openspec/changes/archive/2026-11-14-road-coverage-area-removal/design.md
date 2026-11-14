# Design

## Context

`tools/settlement_spacing.py` (from `settlement-spacing-validation`) checks a road gap only when every cell of the gap lies in a completed area. `SpacingInput.areas`, `Area`, `load_areas`, the `--areas` option and `tools/settlement_spacing_areas.json` carry that list. After the six placement changes the file lists the five regions that have a nation: `western_hills_valleys`, `southwest_coast`, `southeast_coast`, `eastern_plains` and `northwest_highland_forest`.

Measured at planning time, no road cell lies in the two regions without a nation (`central_mountains`, `north_deep_forest`). So the only gaps the list still excludes are those that cross a boundary between two regions.

## Goals / Non-Goals

**Goals:**

- Every road gap is checked, with no list.
- The command passes on the shipped data when this change is committed.

**Non-Goals:**

- No change to the minimum-spacing rules, the placement identity rules, the exemption field or the thresholds.
- No change to the gap rule itself (design D3 of `settlement-spacing-validation`).
- No new village. A remaining gap is closed with a hamlet.

## Decisions

### D1. Removal

In `tools/settlement_spacing.py`:

- delete `Area`, `load_areas`, the `areas` field of `SpacingInput`, the `--areas` option and the `areas` parameter of `build_input`;
- in the gap rule, delete the test that every cell of a gap lies in a completed area, so every gap of every road is checked.

Delete `tools/settlement_spacing_areas.json`.

No alias and no ignored option remain: passing `--areas` is an argument error.

### D2. Tests

In `tests/test_settlement_spacing.py`:

- delete the tests of the removed requirement "Road coverage applies only inside completed areas" (inside, crossing and outside; rectangle bounds; empty list; invalid area file);
- remove the `areas` argument from the helper that builds a `SpacingInput`;
- add one test: an over-long gap whose cells lie in two different regions is reported;
- the command test drops the area file from its synthetic workspace.

The MODIFIED requirement keeps its identifier. The removed requirement's annotations are deleted with its tests; run the traceability gate with `--change road-coverage-area-removal` before the archive sync.

### D3. Remaining boundary gaps

Run `uv run --locked python -m tools.settlement_spacing` after D1. If it reports `road_gap` problems, each is a gap that crosses a region boundary. Close each by placing one hamlet on an inner cell of that road stretch, under design D2 to D7 of `valhalla-village-placement` (approval criteria, row formats, order of work, regeneration, prose), using the nation of the cell's region. Skip the area-file step of that design; the file no longer exists.

If more than 10 gaps are reported, stop and report instead: that many means an earlier placement change left its own area incomplete.

### D4. Documentation

In `.agents/skills/map-data-authoring/references/locations-and-districts.md`, section "Spacing rules for villages and hamlets": remove every sentence about completed areas and state that road coverage applies to every road.

## Risks / Trade-offs

- [A boundary gap has no valid hamlet site within the stretch] → Stop and report with the gap and the candidate cells tried. Do not add an exemption: the exemption field does not cover road gaps.
- [A new hamlet changes no road, but it changes the road artifact's signature] → Regenerate in the documented order, as every placement change does.
