# Proposal

## Why

District landmarks (`content/maps/districts.yaml` → `districts.<id>.landmark`) seed the world-map district partition, but the standalone map editor never draws them on the continent canvas, so an author cannot see or move one where it sits. The only way to change one is the inspector's structured landmark selector. Browser inspection of the running editor (agent-browser, 1451x790, 2026-11-03) found that selector broken for wilderness-cell landmarks: the 東向格/北向格 fields read `undefined` and a draft is open as soon as a district is selected. The cause is that the service projects the authored cell as a `{cell_x, cell_y}` mapping, while the inspector reads it as an `[x, y]` pair.

## What Changes

- The service's workspace projection gives each district landmark a normalized `cell` (`[x, y]` or `null`, the same pair shape every other projected cell uses) and a new derived `landmark_centre_m` (`[east_m, north_m]` or `null`). The centre comes from the landmark's referent: a wilderness-cell landmark uses its cell centre, a location landmark uses its location's cell centre, and a settlement-node landmark uses that node's `world_m`. An interior-room landmark, or any referent that does not resolve, gets `null`.
- The continent scene draws one landmark mark per district that has a non-null centre, on the existing 地點 (`locations`) layer. Clicking a mark selects its district (`district:<id>`), so the existing district inspector opens.
- Dragging a **wilderness-cell** landmark mark is one `set_district_field` command on release. It carries the full four-key wilderness reference with the dropped cell, writes only `districts.yaml`, makes one undo entry, and leaves the partition stale. Landmarks that reference a location or a settlement node are drawn but are not draggable, because they follow their referent. The editor never swaps a reference for a coordinate.
- No new client-side validation. A cell the service refuses (for example a negative cell) snaps back to the saved position through the existing refusal path and banner. A saveable but unfinished placement (sea, unreachable, `invalid_spacing`, `region_mismatch`) saves and shows up as a semantic diagnostic, as the numeric path already does.
- The inspector's numeric landmark entry shows the authored cell again, because it now receives the `[x, y]` pair it expects.
- `.agents/skills/map-data-authoring/` documents the new editor path: SKILL.md, `references/locations-and-districts.md` and `references/verification.md` describe landmark drag, its single-owner write, which domains are draggable, and that continent captures now include landmark marks on the `locations` layer. `scripts/place_sites.py` gains a `--landmarks` mode that re-checks every authored wilderness-cell landmark after a move.
- `docs/development/map-editor.md` records the new projection fields and the landmark drag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-editor-geography`: adds a requirement that district landmark positions are projected and drawn on the continent canvas, and that wilderness-cell landmarks are moved by drag as one owner-only command.

## Impact

- Service: `tools/map-editor/elosern_map_editor/snapshot.py` (`_project` district rows). Command handling in `geography.py` (`SetDistrictField`, `_landmark`) is reused unchanged.
- Frontend: `tools/map-editor/frontend/src/lib/map_scene.js` (`continentScene`), `src/lib/continent.js` (new `wildernessLandmark` descriptor helper), `src/App.vue` (`continentMove`), `src/components/MapSurface.vue` (landmark glyph), `src/styles/editor.css` (gold-on-ink landmark styles from the existing theme tokens, no new font sizes). `ContinentInspector.vue` is fixed by the projection change alone and is not edited.
- Tests: `tools/map-editor/frontend/tests/continent.test.mjs`, `tests/test_map_editor_geography.py` (real process), `web/tests/browser/test_map_editor_geography.py` (Playwright drag, reload and persistence).
- Skill and docs: `.agents/skills/map-data-authoring/**`, `docs/development/map-editor.md`.
- Game runtime, map-core schema, the partition algorithm and authored map data are unchanged. No data migration.
- Human-reviewed, not tested: the visual legibility of the landmark glyph and its labels against the ink/gold theme at 1451x790 and 2560x1440. This is reviewed through the agent-browser screenshots that `design.md` names. The skill's prose quality is also reviewed by a person.
- In-flight changes (`regional-*`, `actual-live-population-view`, `manual-monster-compositions`, `whole-cell-field-engagement`, `combat-individual-identity`, `regional-ecology-authoring`) touch none of these files. No ordering constraint.
