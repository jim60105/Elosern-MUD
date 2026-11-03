# Design

## Context

See proposal.md (Why) for motivation. These are the facts the design depends on. Each was observed in the code on 2026-11-03 and in a headless agent-browser session against a private editor instance (`--port 8799`, viewport 1451x790).

- `tools/map-editor/elosern_map_editor/snapshot.py::_project` builds each `world.districts[]` row. Its landmark is `"landmark": thaw(world.districts.data["districts"][district_id]["landmark"])`, the raw authored mapping, so `cell` reaches the browser as `{"cell_x": X, "cell_y": Y}` or `None`. Every other projected cell, such as `locations[].cell`, uses `_cell(cell) -> [x, y]`.
- `frontend/src/components/ContinentInspector.vue::loadLandmark` reads `source.cell[0]` and `source.cell[1]`, so both fields show `undefined`. `landmarkDraft` compares `JSON.stringify(landmarkValue)` against the source, so it is always true for a wilderness landmark and 取消 shows at once. Fixing the projection fixes both; the inspector file is not edited.
- `frontend/src/lib/map_scene.js::continentScene` draws locations, harbour sites, fords, passes and control-point handles as `marks`. It draws no district landmark. Districts appear only in the object list (`listed`, id `district:<id>`, layer `partition`) and as derived partition outlines.
- `frontend/src/App.vue::onCanvasMove` routes a released continent drag to `continentMove(id, point)`, which returns one command descriptor or `null`. It then calls `send(descriptor).finally(settle)`. A refused command settles the mark back to the snapshot. `MapCanvas.vue` starts a drag only for a mark with `data-draggable="true"`.
- `geography.py::SetDistrictField` with `field: "landmark"` validates through `_landmark`, which requires exactly the keys `domain, map_id, object_id, cell`. `cell` goes through `_pair(..., minimum=0)`, so a negative cell is refused with 400 `invalid_command` and nothing is written. The value is stored as `{"cell_x", "cell_y"}`. Unknown references are refused as a structure diagnostic (422). Water and unreachable cells save as semantic work in progress (`unreachable_landmark`).
- The settlement node rows already carry the service-derived `world_m` (`null` while the settlement has no frame). Location rows carry `centre_m`.
- Shipped data: almost every district landmark is `wilderness_cell`, and one is `settlement_node`. Specs and tests never depend on these counts.
- Only Python tests carry `@covers_requirement` (`tools/spec_traceability.py`). Node tests under `tools/map-editor/frontend/tests/` are mechanism tests without traceability.

## Goals / Non-Goals

**Goals:**
- The service projects the landmark cell as a pair and its resolved centre.
- Every resolvable landmark is visible and selectable on the continent canvas.
- A wilderness-cell landmark can be moved by drag as one command and one undo entry that write only `districts.yaml`.
- The map-data-authoring skill documents that path.

**Non-Goals:**
- No new placement tool button and no click-to-place mode. Drag plus the existing numeric inspector is the whole surface.
- No changes to the domain (reference vs. cell) by drag. Converting a referenced landmark into a wilderness cell stays a deliberate act in the inspector's 領域 selector.
- No client-side placement validation: no spacing, sea, region or reachability checks and no disabled-drop UI. Rejection belongs to the service and diagnostics belong to the core.
- No new continent layer, no capture CLI flag change, no partition regeneration, no map-core or game change.
- No keyboard nudge for landmarks. The inspector's numeric fields are the non-drag path the existing requirement already demands.

## Decisions

### D1. Service projects `landmark` normalized plus `landmark_centre_m`

In `snapshot.py`, add two module-level helpers next to `_cell` and use them in the district rows of `_project`:

```python
def _landmark(landmark) -> dict[str, Any]:
    """The qualified landmark reference with its cell as an ``[x, y]`` pair."""

    return {
        "domain": landmark.domain,
        "map_id": landmark.map_id,
        "object_id": landmark.object_id,
        "cell": None if landmark.cell is None else _cell(landmark.cell),
    }


def _landmark_centre_m(landmark, location_cells, node_world_m) -> list[int] | None:
    """The landmark's continental centre in metres, derived from its referent.

    A wilderness cell is its cell centre, a location is its location cell's
    centre, and a settlement node is that node's derived world position.
    An interior room, an unknown referent, or a node whose settlement has no
    frame yet has no continental position.
    """

    if landmark.domain == "wilderness_cell" and landmark.cell is not None:
        return [int(value) for value in cell_center_m(landmark.cell)]
    if landmark.domain == "location" and landmark.object_id in location_cells:
        return [int(value) for value in cell_center_m(location_cells[landmark.object_id])]
    if landmark.domain == "settlement_node":
        return node_world_m.get((landmark.map_id, landmark.object_id))
    return None
```

Wiring inside `_project`:
- Before the settlements loop, declare `node_world_m: dict[tuple[str, str], list[int] | None] = {}`. Inside the existing per-node loop, after `world_m` is computed, store `node_world_m[(settlement_id, node_id)] = None if world_m is None else [int(world_m[0]), int(world_m[1])]`. This is the same value the node row's `"world_m"` gets.
- Before the `"districts"` list, build `location_cells = {location_id: location.cell for location_id, location in world.locations.locations.items()}`.
- In each district row, replace the `thaw(...)` landmark with `"landmark": _landmark(district.landmark),` and add `"landmark_centre_m": _landmark_centre_m(district.landmark, location_cells, node_world_m),` directly after it.

Field contract (JSON, per `world.districts[]` row):

```text
landmark:          {domain: str, map_id: str|null, object_id: str|null, cell: [int, int] | null}
landmark_centre_m: [int, int] | null
```

Rationale: the frontend rule is that every coordinate comes from the service (`map_scene.js` header). Resolving the referent server-side keeps that rule and makes the centre testable in a real-process test. Alternative rejected: resolving in `map_scene.js` from `locations[].centre_m` and `nodes[].world_m`. It would work, but it duplicates a join the service already owns and cannot be covered by a traceable Python test.

`district.landmark` is the core's `QualifiedRef`, and `landmark.cell` is indexable as `cell[0]`, `cell[1]`. `elosern_map_core.authoring._candidate_protected_cells` already reads it that way.

### D2. Landmark marks reuse the district reference and live on the `locations` layer

In `map_scene.js::continentScene`, insert one mark per district with an array centre as the **first** spread entry of the `marks` array literal, before the `world.locations.map(...)` entry. SVG draws later marks on top. Landmarks therefore sit underneath locations, sites, fords, passes and handles, and every existing mark keeps its current hit area. This matters because a settlement-node landmark lies a few pixels from its settlement's location mark, and existing location-drag tests start their drag near that edge:

```js
...(world.districts ?? [])
  .filter((district) => Array.isArray(district.landmark_centre_m))
  .map((district) => ({
    id: districtRef(district.id),
    kind: "landmark",
    label: district.landmark_name_zh,
    role: district.landmark?.domain === "wilderness_cell" ? "landmark" : "landmark-linked",
    layer: "locations",
    draggable: district.landmark?.domain === "wilderness_cell",
    ...point(district.landmark_centre_m),
  })),
```

Change the `items` line to keep one object-list entry per district: the `listed` district rows stay unchanged, and landmark marks are excluded from the mark-derived part.

```js
const items = [
  ...listed,
  ...marks.filter((mark) => mark.kind !== "landmark").map((mark) => ({ id: mark.id, label: mark.label, layer: mark.layer })),
];
```

Rationale:
- The mark id equals `district:<id>`. A click therefore selects the district through the existing `objectCatalog`, `ContinentInspector` and OMP-context paths, with no new reference grammar.
- `locations` is the layer for authored placement points (locations and harbour sites). `partition` is labelled 衍生・唯讀 and an existing test requires that no mark sits on it.

A landmark hidden under a location mark stays selectable: pick it through the object list (`分區 …`) or the inspector, and the mark then shows `map-mark--selected`. Wilderness landmarks rarely share a pixel with another mark.

Alternative rejected: a new `district_landmark:<id>` reference. It would need catalog, inspector, deletion and context-copy support for no user-visible gain.

### D3. Drag routing builds one full wilderness reference

In `continent.js`, add next to `districtField`:

```js
export const wildernessLandmark = (cell) => ({ domain: "wilderness_cell", map_id: null, object_id: null, cell });
```

In `App.vue::continentMove`, add this branch after the `site` branch and before the `location` lookup:

```js
if (parsed?.kind === "district") {
  const district = (world.value.districts ?? []).find((row) => row.id === parsed.id);
  if (!district || district.landmark?.domain !== "wilderness_cell") return null;
  const cell = cellOfMetres(world.value, point);
  return sameStored(district.landmark.cell, cell) ? null : districtField(district.id, "landmark", wildernessLandmark(cell));
}
```

Import `districtField` and `wildernessLandmark` from `./lib/continent.js` if they are not already imported.

Layer toggle: `App.vue::toggleLayer` prunes a selected continent ref that is missing from the visible scene's `items`. Landmark marks are not in `items` (D2), so hiding 分區 would drop a district selected through its mark even though the mark still draws on 地點. Replace its `visible` line with:

```js
const visible = new Set([...(next?.items ?? []), ...(next?.marks ?? [])].map((mark) => mark.id));
```

Every non-landmark mark id is already in `items`, so this changes nothing else.
 A non-wilderness landmark is never draggable (D2), and this guard makes a stray event a no-op. A negative cell from dropping west or south of the frame goes to the service and is refused, and the existing `.finally(settle)` returns the mark to its saved position. This is the server-side rejection path. No client check is added.

### D4. Glyph and theme

In `MapSurface.vue`, add a `v-else-if="mark.kind === 'landmark'"` branch before the final `v-else`:

```vue
<template v-else-if="mark.kind === 'landmark'">
  <circle r="16" class="map-mark__hit" />
  <circle v-if="chosen.has(mark.id)" r="14" class="map-mark__ring" />
  <path d="M0 -7 L7 0 L0 7 L-7 0 Z" class="map-mark__landmark" />
  <text v-if="mark.showLabel !== false" y="-14" class="map-mark__label">{{ mark.label }}</text>
</template>
```

In `editor.css`, after `.map-mark--location-bare .map-mark__dot`:

```css
.map-mark__landmark {
  fill: var(--gold-300);
  stroke: var(--ink-820);
  stroke-width: 1.5;
}

.map-mark--landmark-linked .map-mark__landmark {
  fill: none;
  stroke: var(--gold-300);
}
```

Only existing tokens are used, and the label reuses `.map-mark__label` (`--text-xs`, already at or above the 16px floor under the editor's UI scale). No new font size is introduced.

### D5. Skill and docs

- `.agents/skills/map-data-authoring/SKILL.md`, "Add or move a district" recipe: an author can drag a wilderness-cell landmark's gold diamond on the continent canvas (地點 layer). The drag is one `set_district_field` landmark command that writes only `districts.yaml`. Referenced landmarks (hollow diamond) follow their referent and do not drag. Afterwards, run the check, run `place_sites.py --landmarks --min-km 100` for Voronoi spacing, and regenerate the partition. The "Placing sites" section lists `--landmarks`.
- `references/locations-and-districts.md`, "Editor equivalents": the drag path, the four-key wilderness value it writes, the non-draggable domains, the 400 refusal for negative cells, and that sea or unreachable cells save as diagnosed work in progress. Also note that the editor projection exposes `landmark.cell` as `[x, y]` and `landmark_centre_m`, while the YAML keeps `{cell_x, cell_y}`.
- `references/verification.md`: the capture layer table row for `continent` / `locations` becomes "locations, reserved harbour sites and district landmarks".
- `scripts/place_sites.py`: add `--landmarks` to the mutually exclusive source group. `_authored_landmarks(root)` returns `[{"id": f"district:{key}", "cell": list(row.landmark.cell)} for key, row in sorted(world.districts.districts.items()) if row.landmark.domain == "wilderness_cell" and row.landmark.cell is not None]`. It then flows through the same `_evaluate` pool and report as `--locations`. Update the module docstring usage block and the paragraph that describes `--locations`.
- `docs/development/map-editor.md`: in the projection paragraph, document `landmark.cell` as a pair and `landmark_centre_m`. In the continent tools paragraph, document the landmark drag and that referenced landmarks do not drag.

### D6. Verification split

- Mechanism (traceable): the real-process test in `tests/test_map_editor_geography.py` checks the projection, the one-owner write and the refusal. The Playwright test in `web/tests/browser/test_map_editor_geography.py` checks mark selection, the drag, undo, reload, the persisted cell, the non-draggable referenced mark, and a refused off-frame drop that returns the mark to its saved position. Until archive sync, both carry the nearest current canonical ID, `map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls`, because an ADDED requirement has no canonical ID before sync. At archive they are re-mounted to the ID that `tools.spec_traceability list` generates for the new requirement.
- Scene logic (untraced): Node tests in `frontend/tests/continent.test.mjs`.
- Human-reviewed (not tested): the agent-browser screenshots from task 5 at 1451x790 and 2560x1440 are the review document for glyph legibility, label clutter at overview zoom, and fidelity to the ink/gold theme. Store them under the worker's scratchpad, attach them in the apply report, and do not commit them.

## Risks / Trade-offs

- [Many labels at continent overview add clutter] → Labels reuse the existing `showLabel` path. The human reviewer judges clutter from the task 5 screenshots. A follow-up may add label LOD, which is out of scope here.
- [A landmark mark sits on or near a location mark] → Landmark marks draw first (D2), so existing marks keep their hit areas and the location-drag workflow test is unaffected. A covered landmark is selected through the object list. The browser test drags and clicks `synthetic_north` at cell (3, 25), where no other mark exists. It selects the covered `synthetic_district` landmark through the object list. Task 3.2 re-runs the location-drag workflow tests.
- [The offline capture renders the same scene, so its continent mark count grows] → `web/tests/browser/test_map_capture_surface.py::continent_mark_count` adds resolvable landmarks (task 3.2).
- [Changing the projected `landmark.cell` shape breaks a consumer] → The frontend readers (`relations.js`, `settlement.js`, `interior.js`, `diagnostics.js`) read only `domain`, `map_id` and `object_id`. `ContinentInspector.vue` expects the pair. Python tests read `landmark["object_id"]` from the projection, and `landmark["cell"]` only from the YAML file. The full `pnpm --dir tools/map-editor/frontend test` and `tools/map-editor` pytest runs in task 4 confirm this.
- [A drag converts nothing but still triggers a partition-stale state] → Expected. Any district change stales the partition, as documented in the skill.
