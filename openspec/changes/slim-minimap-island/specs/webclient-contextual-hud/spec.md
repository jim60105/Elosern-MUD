# webclient-contextual-hud delta

## MODIFIED Requirements

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island in the stage's right anchor, beneath the top-meta
surface, carrying the committed `local_map` payload's title. Where the resolved layout variant is the
coordinate lattice — which exactly the coordinate-bearing layers (`grid`, `wilderness`) select — the
island SHALL state the renderer's own axis convention as orientation marks in its header following the
redesign draft's header treatment (the letterspaced title style and the `北↑ 東→` marks the draft's
lattice header draws); on the radial graph variant it SHALL omit those marks rather than assert an axis
the presentation does not draw (a radial graph draws no axis). While the detail line shows the `current`
node on a coordinate-bearing layer, the island SHALL additionally state that node's own coordinates as
a two-integer figure — the payload `x` and `y` exactly as committed, with no unit, delta, or derived
quantity — so the island's position statement is the drawing convention plus the current cell's world
coordinates. Apart from that single figure the island SHALL NOT render a bearing angle, a compass
angle, a distance, or any other coordinate figure: coordinate readouts for non-current nodes,
differences between node coordinates, and every spatial figure on the graph variant remain forbidden,
because on coordinate-bearing layers node coordinates are validated world coordinates whose only
permitted visual uses are relative-direction geometry and the current-node figure, and on every other
layer they are renderer-local layout values that carry no spatial meaning at all.

The island SHALL NOT present any map layout control — no segmented switch, button, menu item, or other
affordance selecting between the coordinate lattice and the radial graph — on the island or on the
full-map surface: the layout is resolved once from the committed payload's `layer` in the render model
and both surfaces consume that one value, so there is nothing for a control to change. No layout choice
SHALL be persisted in a client-local preference or any storage, and nothing about layout selection SHALL
travel to the server, because no selection exists to persist.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. Clicking anywhere on the
island's non-interactive body SHALL open the full-map surface as a pointer convenience, provided the
click did not originate in an interactive descendant; the island root SHALL NOT gain a button role or
tab-stop of its own, so the labelled control below remains the only keyboard path. The minimap's existing
per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates and the resolved variant is the lattice
- **THEN** the island renders the renderer's axis orientation marks in its draft-styled header
  alongside the map title, and while the detail line shows the current node it states that node's
  two payload coordinates

#### Scenario: A coordinate-free layer omits the legend
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure rather than asserting a
  direction or position the payload does not support

#### Scenario: The layout follows the payload without any control
- **WHEN** a coordinate-bearing payload and then a coordinate-free payload are committed, with no player
  interaction beyond movement
- **THEN** the island and the full-map surface render the lattice for the first payload and the radial
  graph for the second, the map chrome exposes no layout-control element in either state, and no
  preference or storage write occurs

#### Scenario: No compass angle or distance is rendered
- **WHEN** the minimap island renders on any layer
- **THEN** no compass angle, bearing angle, or distance appears anywhere in the island, and the only
  coordinate figure that can appear is the current node's own payload pair on a coordinate-bearing layer

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
