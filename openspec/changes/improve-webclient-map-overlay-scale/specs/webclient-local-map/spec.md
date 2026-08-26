## MODIFIED Requirements

### Requirement: The browser minimap renders states without relying on color alone
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels, SHALL allow focusing a remembered remote node to view its name/landmark without any travel action, and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

Layout SHALL be computed in the DOM-independent render model as a bounded integer lattice, not as a rescaling of payload coordinates into a fixed pixel box. The model SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on that lattice, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts. When that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The renderer SHALL size the map canvas from the exported lattice so the canvas reserves its own space **within the island's bounded height**, scaling the canvas down rather than requiring the island to scroll a required surface out of view, and SHALL NOT allow map content to overlap the island's title, its orientation legend, the state legend, the remembered-node list, the detail line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The lattice-rendering logic (node/marker placement, connector edges, per-node labels, and the state legend) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale rather than duplicated: the full-map overlay SHALL render the identical in-view nodes, edges, and legend the minimap island renders for the same committed payload, sized to the overlay surface's own available space rather than the minimap island's fixed small canvas, with the same non-overlap guarantee applying at that larger scale. The full-map overlay SHALL NOT render the `remembered` remote-node list or the hovered/selected-node detail line; both remain minimap-island-only, since selection state has no visual effect on the lattice itself and the detail line's content spans both the in-view lattice and the remembered list.

The island SHALL carry the payload's `title`. It MAY additionally state the renderer's own axis orientation as a legend on a layer whose nodes are placed on coordinates, and SHALL omit that legend on a coordinate-free layer rather than assert a direction the payload does not support. It SHALL NOT render a bearing, a compass angle, or a distance in any form: node `x`/`y` are renderer-local presentation geometry, not canonical world coordinates, and no such figure may be derived from them.

`remembered` nodes SHALL be presented as a bounded, focusable list outside the coordinate canvas, retaining their non-color state indicator and their focus-only, no-travel behavior. Their payload coordinates describe locations outside the current field of view and SHALL NOT influence the lattice. Edges SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer. The `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged.

#### Scenario: Focused remembered node offers no travel action
- **WHEN** the player focuses a remembered remote node in the minimap
- **THEN** its name and landmark are shown and there is no move or travel control for it

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (shape, border, or text label) and the
  legend text is readable

#### Scenario: Reconnect rebuilds from persisted knowledge
- **WHEN** the WebSocket reconnects and a new-epoch snapshot arrives
- **THEN** the minimap is rebuilt from the server-persisted visited record and current location, and no
  client-stored map state is treated as authoritative

#### Scenario: Unknown panel schema disables only the minimap
- **WHEN** a received `local_map` payload fails its exact schema
- **THEN** only the minimap renderer is disabled, the browser requests at most one full
  resynchronization, and narrative and text input remain usable

#### Scenario: In-view nodes occupy distinct lattice cells
- **WHEN** a grid-layer payload places several in-view nodes at distinct coordinates
- **THEN** each node occupies its own lattice cell, no two node markers overlap, and their relative row and column order matches the payload coordinates

#### Scenario: Distant remembered nodes do not distort the local view
- **WHEN** the payload carries remembered nodes many cells away from the current node
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear in the bounded list rather than on the canvas

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1440x900 and at 1280x720
- **THEN** the canvas is sized within the island's bounded height, the title, orientation legend, state legend, remembered list, and detail line remain readable, no node marker or edge overprints other island content, and no required island content has to be scrolled to

#### Scenario: The island keeps the identifier its mode gating selects on
- **WHEN** the minimap island renders after a chrome change
- **THEN** its root element still carries the stable `local-map` component identifier, and the mode whose matrix hides the minimap still removes it from the layout and from the tab order

#### Scenario: The orientation legend states only the drawing convention
- **WHEN** the committed payload's layer places nodes on coordinates
- **THEN** the island may state the renderer's axis orientation as a legend, and no bearing, compass angle, or distance figure is rendered anywhere in the island

#### Scenario: A coordinate-free layer asserts no orientation
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation legend, and the map title, legend, and detail line render exactly as on a coordinate-bearing layer

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a schema-valid payload places in-view nodes at coordinates whose span exceeds the lattice bound
- **THEN** the model falls back to rank compression, the lattice stays within its bound, and every node is still rendered exactly once

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay for a committed `local_map` payload
- **THEN** the overlay renders the identical in-view nodes, edges, and legend entries the minimap island
  renders for that same payload, sized to the overlay's own available surface rather than the minimap
  island's fixed canvas size, with no marker, label, or edge collision at the overlay's scale

#### Scenario: The full-map overlay omits the remembered-node list and the detail line
- **WHEN** the committed payload carries one or more `remembered` nodes, or a node is hovered inside the
  overlay
- **THEN** the full-map overlay does not render a remembered-node list or a hovered/selected-node detail
  line; both disclosures remain reachable only from the minimap island

### Requirement: Adjacent traversable map nodes submit explore.move through their move descriptor
The WebClient `local-map` component SHALL make a currently traversable adjacent node with an exact `move` action descriptor actionable: activating it (click or Enter on the focused node) SHALL submit the `explore.move` UI action carrying that node's opaque `exit_ref` and the canonical `current_node` identity. A node with `action: null`, a remembered remote node, or a node whose `visibility` is not a current-field-of-view state SHALL NOT submit any travel action and SHALL remain inert or focus-only exactly as before. The component SHALL derive the submitted `exit_ref` and `current_node` only from the validated `local_map` payload, SHALL NOT construct an exit reference, destination, or room identity from entity data or prose, and SHALL leave the `local_map` panel payload contract, the `未探索` unvisited-node rule, and the remembered-node no-travel rule unchanged. On a successful or rejected submission the refreshed `local_map` payload at the newer revision SHALL replace the rendered minimap; the component SHALL NOT keep a client-side canonical map cache. This activation behavior SHALL be identical whether the lattice renders inside the minimap island or inside the full-map overlay, since both consume the same shared lattice-rendering logic.

#### Scenario: Activating an adjacent traversable node submits explore.move
- **WHEN** the player focuses an adjacent traversable node whose `action` is the exact `move` object and confirms it
- **THEN** the browser submits exactly one `explore.move` envelope with that node's `exit_ref` and the panel's `current_node`, and the refreshed `local_map` payload replaces the rendered map

#### Scenario: A remembered remote node still offers no travel action
- **WHEN** the player focuses a remembered remote node (which carries `action: null`)
- **THEN** its name/landmark is shown and no `explore.move` or other travel submission is possible, matching the pre-existing rule

#### Scenario: A map node never invents a destination
- **WHEN** a node's `action` is missing, malformed, or not the exact `move` object, or the payload is rejected by its validator
- **THEN** no travel action is submitted, only the minimap renderer disables itself with the single-sync recovery path, and narrative and text input remain usable

#### Scenario: Move submission works identically from the full-map overlay
- **WHEN** the player activates an adjacent traversable node while the full-map overlay is open
- **THEN** the same single `explore.move` envelope is submitted as if the same node had been activated in the minimap island, and the overlay's rendered lattice reflects the refreshed payload
