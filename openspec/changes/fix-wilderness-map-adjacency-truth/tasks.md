# Tasks — Fix Wilderness Map Adjacency Truth

## 1. Shared direction geometry (resolver module)

- [ ] 1.1 `world/maps/wilderness_destination.py`: rename `_DIRECTION_DELTAS` to `DIRECTION_DELTAS` (keep the literal order `n,ne,e,se,s,sw,w,nw`), add `wilderness_neighbor(x, y, direction) -> tuple[int, int] | None` applying the delta + `WILDERNESS_MAX_X/Y` bounds, export both in `__all__`, and make `resolve_wilderness_destination` use the helper for its ordinary step.
- [ ] 1.2 `web/webclient/presentation/local_map.py`: delete `_wild_neighbor` and its duplicated delta literal; import `DIRECTION_DELTAS`/`wilderness_neighbor` from the resolver module.

## 2. Wilderness layer: identity follows resolution

- [ ] 2.1 In `_wilderness_layer`, branch on `resolve_wilderness_destination`'s return: `wild:`/`None` behaves as today; `grid:` builds the node with id = resolved id, label = gate room `key` via `decode_node` xyz lookup (`GridRoom.objects.filter_xyz`), `anchor`/`landmark` = `isinstance(room, AnchorRoom)`, visibility keyed on the resolved id in the visited map, `x`/`y` = the adjacent wild cell (via `wilderness_neighbor`), action unchanged (destination already = resolved id, so `action.destination == node.id`).
- [ ] 2.2 Keep the edge `traversable` flag tied to the action and the remembered-loop filter as-is (a `grid:` visit in the remembered loop is already excluded by the `wild:` prefix filter; verify no gateway node is ever duplicated as remembered).

## 3. Grid layer: registered gate exits as nodes

- [ ] 3.1 In `_grid_layer`, collect gate candidates FIRST (`WildernessGateExit` in `location.exits` whose `db.anchor_key` is in `WILDERNESS_ENTRY_REGISTRY`, deterministic order by `dbid`), then cap `_grid_nodes_in_range`'s result at `MAX_NODES - len(candidates)` by dropping the farthest nodes first (descending Chebyshev distance, then Y, then X) before any node is added.
- [ ] 3.2 For each gate candidate compute id `encode_wild(WILDERNESS_NAME, *entry.wilderness_xy)`, label = `WILDERNESS_REGION_REGISTRY[region_for_coordinates(*xy)].display_name_zh`, visibility from the visited map, action = gate `move` descriptor (destination = that `wild:` id) when `_traversable(gate, actor)`; geometry = current position + the direction delta named by the gate exit key/aliases through `normalize_wilderness_direction` (first direction-bearing alias wins; fallback `n`); if that slot is occupied by an added node, probe the nearest free slot in ring order `(|dx|+|dy|)`, then `dy`, then `dx`; never add a duplicate id.
- [ ] 3.3 Edge from current to the gate node with the gate's normalized direction label and `traversable = action is not None`.

## 4. Hygiene (same file)

- [ ] 4.1 Remove `_grid_layer`'s dead `known_visited_ids` set and the `anchor_coord` rebuild loop (the `current_node is None` guard already precedes it; delete the now-unused import surface if any).
- [ ] 4.2 Collapse `_grid_node_label` and `_grid_coord_label` into one `_grid_room_label(coord, z)`; update both call sites (`in_range` node labels, remembered label).

## 5. Tests

- [ ] 5.1 `web/webclient/presentation/tests/test_local_map.py`: add gateway tests — entry-cell panel renders the gate `grid:` node (id, room-key label, `visible_visited` after walking in through the gate, `action.destination == node.id`) and no `wild:` node for the direction's geometric cell; gate-room panel renders the `wild:elosern:60:100` node (region label, gate `exit_ref`, action destination = the node id, drawn to the north).
- [ ] 5.2 Update the existing tests pinning the old behavior: wilderness adjacent-node label/destination tests and any grid gate-exit invisibility assumption. DELETE `test_wild_neighbor_returns_none_at_provider_edges` (it imports the removed `_wild_neighbor`); its bounds assertions move to task 5.6's resolver test.
- [ ] 5.3 Pinning anti-drift test: walk a character through the real `WildernessGateExit` and the `south` `WildernessReturnExit`, building the panel at each end, and assert every rendered gateway node's id/action destination equals the actual arrival node id (both directions).
- [ ] 5.4 Determinism tests for the D2 rules: (a) a grid room whose gate-direction slot is occupied by an in-range node — assert the payload is schema-valid AND contains both the in-range grid node and the gate node at its probed slot with its action; (b) a synthetic xymap with `MAX_NODES` in-range nodes plus a gate — assert `len(nodes) == 64`, the gate node present, payload passes `validate_local_map`.
- [ ] 5.5 `covers_requirement` anchors: keep existing anchors on updated tests; anchor the new pair-matching tests with the literal new ID `webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions`. The landing commit syncs this delta into `openspec/specs/` in the same commit (repo convention), so add the annotation together with the spec sync and keep `uv run --locked python -m tools.spec_traceability check` green at the end of the commit.
- [ ] 5.6 Resolver helper tests: `wilderness_neighbor` bounds (port the deleted `_wild_neighbor` edge assertions) + delta equality against the resolver's own ordinary-step results, in `world/maps/tests/` (existing module if present, else the module that already pins `resolve_wilderness_destination`).

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_local_map` green.
- [ ] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world` green (resolver + traversal pinning).
- [ ] 6.3 `uv run --locked python -m compileall -q world web/webclient` clean; `git diff --check` clean.
- [ ] 6.4 `openspec validate fix-wilderness-map-adjacency-truth --strict` green.
