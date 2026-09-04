# Tasks — Remembered Nodes Are Map Gateways, Not Visited Ground

> Server-side only, except wave 6. Every task edits
> `web/webclient/presentation/local_map.py` or its test module unless it names
> another file. Nothing here touches `world/`, the persisted `map_knowledge`
> record, the shared validators, or the preserved UMD bundles.
>
> **Wave 6 is the flagged, strikeable addition** (proposal + design D8): the
> owner has not ruled on it. Deleting wave 6 and the ADDED requirement "The map
> surfaces state a place name only where it adds information" leaves waves 1–5
> and 7 complete and coherent.

## 1. The gateway predicate and the far-side namer

- [ ] 1.1 Add a module-level helper `_registered_gateways()` to
  `web/webclient/presentation/local_map.py` that walks
  `world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY` (deferred import, as
  every other registry read in this module is) and returns, per entry and gate,
  the triple `(approach_cell, (grid_xy, z_map_key), anchor_key)` with
  `approach_cell = entry.approach_cell(gate)`. A gate whose `approach_cell` is
  `None` is skipped, never raised on — the registry is validated at sync time and
  the panel must not go unavailable on authored data. Proof:
  `web/webclient/presentation/tests/test_local_map.py` — a unit test asserts the
  helper yields `(60, 97)`/`((2, 0), "capital_altoria")` and
  `(60, 103)`/`((2, 4), "capital_altoria")` for the shipped registry, and yields
  a point-shape entry's anchor cell as its own approach cell for a constructed
  one-`#` registry.
- [ ] 1.2 Add `_wilderness_gateway_at(x, y)` and `_grid_gateway_at(x, y, z)`
  returning the matching entry/gate (or `None`) from 1.1's table, keyed exactly
  as design D1's table states. Proof: unit tests — `(60, 103)` is a gateway,
  `(60, 104)` is not, `(2, 4, "capital_altoria")` is a gateway,
  `(2, 2, "capital_altoria")` (the plaza `AnchorRoom`) is NOT, pinning design D2.
- [ ] 1.3 Add `_gateway_far_side_label(...)` implementing design D5: the
  `ANCHOR_REGISTRY[anchor_key].display_name_zh` for a wilderness-layer gateway,
  and `_wild_region_label(*approach_cell)` for a grid-layer gateway. Proof: unit
  tests — the wilderness label for either capital gate is 「聖潔王都」 and never
  「西部丘陵與谷地」; the grid label for `北門` is the approach cell's region display
  name.
- [ ] 1.4 Add the distinctness qualifier from design D5: given the ordered list
  of remembered gateway nodes about to be emitted, any label appearing more than
  once is replaced on every colliding node by
  `f"{far_side}（{boundary_node_name}）"`, where the boundary node name is the
  gate room's `key` on the grid layer and the entry's anchor display name is
  already unique on the wilderness layer. Proof: a unit test remembers both
  capital gate rooms on the grid layer and asserts the two labels are
  「西部丘陵與谷地（南門）」 and 「西部丘陵與谷地（北門）」, distinct and each within
  `MAX_STRING_CODE_POINTS`.

## 2. The bound, the ordering, and the shared candidate filter

- [ ] 2.1 Add `MAX_REMEMBERED_GATEWAYS = 16` beside the existing bounds in
  `local_map.py`, with a comment stating it is a presenter ceiling and is
  deliberately NOT mirrored in `web/static/webclient/js/elosern/protocol.js`
  (design D6). Proof: `tests/test_panel_schema_version_parity_contract.py` still
  passes unchanged — the constant is absent from the mirrored bounds table.
- [ ] 2.2 Leave `_GraphBuilder.remembered(cap)`'s ordering contract exactly as
  shipped (descending `last_seen_tick`, then ascending `node_id`, excluding IDs
  already in the payload). Proof: the existing
  `test_graph_builder_remembered_bounds_by_last_seen` passes untouched.
- [ ] 2.3 In both coordinate-layer remembered loops, cap the emitted set at
  `min(MAX_REMEMBERED_GATEWAYS, MAX_NODES - len(builder.nodes))` and keep the
  in-view collection order (current → in-range → reserved gate capacity →
  remembered) unchanged. Proof: a test with a constructed knowledge record
  holding more gateway visits than the ceiling asserts at most 16 remembered
  nodes, the deterministic order, and that no in-view node was displaced.

## 3. The wilderness layer's remembered set

- [ ] 3.1 Replace `_wilderness_layer`'s remembered loop (`local_map.py:843`) so a
  candidate is emitted only when `decode_node` yields a `wild:` node whose
  coordinates are a registered approach cell (1.2), the node ID is present in the
  visit record, and the node is outside the drawn field of view. Proof:
  `test_local_map.py` — the rewritten
  `test_visited_cells_beyond_adjacency_become_remembered` becomes
  `test_only_stood_on_gateways_are_remembered_in_the_wilderness`: a record with
  a distant ordinary cell plus a visited approach cell yields exactly one
  remembered node, the approach cell's.
- [ ] 3.2 Emit that node at the approach cell's own wilderness coordinates, with
  1.3's wilderness label, `landmark=True`, `anchor=False`, `action=None`. Proof:
  the same test asserts `x`/`y` equal the approach cell, the label is 「聖潔王都」,
  and the three flags.
- [ ] 3.3 Add the negative case: a player whose record contains the gate room's
  `grid:` ID but not the approach cell's `wild:` ID gets no remembered node on
  the wilderness layer (design D4). Proof: a dedicated test asserting the payload
  has zero remembered nodes for that record.
- [ ] 3.4 Add the seven-chips regression test: a record seeded with eight visited
  ordinary cells of one region yields zero remembered nodes and, in particular,
  no two remembered nodes sharing a label. Proof: the delta scenario "Walked
  wilderness ground is not remembered".

## 4. The grid layer's remembered set

- [ ] 4.1 Replace `_grid_layer`'s remembered loop (`local_map.py:477`) so a
  candidate is emitted only when `decode_node` yields a `grid:` node whose
  `(x, y, z_map_key)` matches a registered gate's `grid_xy`/`z_map_key` (1.2),
  its ID is in the visit record, and it is outside visual range. Proof:
  `test_local_map.py` — a test standing at `南門` with `北門` recorded and out of
  range asserts one remembered node, the gate room's `grid:` ID.
- [ ] 4.2 Emit that node at the gate room's own grid coordinates with 1.3's grid
  label (then 1.4's qualifier), `landmark=True`, `anchor=False`, `action=None`.
  Proof: the same test asserts `x`/`y` equal `(2, 4)`, and
  `test_remembered_nodes_carry_no_action` still passes.
- [ ] 4.3 Drop a candidate whose `z_map_key` is not the map being drawn, with no
  node emitted and no probed slot (design D3). Proof: a test with a constructed
  registry gate on a second `z_map_key` asserts the node is absent and the
  payload still passes the exact validator.
- [ ] 4.4 Pin that an `AnchorRoom` alone is not a gateway: a visited plaza
  `(2, 2)` outside visual range yields no remembered node. Proof: the delta
  scenario "An in-map landmark is not a way out of the map".
- [ ] 4.5 Confirm `_interior_graph`'s remembered loop is untouched and its
  behaviour unchanged (design D7). Proof: the existing interior/instance
  remembered assertions in `test_local_map.py` pass with no edit, plus one new
  test asserting an interior payload still remembers a previously entered room.

## 5. Coordinate-space soundness and payload-contract regressions

- [ ] 5.1 Add the cross-space guard test: build a wilderness payload for a player
  who has walked through a gate (so the record holds both the approach cell and
  the gate room) and assert every `remembered` node's ID starts with `wild:` and
  carries wilderness coordinates; build the grid payload for the same record and
  assert every `remembered` node's ID starts with `grid:`. Proof: the delta
  scenario "A remembered node is never plotted from a cross-coordinate-space
  position".
- [ ] 5.2 Add a test asserting no remembered node ever lands on a
  renderer-local/probed slot: for every remembered node in a coordinate-layer
  payload, `(x, y)` equals the coordinates decoded from its own ID, and no
  remembered node shares the current node's coordinates.
- [ ] 5.3 Re-run the whole presenter suite and fix fallout in
  `web/webclient/presentation/tests/test_local_map.py`, notably
  `test_wilderness_payload_uses_provider_bounds_and_terrain_labels` (its
  non-empty-label and provider-bound assertions must still hold) and the
  worst-case serialization tests. Proof:
  `evennia test --settings settings.py web.webclient.presentation.tests.test_local_map`.
- [ ] 5.4 Update `web/tests/browser/test_browser_local_map.py`'s
  `test_remembered_remote_node_focus_shows_name_without_travel_action`: its
  fixture already records `北門 (2, 4)`, which IS a registered gate room, so the
  node survives the redefinition — but the detail line now reads the far-side
  region name instead of 「北門」, so the `assertIn("北門", detail)` assertion moves
  to the gateway's far-side label. Proof:
  `evennia test --settings settings.py web.tests.browser.test_browser_local_map`.
  Note for the implementer: `webclient-minimap-04-island-single-affordance`
  rewrites this same detail line — land whichever is later on top of the other
  rather than re-litigating the assertion.

## 6. FLAGGED / STRIKEABLE — the in-view duplicate-label rule (design D8)

> Delete this whole wave together with the ADDED requirement if the owner
> strikes it in review. Nothing in waves 1–5 or 7 depends on it.

- [ ] 6.1 In `_wilderness_layer`'s in-view neighbour loop, label a neighbour cell
  that is a registered gate approach cell (1.2) with 1.3's wilderness far-side
  name instead of its region display name, changing nothing else about the node
  (ID, action, edge, visibility, flags). Proof: `test_local_map.py` — standing at
  `(60, 104)`, the node for `(60, 103)` carries 「聖潔王都」, keeps its
  `wild:elosern:60:103` ID and its move action, and the payload passes the exact
  validator.
- [ ] 6.2 In `web/webclient-app/components/MapLattice.vue`, suppress the visible
  `<text>` content of an in-view node whose `label` string equals the `current`
  node's `label`, while keeping the `<title>` accessible name, the marker, the
  landmark treatment, `data-node`, and activation. The `current` node always
  draws its label. Proof: `web/webclient-app/tests/world/local_map.test.js` — a
  wilderness payload whose nine in-view nodes share one label renders exactly one
  visible label and nine `<title>` elements.
- [ ] 6.3 Confirm no payload field, bound, or validator changed: node labels
  stay non-empty on both sides, and neither `protocol.js` nor
  `web/static/webclient/js/elosern/local_map.js` is edited. Proof:
  `node --test web/static/webclient/js/tests/*.test.js` and
  `tests/test_panel_schema_version_parity_contract.py` pass with no edit.
- [ ] 6.4 Add the browser gate: the wilderness island shows one region name, not
  nine. Proof: `web/tests/browser/test_browser_local_map.py` — a seeded
  wilderness payload renders exactly one visible node label matching the current
  node's text.

## 7. Verification and suite gates

- [ ] 7.1 `evennia test --settings settings.py web.webclient.presentation.tests.test_local_map`
  green, with every new test carrying its `@covers_requirement` anchor on
  `webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered`
  or `webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel`
  (both titles are modified in place, so no existing anchor moves).
- [ ] 7.2 `evennia test --settings settings.py web.tests.browser.test_browser_local_map`
  and `web.tests.browser.test_browser_contextual_hud` green.
- [ ] 7.3 `npx vitest run` and `node --test web/static/webclient/js/tests/*.test.js`
  green — untouched unless wave 6 lands.
- [ ] 7.4 `tests/test_map_knowledge_contract.py` and
  `tests/test_panel_schema_version_parity_contract.py` green with no edit,
  evidencing design D9: no stored record, node grammar, or shared bound moved.
- [ ] 7.5 `openspec validate local-map-remembered-are-map-gateways --strict`
  green, and the spec-test traceability gate resolves every
  `@covers_requirement` anchor added in waves 3–6.
