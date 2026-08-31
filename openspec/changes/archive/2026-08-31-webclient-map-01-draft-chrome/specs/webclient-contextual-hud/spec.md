# webclient-contextual-hud delta

## MODIFIED Requirements

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island in the stage's right anchor, beneath the top-meta
surface, carrying the committed `local_map` payload's title. Where the payload's layer places nodes on
coordinates, the island MAY state the renderer's own axis convention as orientation marks in its header
following the redesign draft's header treatment (the letterspaced title style and the axis marks the
draft's map header draws); where the layer is coordinate-free, it SHALL omit those marks rather than
assert one. The island SHALL NOT render a bearing, a compass angle, a distance, or a coordinate figure
in any form: node `x`/`y` are renderer-local presentation values — on a coordinate-bearing layer they
mirror validated world coordinates, elsewhere they are layout indices — and no numeric spatial reading
may be derived from them.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. Clicking anywhere on the
island's non-interactive body SHALL open the full-map surface as a pointer convenience, provided the
click did not originate in an interactive descendant; the island root SHALL NOT gain a button role or
tab-stop of its own, so the labelled control below remains the only keyboard path. The minimap's existing
per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates
- **THEN** the island may render the renderer's axis orientation marks in its draft-styled header
  alongside the map title

#### Scenario: A coordinate-free layer omits the legend
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks rather than asserting a direction the payload does not support

#### Scenario: No bearing or distance is rendered
- **WHEN** the minimap island renders on any layer
- **THEN** no compass angle, bearing, distance, or coordinate figure appears anywhere in the island

#### Scenario: No control opens an unmounted surface
- **WHEN** the full-map surface is not mounted in the application
- **THEN** the island presents no full-map control, and the per-node movement submission continues to work unchanged

#### Scenario: Island body click opens the map without a second tab stop
- **WHEN** the player clicks the island's non-interactive body while the full-map surface is mounted
- **THEN** the full-map surface opens, the island root carries no button role and no additional tab stop,
  and the labelled expand control remains the keyboard path with its focus restore unchanged

#### Scenario: Clicking an interactive descendant does not open the map
- **WHEN** the player activates a node, a remembered-list item, or the expand control itself
- **THEN** only that control's own behavior runs and no additional map-open is emitted

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its lattice rather than as a wrapper around its
actionable nodes; the island's non-interactive body MAY additionally open the same surface on pointer
click, which SHALL NOT replace or wrap the labelled control. The command line's utility controls SHALL
open the settings and help surfaces.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale lattice or a stale reason on screen. It SHALL
present no zoom or pan affordance and SHALL NOT advertise one. It SHALL render no bearing, compass
angle, distance, or coordinate figure, on any layer.

The map surface's body SHALL carry the redesign draft's map-canvas framing (the radial-gradient dark
terrain background painted as pure CSS inside a rounded ink border), and SHALL NOT fabricate terrain
geometry the payload does not claim.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model, the quick-word chips and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the command line carries labelled controls that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement lattice, and at no point shows a lattice or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** no zoom or pan control, hint or legend entry is present, and no bearing, compass angle or distance figure appears

#### Scenario: The map surface frames the draft canvas without invented terrain
- **WHEN** the map surface renders an available payload
- **THEN** the map body shows the radial-gradient ink background inside the rounded ink frame, and no terrain, coastline, or route geometry is drawn that the payload does not carry

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference and a statement of how the game's help output is reached, and it renders no authored game-help entry and no placeholder standing in for one
