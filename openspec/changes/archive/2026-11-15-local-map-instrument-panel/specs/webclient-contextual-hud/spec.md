## MODIFIED Requirements

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island inside its own instrument panel in the `map` anchor, below the place card and above the objective line, carrying the committed `local_map` payload's title; the panel SHALL span the column's width like the place card. The island SHALL state no orientation marks: on the coordinate lattice (`grid`, `wilderness`) it SHALL draw the axis cross through the current node, and on the radial graph none.

#### Scenario: Omitted marks never assert an undrawn axis
- **WHEN** the resolved layout variant is the radial graph
- **THEN** the island states no orientation marks and draws no axis cross (a radial graph asserts no axis)

#### Scenario: The worded marks and the drawn axis travel together
- **WHEN** the island draws its lattice
- **THEN** the island states no orientation marks on any variant, because the minimap never rotates and a fixed north-up, east-right legend carries no information; the axis cross is the lattice's own geometry, drawn through the `current` node on the island's coordinate lattice, drawn on neither the radial graph nor the full-map surface, and never accompanied by worded marks

#### Scenario: The header follows the redesign draft's treatment
- **WHEN** the island renders on the coordinate lattice
- **THEN** its header carries the letterspaced title and the decorative open-map glyph and no orientation marks

#### Scenario: Decoration states nothing in words
- **WHEN** the lattice draws its coordinate dot field and its knowledge-edge vignette
- **THEN** they are decoration that states nothing in words and are not read as a position, a bearing, a distance, or a terrain claim: the dot field pictures the coordinate cell step the lattice already claims, and the vignette pictures the limit of what the payload knows

#### Scenario: The readout states the current cell's world coordinates alone
- **WHEN** the island renders on a coordinate-bearing layer
- **THEN** it states the `current` node's own coordinates as a two-integer figure — the payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — as the entire content of its readout line, so the island's position statement is the drawing convention plus the current cell's world coordinates and nothing else

#### Scenario: The readout never restates what other surfaces own
- **WHEN** the readout line renders
- **THEN** it does not restate the current node's place name, its visibility state, or a movement destination: the place name belongs to the stage's place card, which stands directly above this island in the same column, and a minimap shows the current position by definition

#### Scenario: Node names stay available without island selection state
- **WHEN** the player hovers or selects, or a remembered node renders
- **THEN** the readout is not driven by hover or by selection and the island keeps no hovered-node or selected-node state; a node's own name stays available as its on-canvas accessible name and, for a remembered node, as visible text on the surface its layout variant presents it on — the name drawn beside the island's edge direction marker on the coordinate lattice, and its entry in the full-map surface's remembered list on the radial graph, where the island draws no visible remembered-node list at all — with the untruncated name always available to assistive technology on the island, so no remembered place is readable by sight alone

#### Scenario: No spatial figure beyond the single coordinate pair
- **WHEN** any layer renders on the island
- **THEN** apart from that single figure the island renders no bearing angle, compass angle, distance, or other coordinate figure: coordinate readouts for non-current nodes, differences between node coordinates, and every spatial figure on the graph variant remain forbidden, because on coordinate-bearing layers node coordinates are validated world coordinates whose only permitted visual uses are relative-direction geometry and the current-node figure, and on every other layer they are renderer-local layout values that carry no spatial meaning at all

#### Scenario: Octant words exist only in the markers' text alternative
- **WHEN** the island exposes its edge direction markers to assistive technology
- **THEN** the one direction statement the island MAY make in words is the octant name an edge direction marker already draws — one of `北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北` — and only on the island's assistive-technology text alternative for those markers, where it names the bearing the drawing already asserts to a reader who cannot see it; a numeric angle, a degree figure, and a distance remain forbidden everywhere

#### Scenario: No layout control exists to persist
- **WHEN** either layout variant renders on the island or the full-map surface
- **THEN** neither presents any map layout control — no segmented switch, button, menu item, or other affordance selecting between the coordinate lattice and the radial graph — because the layout is resolved once from the committed payload's `layer` in the render model and both surfaces consume that one value, so there is nothing for a control to change; no layout choice is persisted in a client-local preference or any storage, and nothing about layout selection travels to the server, because no selection exists to persist

#### Scenario: The single full-map affordance wears no chrome
- **WHEN** the full-map surface the island opens is reachable
- **THEN** the island presents no control for a surface the application does not mount — a full-map affordance exists only once that surface is reachable — and otherwise exactly ONE full-map affordance with no visible button chrome: no labelled control, icon button, or other visible trigger occupies the island's header or any other part of the island, because the island itself is the affordance

#### Scenario: The affordance is a real full-bleed button
- **WHEN** the full-map affordance renders
- **THEN** it is a real `<button>` element spanning the island's whole box, transparent and layered beneath the island's visual content so the button element contains no focusable descendant, carrying 展開全地圖 as its accessible name and opening the full-map surface through the platform's own Enter/Space button behaviour rather than a key handler on a non-button element; its focus-visible indication delineates the whole island rather than a small region of it

#### Scenario: Every activation path opens the map exactly once
- **WHEN** the player clicks anywhere on the island's non-interactive body
- **THEN** the full-map surface still opens as a pointer convenience, provided the click did not originate in an interactive descendant, and every activation path opens the surface exactly once

#### Scenario: The island root never becomes a button
- **WHEN** the island's content changes
- **THEN** the island root gains no button role or tab-stop of its own — the full-bleed button, not the root, is the keyboard path — and `role="button"` on the island root is forbidden outright: a `role="button"` element must contain no focusable descendant and must not flatten a composite surface into one accessible name, and the island is a composite surface whose content the root would swallow; the full-bleed button remains the island's only tab stop whatever its content becomes — a remembered place's presentation is not a tab stop, on either layout variant, and is readable without being focusable — and the minimap's existing per-node movement submission is unchanged

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates and the resolved variant is the lattice
- **THEN** the island renders the map title and no orientation marks in its header, and its readout
  line states the current node's two payload coordinates as its entire content — no place name, no
  visibility-state word, no destination

#### Scenario: The stated convention and the drawn axis travel together
- **WHEN** a coordinate-bearing payload renders on the island, then a coordinate-free payload renders on
  the island, then the same coordinate-bearing payload renders on the full-map surface, which states no
  orientation marks
- **THEN** the island draws the axis cross on the lattice and nowhere else — absent on the graph and
  absent on the full-map surface — and no surface states orientation marks
- **AND** the island's coordinate dot field and knowledge-edge vignette add no word, figure, or angle to
  the island: no bearing, no distance, and no coordinate figure beyond the current node's own pair appears
  anywhere because of them

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
- **WHEN** the player activates an actionable lattice node, an edge direction marker, or the
  full-map affordance itself
- **THEN** only that control's own behavior runs — the node submits its move and no additional
  map-open is emitted, the affordance opens the map exactly once, and the marker, which carries no
  behaviour and no tab stop, lets the click fall through to the island body so the map opens exactly
  once from there

#### Scenario: A remembered place is readable on the island without a tab stop
- **WHEN** the island renders a coordinate-bearing payload carrying remembered gateways and, in turn,
  a coordinate-free payload carrying remembered rooms
- **THEN** the first draws each place's name beside its edge direction marker, the second draws no
  remembered place's name as visible text on the island and the full-map surface it opens lists each
  place's name as visible text, both islands expose every such place's untruncated name to assistive
  technology — with the marker's octant direction word on the lattice variant and no direction on the
  graph variant — and in neither case does the island offer a second tab stop beyond its full-map
  affordance

#### Scenario: The island sits under the place card at the column's width
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel
- **THEN** the minimap's instrument panel's top edge lies directly below the place card's bottom edge
  across the anchor's gap, and the panel's left and right edges coincide with the place card's (±1px)

#### Scenario: The island wears no card inside its panel
- **WHEN** an available payload renders on the island in the live client
- **THEN** the island element has no border, corner radius, box shadow, background fill or padding of its own, its panel is an instrument panel as "An instrument panel wears a feathered ground and one brass fitting instead of a box" defines, and the canvas keeps its own ink ground and its four corner brackets

#### Scenario: The canvas stands clear of the spine
- **WHEN** the island renders at 1280x720, 1451x790 and 2560x1440
- **THEN** the canvas is 240px × S square (±1px) and its right edge stands 22px × S (±1px) left of the panel's right edge, so the panel's spine runs unbroken beside it

#### Scenario: The open-map glyph answers hover and focus
- **WHEN** the pointer rests outside the island, then hovers the island, then keyboard focus enters the island's full-map affordance
- **THEN** the header's open-map glyph is dimmed (opacity below 1) at rest and fully opaque while the island is hovered or holds focus
