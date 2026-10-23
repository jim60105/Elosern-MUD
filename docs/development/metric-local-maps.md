# Metric local maps and uniform projection

`project-metric-local-maps` cuts the `local_map` transport and client renderer
over to physical coordinates. The wire payload carries canonical
server-authoritative coordinates; the browser projects them at one uniform
physical scale. The property that matters for play is that unequal distances
stay unequal on screen: two nodes 100 m apart and two nodes 900 m apart draw at
a 1:9 ratio at every zoom, and the ratio never changes per axis.

## Unit and ownership contract

| Layer | Unit | Owner |
| --- | --- | --- |
| Settlement node coordinates | integer metres in the settlement's local frame (`x` east, `y` north) | `world/maps/` (room lifecycle), declared by the settlement graph |
| Wilderness node coordinates | integer one-kilometre cell indices (`0 <= x, y < 2700` once rescaling lands) | `world/maps/wilderness_provider.py` |
| `local_map` payload `x`/`y` | those same integers, unchanged | `web/webclient/presentation/local_map/` |
| Lattice cell in the browser | the smallest positive in-view coordinate delta, one divisor for both axes | `web/static/webclient/js/elosern/local_map.js::layoutNodes` |
| Canvas placement | presentation only (`col`/`row` × pitch) | `web/webclient-app/composables/use-map-lattice-geometry.js` |

`z` stays the logical grid/layer key; it is never physical elevation. Interiors
without coordinates stay coordinate-free connected scenes: their payload keeps
`room:` identities and the radial graph layout, and no metre position is
invented for them.

## Wire envelope

Both validators share one exact envelope and enforce it identically:

- `web/webclient/presentation/local_map/validate.py`: `COORD_MIN = -10_000_000`,
  `COORD_MAX = 10_000_000`.
- `web/static/webclient/js/elosern/protocol/constants.js`:
  `LOCAL_MAP_COORD_MIN`/`LOCAL_MAP_COORD_MAX`, consumed by
  `protocol/panels/local_map.js::requireCoord`.

The envelope is a transport bound, not a rendering bound and not a statement
about any map's extent. A `grid:` identity still resolves against the
registered extent of its own `z_map_key`
(`world/rules/map_knowledge._registered_grid_bounds`), and a `wild:` identity
still resolves against the provider frame; widening one never widens the
other. Non-integer, non-finite, boolean and numeric-string coordinates remain
rejected, so the renderer never receives invented geometry.

The on-demand `area_map` and `world_map` drawer panels reuse the same
coordinate envelope but have their own schemas, frames and bounds. See
[map-panel-protocol.md](map-panel-protocol.md). The `local_map` minimap keeps
its existing 65,536-byte budget.

## Projection

The `local_map` model keeps every in-view node at its payload coordinates.
The minimap island projects them itself (`lib/minimap_projection.js`): an
exit-driven uniform scale or a monotone compressed one, with exact bearings
except bounded overlap spreading, inside its fixed 240-unit square. Payload
coordinates are never rewritten by the projection.

The full map is the map drawer (redesign-map-drawer): its area tab draws the
on-demand `area_map` at one uniform metre scale and its world tab the
`world_map` in kilometres, both through `lib/map_viewport.js`. The old
full-map overlay and its lattice (`cellSize`, col/row cell units, the
overlay pitch fit and fitted view) were removed with it.

`remembered` nodes stay off the canvas: on coordinate-bearing layers they are
named edge-direction markers derived from the **raw** payload delta, and they
keep the same bearing at any projection scale. Coordinate-free layers keep the
radial graph and its text alternative.

## Verification

```sh
node --test web/static/webclient/js/tests/local_map.test.js \
  web/static/webclient/js/tests/protocol_local_map.test.js

pnpm exec vitest run \
  web/webclient-app/tests/world/local_map.test.js \
  web/webclient-app/tests/world/map_drawer.test.js \
  web/webclient-app/tests/world/map_lattice_fidelity.test.js \
  web/webclient-app/tests/world/map_lattice_renderer.test.js \
  web/webclient-app/tests/world/map_lattice_name_fit.test.js

uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb \
  web.webclient.presentation.tests.test_local_map
```

The browser acceptance path is
`web/tests/browser/test_browser_local_map_lattice.py`
(`test_metric_projection_keeps_gap_ratio_and_actions`): it injects a metric
payload into the real client and checks automatic island projection and the
adjacent node's move identity. Uniform area gap ratios belong to
`tests/world/area_map_view.test.js`; drawer navigation and memory belong to
`tests/world/map_drawer.test.js`.

### Drawer cutover assertion ownership

The canonical identifiers below come from `tools.spec_traceability list` on
the complete equivalent merged-spec tree for `redesign-map-drawer`. The five
retired mixed overlay requirements have no aliases in implementation tests.
These short labels are documentation references only:

| Label | Canonical identifier |
| --- | --- |
| Island presentation | `webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure` |
| Island movement | `webclient-local-map::minimap-adjacent-movement-remains-bound-to-authoritative-descriptors` |
| Drawer navigation | `webclient-map-drawer::map-keyboard-and-pointer-interaction-remains-modal-and-accessible` |
| Drawer memory | `webclient-map-drawer::the-map-drawer-opens-the-appropriate-scope-and-preserves-session-views` |
| Drawer chrome | `webclient-map-drawer::floating-map-chrome-avoids-selected-details` |
| Drawer current | `webclient-map-drawer::the-drawer-current-marker-makes-one-truthful-position-claim` |
| Font measure | `webclient-local-map::the-shipped-font-manifest-is-the-single-source-of-the-map-cell-measure` |

Each retained browser method below keeps its substantive island assertions.
The file names are relative to `web/tests/browser/` unless otherwise stated.

| Assertion owner before cutover | Retained role and replacement |
| --- | --- |
| `test_browser_local_map_geometry.py::test_minimap_content_stays_inside_its_island` | Island presentation, fixed bounds |
| `test_browser_local_map_geometry.py::test_island_type_ladder_stays_under_its_own_chrome_step` | Island presentation, label hierarchy |
| `test_browser_local_map_geometry.py::test_mirrors_are_clipped_non_focusable_and_do_not_change_island_box` | Island presentation, full-name alternative |
| `test_browser_local_map_interaction.py::test_adjacent_traversable_node_submits_explore_move` | Island movement, exact descriptor |
| `test_browser_local_map_interaction.py::test_gateway_exit_stub_is_a_named_keyboard_button_moving_once` | Island presentation and existing gateway requirement, named keyboard control |
| `test_browser_local_map_interaction.py::test_minimap_pointer_events_blank_canvas_opens_overlay_while_actionable_moves` | Island presentation, drawer disclosure versus movement |
| `test_browser_local_map_lattice.py::test_densely_populated_lattice_scales_down_without_reintroducing_overlap` | Island presentation, fixed canvas and retained model; obsolete overlay pass removed |
| `test_browser_local_map_lattice.py::test_long_remembered_list_never_resizes_the_island` | Island presentation, fixed canvas and full names |
| `test_browser_local_map_lattice.py::test_metric_projection_keeps_gap_ratio_and_actions` | Existing metric requirement and Island movement; uniform drawer ratios move to area-view tests |
| `test_browser_local_map_layout_variants.py::test_layout_follows_payload_layer_without_any_control` | Island presentation, data-selected layout |
| `test_browser_local_map_layout_variants.py::test_walked_instance_layer_renders_radial_on_both_surfaces` | Island presentation for radial island; real radial area drawing covered by area-view tests and Drawer Dungeon/Interior plays |
| `test_browser_local_map_rendering.py::test_minimap_renders_and_distinguishes_states_without_color` | Island presentation, non-colour state ladder |
| `test_browser_local_map_rendering.py::test_remembered_remote_node_presentation_and_accessibility` | Island presentation, remembered-name disclosure |
| `test_browser_local_map_rendering.py::test_unknown_nodes_never_appear_in_the_dom` | Island presentation, knowledge boundary |
| `test_browser_local_map_rendering.py::test_reconnect_rebuilds_minimap_from_persisted_knowledge` | Island presentation, server-owned knowledge |
| `test_browser_shell_surfaces.py::test_minimap_present_in_exploration_absent_in_combat` | Island presentation and existing mode visibility requirement |
| `tests/test_mono_cells_table.py::test_regeneration_reproduces_the_committed_block` | Font measure, generated cell table |
| `web/webclient/tests/test_node_suite_evidence.py::test_local_map_lattice_node_suite_passes` | Island presentation, executed model assertions |
| `web/webclient/tests/test_node_suite_evidence.py::test_local_map_island_vitest_evidence_passes` | Island presentation plus unchanged chrome, metric, gateway and naming identifiers |
| `web/webclient/tests/test_node_suite_evidence.py::test_island_label_placement_vitest_evidence_passes` | Island presentation and unchanged chrome identifier |
| `web/webclient/tests/test_node_suite_evidence.py::test_map_lattice_island_renderer_vitest_evidence_passes` | Island presentation and unchanged chrome identifier |

The removed full-map assertions have these explicit replacements:

| Removed assertion | Replacement |
| --- | --- |
| `test_overlay_renders_scale_note_as_neutral_info_entry` | Drawer chrome and navigation, real legend popover and scale bar; the old `local_map.legend` overlay-only note is retired |
| `test_full_map_opens_fitted_zooms_pans_and_recentres` | Drawer memory/navigation unit assertions and `MapDrawerWalkTests`; viewport projection remains in its existing capability |
| `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas` | Drawer chrome, `map_edge_pointers.test.js` and OverflowPointers play; the overlay remembered-marker gutter no longer exists |
| `test_full_map_marks_the_current_place_once` | Drawer current, area ring/connector assertions in `map_drawer.test.js` and real current-marker checks in the managed drawer class |

The four modified inherited titles keep their canonical identifiers. Their
island assertions retain automatic projection, label floors, gateway names
and scale-aware motion. Their former full-map lattice clauses are replaced
by the independent area/world/viewport/drawer contracts, rather than applied
to a second `local_map` renderer.
