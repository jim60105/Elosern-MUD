# webclient-contextual-hud delta

## MODIFIED Requirements

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island in the stage's right anchor, beneath the top-meta
surface, carrying the committed `local_map` payload's title. Where the resolved layout variant is the
coordinate lattice — which exactly the coordinate-bearing layers (`grid`, `wilderness`) select — the
island SHALL state the renderer's own axis convention as orientation marks in its header following the
redesign draft's header treatment (the letterspaced title style and the `北↑ 東→` marks the draft's
lattice header draws); on the radial graph variant it SHALL omit those marks rather than assert an axis
the presentation does not draw (a radial graph draws no axis). On a coordinate-bearing layer the island SHALL additionally state the
`current` node's own coordinates as a two-integer figure — the payload `x` and `y` exactly as
committed, with no unit, delta, or derived quantity — as the entire content of its readout line, so
the island's position statement is the drawing convention plus the current cell's world coordinates
and nothing else. The readout SHALL NOT restate the current node's place name, its visibility state,
or a movement destination: the place name belongs to the shell's own top-meta location surface, and a
minimap shows the current position by definition. The readout SHALL NOT be driven by hover or by
selection, and the island SHALL keep no hovered-node or selected-node state; a node's own name stays
available as its on-canvas accessible name and, for a remembered node, as the visible text of the
presentation its layout variant gives it — the name drawn beside its edge direction marker on the
coordinate lattice, its list entry on the radial graph — with the untruncated name always available
to assistive technology, so no remembered place is readable by sight alone. Apart from that single figure the island SHALL NOT render a bearing angle, a compass
angle, a distance, or any other coordinate figure: coordinate readouts for non-current nodes,
differences between node coordinates, and every spatial figure on the graph variant remain forbidden,
because on coordinate-bearing layers node coordinates are validated world coordinates whose only
permitted visual uses are relative-direction geometry and the current-node figure, and on every other
layer they are renderer-local layout values that carry no spatial meaning at all. The one direction
statement the island MAY make in words is the octant name an edge direction marker already draws — one
of `北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北` — and only on the island's assistive-technology
text alternative for those markers, where it names the bearing the drawing already asserts to a reader
who cannot see it; a numeric angle, a degree figure, and a distance remain forbidden everywhere.

The island SHALL NOT present any map layout control — no segmented switch, button, menu item, or other
affordance selecting between the coordinate lattice and the radial graph — on the island or on the
full-map surface: the layout is resolved once from the committed payload's `layer` in the render model
and both surfaces consume that one value, so there is nothing for a control to change. No layout choice
SHALL be persisted in a client-local preference or any storage, and nothing about layout selection SHALL
travel to the server, because no selection exists to persist.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. The island SHALL present
exactly ONE full-map affordance, and it SHALL carry no visible button chrome — no labelled control,
icon button, or other visible trigger occupies the island's header or any other part of the island,
because the island itself is the affordance. That affordance SHALL be a real `<button>` element
spanning the island's whole box, transparent and layered beneath the island's visual content so the
button element contains no focusable descendant, carrying 展開全地圖 as its accessible name and opening
the full-map surface through the platform's own Enter/Space button behaviour rather than a key handler
on a non-button element. Its focus-visible indication SHALL delineate the whole island rather than a
small region of it. Clicking anywhere on the island's non-interactive body SHALL still open the
full-map surface as a pointer convenience, provided the click did not originate in an interactive
descendant, and every activation path SHALL open the surface exactly once. The island root SHALL NOT
gain a button role or tab-stop of its own — the full-bleed button, not the root, is the keyboard path
— and `role="button"` on the island root is forbidden outright: a `role="button"` element must contain
no focusable descendant and must not flatten a composite surface into one accessible name, and the
island is a composite surface whose content the root would swallow. The full-bleed button SHALL remain
the island's only tab stop whatever its content becomes: a remembered place's presentation SHALL NOT
be a tab stop, on either layout variant, and SHALL be readable without being focusable. The minimap's
existing per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates and the resolved variant is the lattice
- **THEN** the island renders the renderer's axis orientation marks in its draft-styled header
  alongside the map title, and its readout line states the current node's two payload coordinates as
  its entire content — no place name, no visibility-state word, no destination

#### Scenario: The readout ignores hover and selection
- **WHEN** the player hovers and then activates a non-current node on a coordinate-bearing layer
- **THEN** the readout line still states only the current node's coordinate figure, no coordinate
  figure appears for the hovered or activated node, and the island holds no hovered-node or
  selected-node state

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
- **THEN** the full-map surface opens exactly once, the island root carries no button role and no
  additional tab stop, and the island's full-bleed transparent button remains the keyboard path with
  its focus restore unchanged

#### Scenario: The island's single affordance wears no visible chrome
- **WHEN** an available payload renders on the island while the full-map surface is mounted
- **THEN** exactly one full-map affordance exists, it is a `<button>` spanning the island's whole box
  with 展開全地圖 as its accessible name, no labelled or icon full-map control is rendered in the
  island's header or anywhere else in the island, and the island root carries no `role="button"`

#### Scenario: A keyboard user reaches the full map from the island
- **WHEN** a keyboard user tabs into the island and presses Enter, and repeats the run with Space
- **THEN** each press opens the full-map surface exactly once through the button element's own
  behaviour, the focus-visible indication while it is focused delineates the whole island, and closing
  the surface restores focus to that same still-present element

#### Scenario: Clicking an interactive descendant does not open the map
- **WHEN** the player activates an actionable lattice node, an edge direction marker, a
  graph-variant remembered-list item, or the full-map affordance itself
- **THEN** only that control's own behavior runs — the node submits its move and no additional
  map-open is emitted, the affordance opens the map exactly once, and the marker and the remembered
  item, which carry no behaviour and no tab stop, let the click fall through to the island body so the
  map opens exactly once from there

#### Scenario: A remembered place is readable on the island without a tab stop
- **WHEN** the island renders a coordinate-bearing payload carrying remembered gateways and, in turn,
  a coordinate-free payload carrying remembered rooms
- **THEN** the first draws each place's name beside its edge direction marker and the second lists each
  place's name beneath the canvas, both expose every such place's untruncated name to assistive
  technology with the marker's octant direction word on the lattice variant, and in neither case does
  the island offer a second tab stop beyond its full-map affordance
