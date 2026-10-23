# Spec Delta

## REMOVED Requirements

### Requirement: The browser minimap renders states without relying on color alone
**Reason**: The old shared-overlay contract is retired by the area/world drawer cutover; retained minimap behavior and new full-map behavior have explicit replacement requirements.
**Migration**: Remap each substantive assertion to the replacement minimap requirements below or to webclient-map-drawer, webclient-map-viewport and the area/world view requirements according to its actual assertion role. Remove obsolete overlay-only assertions, never retain retired IDs or aliases.

### Requirement: Adjacent traversable map nodes submit explore.move through their move descriptor
**Reason**: The old shared-overlay contract is retired by the area/world drawer cutover; retained minimap behavior and new full-map behavior have explicit replacement requirements.
**Migration**: Remap each substantive assertion to the replacement minimap requirements below or to webclient-map-drawer, webclient-map-viewport and the area/world view requirements according to its actual assertion role. Remove obsolete overlay-only assertions, never retain retired IDs or aliases.

### Requirement: The legend renders beyond-state entries as neutral info chips
**Reason**: The old shared-overlay contract is retired by the area/world drawer cutover; retained minimap behavior and new full-map behavior have explicit replacement requirements.
**Migration**: Remap each substantive assertion to the replacement minimap requirements below or to webclient-map-drawer, webclient-map-viewport and the area/world view requirements according to its actual assertion role. Remove obsolete overlay-only assertions, never retain retired IDs or aliases.

### Requirement: The full-map surface opens fitted to its body and offers zoom, pan, and recentre
**Reason**: The old shared-overlay contract is retired by the area/world drawer cutover; retained minimap behavior and new full-map behavior have explicit replacement requirements.
**Migration**: Remap each substantive assertion to the replacement minimap requirements below or to webclient-map-drawer, webclient-map-viewport and the area/world view requirements according to its actual assertion role. Remove obsolete overlay-only assertions, never retain retired IDs or aliases.

### Requirement: Current map location has one unambiguous footprint
**Reason**: The old shared-overlay contract is retired by the area/world drawer cutover; retained minimap behavior and new full-map behavior have explicit replacement requirements.
**Migration**: Remap each substantive assertion to the replacement minimap requirements below or to webclient-map-drawer, webclient-map-viewport and the area/world view requirements according to its actual assertion role. Remove obsolete overlay-only assertions, never retain retired IDs or aliases.

## ADDED Requirements

### Requirement: Minimap presentation retains local knowledge and readable drawer disclosure
The minimap SHALL retain the completed automatic projection, exit labels, gateway controls, graph layout, non-colour states, fixed canvas, token typography, remembered-name alternatives and single drawer-opening affordance. It SHALL render local_map only; the drawer SHALL use area_map/world_map rather than a shared legacy lattice. Unknown nodes SHALL stay absent and full permitted names SHALL remain readable through drawer text disclosure.

#### Scenario: Remembered names stay readable across truncation and graphics
- **WHEN** a remembered remote name is truncated, absent from visible island text or drawn in a graphic
- **THEN** its untruncated name remains in the island text alternative and is disclosed as visible text in the map drawer; coordinate-bearing remembered names also retain their named directional markers

#### Scenario: Reconnect rebuilds from server-persisted knowledge
- **WHEN** the WebSocket reconnects and the new epoch's snapshot arrives
- **THEN** the component rebuilds the map from the server-persisted knowledge in that snapshot, and no client map cache is authoritative

#### Scenario: The island is a bounded constant-size HUD anchored on the stage
- **WHEN** the component renders
- **THEN** it renders as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column
- **AND** the island SHALL have a constant size that no payload changes: a single 1px hairline frame, a padding no larger than the shared spacing scale's smallest step, a single-row header, a square map canvas of 240 CSS px on each side at the 1451x790 reference scale, multiplied once by the desktop chrome factor above the reference height, and a readout row that always reserves its one line

#### Scenario: The island never sizes itself from its surroundings
- **WHEN** the island lays out at any anchor size or payload
- **THEN** the island SHALL NOT stretch to its anchor's width, SHALL NOT measure its anchor or any other surface to size itself, and SHALL NOT draw a second frame around its canvas inside its own frame

#### Scenario: The island root keeps the identifier the shell selects on
- **WHEN** the shell's mode-gated visibility rules or its focus-rescue path select the island
- **THEN** the island's root element SHALL keep the stable `local-map` component identifier both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it

#### Scenario: Map visual language comes from design tokens
- **WHEN** the island present the redesign draft's map visual language
- **THEN** every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value
- **AND** node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far)

#### Scenario: The marker shape ladder holds at both scales
- **WHEN** the island renders visibility or a gateway
- **THEN** current/visited/unvisited/remembered retain non-colour distinction, gateway nodes have their gate glyph and graph glyph semantics are unchanged

#### Scenario: Each surface declares its label type steps
- **WHEN** a surface draws node labels or marker names
- **THEN** each surface SHALL declare its own node-label type size, and that size SHALL NOT resolve to drawn text larger than the surface's own smallest chrome type step, so a node label can never out-weigh the island's own title at any payload
- **AND** the island declares a 16-unit node-label step — equal to its 16px chrome step — and a 16-unit marker-name step; the drawer declares its own readable screen-space type steps

#### Scenario: A fitted drawing never shrinks text below its declared step
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The coordinate-field layers are inert decoration
- **WHEN** the island renders coordinate-field layers
- **THEN** they are pointer-inert, excluded from accessibility, lack node classes/data identities and use tokens; uniform dots follow world anchors, compressed rings replace dots and motion follows the effective preference

#### Scenario: The coordinate dot field states the lattice's coordinate space
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A dot never reads as a fifth node state
- **WHEN** the dot field renders beside the marker ladder
- **THEN** the dot's radius SHALL scale with the marker ladder and SHALL remain strictly and materially smaller than the smallest node marker's radius, it SHALL carry no stroke, no label, and no state class, and the state legend SHALL gain no entry for it, so the legend's four states stay closed exactly as the beyond-state note rule requires

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The axis cross follows the stated convention
- **WHEN** a surface considers drawing the axis cross
- **THEN** it SHALL draw a full-width and full-height axis line through the `current` node's drawn position ONLY where that same surface states the axis convention in words; a surface that states no orientation marks SHALL draw no axis, and the radial graph variant SHALL draw none on the island because a graph asserts no axis
- **AND** the axis SHALL be drawn beneath every node marker — it necessarily passes through the `current` node's own marker, which is what an origin is, and that crossing SHALL NOT be read as a violation of the non-overlap invariant, whose axis clause governs the edge direction markers in the gutter band

#### Scenario: Decoration contrast is pinned in a band against the ground
- **WHEN** the dot field and the axis render against the canvas ground
- **THEN** each SHALL be present as a painted element whose resolved colour differs from the canvas ground; each SHALL keep a contrast ratio against that ground of at least 1.15:1 at every point of the canvas and at least 1.35:1 within the vignette's un-darkened inner field; and neither SHALL exceed the contrast that the connector-edge ink itself keeps against the same ground, so the coordinate decoration never reads louder than the topology it decorates
- **AND** these layers are decoration, not information: the coordinate claim they picture is carried redundantly by the node placement itself, by the header's axis orientation marks, and by the readout's coordinate figure, so no reader depends on them — but the lattice's geometry is its claim, so they SHALL NOT be invisible

#### Scenario: The render model exports two placements
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Automatic island placement stays bounded under scale compression
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The radial placement is deterministic and edge-honest
- **WHEN** the model computes the radial placement
- **THEN** it SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas
- **AND** ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates
- **AND** the radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant is constructible from the model alone
- **AND** neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning

#### Scenario: Surfaces declare a fixed square canvas or a fitted view
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A fixed square canvas never magnifies
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The lattice fill grows pitch before taking margin
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The graph fill is a readable window
- **WHEN** a fixed-square graph variant fills its square
- **THEN** the fixed square window SHALL be centred on the radial placement's current node at one CSS pixel per user unit, clipping oversized radial drawings rather than shrinking their labels, and the complete graph and every full name SHALL remain reachable on the full-map surface

#### Scenario: No cap ever sizes a canvas
- **WHEN** the renderer resolves canvas dimensions
- **THEN** it SHALL accept no maximum-width or maximum-height cap and SHALL NOT resolve any cap into a width bound: no surface sizes its canvas by a cap, so there is no definite width to reconcile against a height cap and no engine-specific replaced-element constraint resolution can letterbox or distort a drawing
- **AND** the canvas's own natural size SHALL NOT be able to breach the island's square however much the edge-marker gutter grows it: the gutter enlarges the drawing's required side, which the square window absorbs as clipping, never as a larger canvas or smaller text

#### Scenario: The island measures nothing and overlaps nothing of its own
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: No marker or label footprint ever intersects another
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The pitch is derived from what needs clearing
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The bare clearance term binds every adjacent pair
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The vertical term clears labels above markers
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The label term measures visible names in monospace cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The label term never binds on undrawn labels
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The derived pitch is a floor, bought without truncation
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The square cell keeps drawing and bearings in agreement
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Only the full-map surface renders the state legend
- **WHEN** the island and map drawer render
- **THEN** the island mounts no state legend; the drawer owns its accessible legend popover for area/world facts

#### Scenario: The layout follows the data, never a setting
- **WHEN** a map surface presents its layout
- **THEN** no map surface SHALL offer a layout switch or any other means for the player to choose a layout, and no layout choice SHALL be kept as a preference or in any client-side storage: the layout follows the data the world ships, not a setting

#### Scenario: The header stays one row at every title length
- **WHEN** the island carries the payload's `title`, server-authored and bounded only by the payload's 128-code-point ceiling
- **THEN** its header SHALL stay a single row at every authored title length as a localization-safe container: the title SHALL be the row's only elastic item — rendered on one line, truncated with an overflow indicator when it does not fit, and keeping its complete string available as the element's own tooltip/accessible text — while the orientation marks and every other header item SHALL be fixed-size items that neither shrink nor wrap
- **AND** no authored or translated title SHALL be able to reflow the header onto a second line, and the island's card SHALL keep its constant width rather than being sized by its widest row, so neither the card's width nor the canvas's is a function of the title's length

#### Scenario: The header carries no full-map control
- **WHEN** the island's header is composed
- **THEN** it SHALL carry no full-map control of its own: the island's single full-map affordance is the full-bleed element specified below, so the header's fixed-size items are the orientation marks and nothing else unless a later change adds one

#### Scenario: Orientation marks appear only on the lattice variant
- **WHEN** the island renders a payload
- **THEN** on the lattice variant — which exactly the coordinate-bearing layers select — the island SHALL state the renderer's own axis orientation as orientation marks in its header and SHALL omit those marks otherwise rather than assert a direction or an axis the presentation does not support (a radial graph asserts no axis)

#### Scenario: Node coordinates carry layer-scoped semantics
- **WHEN** a consumer reads node x/y
- **THEN** same-layer grid nodes carry metre coordinates and wilderness nodes carry kilometre-cell coordinates; cross-layer gateway slots are renderer-local offsets used for exit direction, never physical distance. Instance/interior coordinates remain layout values and are never interpreted as metric geography.

#### Scenario: The readout states the current coordinate figure and nothing else
- **WHEN** the island's readout line renders on a coordinate-bearing layer
- **THEN** it SHALL state the `current` node's coordinates as a two-integer figure — that node's payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — and SHALL state nothing else: it SHALL NOT state the current node's place name, its visibility state, a movement destination, or any other label, because the canvas already marks the current node and the shell's own location surface already names the place

#### Scenario: The readout ignores hover and selection
- **WHEN** the player hovers or selects a node
- **THEN** the readout SHALL NOT be driven by pointer hover or by node selection: the island SHALL hold no hovered-node and no selected-node state, and the readout SHALL be a pure function of the committed payload, so it describes where the player is after every move without any re-seeding and cannot go stale when a payload replaces the rendered one

#### Scenario: No surface states a forbidden figure
- **WHEN** the island renders coordinate or distance figures
- **THEN** only its current coordinate, uniform spacing caption or compressed distance rings are permitted; other-node coordinates/numeric bearings/per-node distances remain absent, while drawer scale and commission text follow their own panel precision contract

#### Scenario: A coordinate-free layer resolves the readout to nothing
- **WHEN** the payload layer is coordinate-free
- **THEN** there is no coordinate figure, so the readout resolves to nothing and the empty-readout rule governs it unchanged: when the readout has nothing to state it SHALL state nothing and SHALL render no framed container, painting no box, rather than presenting an empty bordered widget; its row SHALL keep its one-line height so the island's size does not change with the layer

#### Scenario: No node's name depends on the readout
- **WHEN** the readout label content is removed
- **THEN** drawn island nodes retain full accessible names, gateway stubs are named 往 <leads_to> 移動, and all full remembered/context names remain readable through drawer text disclosure

#### Scenario: The readout treatment is token-driven, not copied
- **WHEN** the island renders its readout
- **THEN** it SHALL adopt the redesign draft's closing-readout treatment as a token-driven rule rather than as a copy of the draft's declarations: it SHALL render at the island's smallest type step in the shared monospace font token, centred beneath the canvas, at a de-emphasised paper tier whose contrast against the island's panel background is at least 4.5:1, separated from the canvas by a step from the shared spacing scale, with no border, no background fill, and no padded box
- **AND** no draft hex value and no draft-canvas pixel literal SHALL be hardcoded for it

#### Scenario: The single full-map affordance is an invisible real button
- **WHEN** the island presents its full-map affordance
- **THEN** exactly one full-map affordance remains, with no visible expand-button chrome; cross-layer gateway stubs are separate focusable move buttons. The transparent full-bleed expand button remains beneath content with no focusable descendant and accessible name 展開全地圖.

#### Scenario: Activation runs through the platform's button behaviour
- **WHEN** the affordance is activated by pointer, by Enter, or by Space
- **THEN** it SHALL open the full-map surface through the platform's own button behaviour, and no key handler on a non-button element SHALL stand in for it

#### Scenario: The affordance is the island's tab order and focus ring
- **WHEN** a keyboard user reaches the affordance
- **THEN** it SHALL be reachable in the island's tab order without the island's root element gaining a role or a tab stop of its own, and its focus-visible indication SHALL delineate the whole island rather than a small region of it

#### Scenario: The affordance survives payloads so focus returns
- **WHEN** payloads commit while the full-map surface is open
- **THEN** the affordance element SHALL be stable across committed payloads, so the full-map surface's opener — the focused element captured when that surface opens — still exists when it closes and focus is restored to it

#### Scenario: Body clicks open the map; descendants keep their own behaviour
- **WHEN** the island's pointer convenience is exercised
- **THEN** it SHALL be unchanged: a click on the island's body SHALL open the full-map surface, a click that originates in an interactive descendant — an actionable lattice node or the affordance itself — SHALL run only that descendant's own behaviour, and every activation path SHALL open the full-map surface exactly once

#### Scenario: The island carries no other interactive descendant
- **WHEN** the island is rendered
- **THEN** remembered markers and their text alternatives remain inert and non-focusable; the existing full-map affordance remains, and each cross-layer gateway stub with a move action is an additional focusable button. Instance/interior behavior is unchanged.

#### Scenario: Remembered presentation follows the variant, once per surface
- **WHEN** remembered nodes are presented on a surface
- **THEN** their presentation SHALL follow the resolved layout variant, and each such node SHALL be presented exactly once on a given surface
- **AND** their payload coordinates SHALL NOT influence either exported node placement

#### Scenario: The lattice names its remembered places by edge direction marker
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Marker names stay inside the outermost gutter band
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A name's room is declared before it is drawn
- **WHEN** a surface prepares to draw marker names
- **THEN** the room a name may occupy SHALL be declared in the terms the placement helper consumes — the band depth every surface reserves, and, on a surface that draws its names OUTWARD across that band rather than along it, an outward name box — so the room is reserved before the names are drawn rather than discovered afterwards
- **AND** each name SHALL then be fitted to what that same declared geometry reserved for it, and no surface SHALL draw a name longer than the room its own declaration set aside

#### Scenario: The fit budget is measured in monospace cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Ambiguous names are dropped, never equalled
- **WHEN** a name does not fit its budget
- **THEN** it SHALL be truncated with an overflow indicator, and no surface SHALL draw two equal marker names while the payload labels behind them differ: rather than asserting that two distinct places are one place, it SHALL drop the visible name of a marker it cannot distinguish, keeping that marker's position, bearing, and state indicator
- **AND** that rule binds every surface that fits names, not only the smaller one
- **AND** a dropped or truncated visible name SHALL NOT reduce what a reader can obtain: every drawn marker's untruncated payload label SHALL remain available through the surface's assistive-technology text alternative

#### Scenario: The text alternative mirrors the drawn marker set
- **WHEN** the lattice variant's remembered markers carry no activation and are drawn inside a graphic
- **THEN** the text alternative mirrors those markers one-for-one in deterministic order with full names and octant words; it adds no remembered distance, numeric bearing or coordinates. The island scale caption and compressed ring labels are separate permitted distance information.

#### Scenario: The mirror omits nothing, invents nothing, adds no tab stop
- **WHEN** the surface derives its remembered-marker text alternative
- **THEN** it derives from the same remembered marker set and adds no tab stop; neither remembered markers nor their mirror become activatable. The island separately retains its full-map affordance and gateway exit-stub buttons.

#### Scenario: Coordinate-free payloads render no edge direction markers
- **WHEN** a coordinate-free payload renders
- **THEN** it SHALL render no edge direction markers, because a radial graph draws no canvas edge for a bearing to cross and its node `x`/`y` are renderer-local layout values

#### Scenario: The graph variant presents remembered nodes through a hidden list
- **WHEN** the graph variant renders remembered nodes on the island
- **THEN** the island SHALL present them only through an assistive-technology text alternative: a visually hidden, non-focusable list with one entry per `remembered` node in payload order, each stating that node's untruncated payload label and no direction, no distance, and no coordinate figure
- **AND** no remembered node on that variant SHALL be placed on the canvas or on its border, since a position there would assert a bearing the payload does not carry

#### Scenario: The island never shows a visible remembered list
- **WHEN** the island renders remembered room nodes
- **THEN** its size remains fixed with no visible list, each remembered name remains in its non-focusable text alternative, and the map drawer provides readable text disclosure

#### Scenario: Edges are inert connector lines
- **WHEN** the island draws edges
- **THEN** connector layers are inert; coordinate-bearing island draws only labelled one-hop current exit edges and no context lines, while radial graph edges remain real-exit-honest and absent endpoints create no connector

#### Scenario: The minimap change leaves the payload rules untouched
- **WHEN** the browser minimap renders
- **THEN** the `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged

#### Scenario: The island mounts no state legend
- **WHEN** a valid local_map island renders and the map drawer opens
- **THEN** no legend element exists in island DOM; the drawer owns its separate area/world legend

#### Scenario: A remembered place is readable and offers no travel action
- **WHEN** the island presents a remembered node as a directional marker or graph text alternative
- **THEN** its untruncated name and non-colour state are readable, drawer disclosure remains available, and that remembered node has no travel action

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (marker shape, border, or text label) on the island without any legend — the remembered state by its diamond ornament on the canvas border, named beside it — and the drawer legend remains readable

#### Scenario: Reconnect rebuilds from persisted knowledge
- **WHEN** the WebSocket reconnects and a new-epoch snapshot arrives
- **THEN** the minimap is rebuilt from the server-persisted visited record and current location, and no client-stored map state is treated as authoritative

#### Scenario: Unknown panel schema disables only the minimap
- **WHEN** a received `local_map` payload fails its exact schema
- **THEN** only the minimap renderer is disabled, the browser requests at most one full resynchronization, and narrative and text input remain usable

#### Scenario: In-view nodes occupy distinct lattice cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Distant remembered nodes do not distort the local view
- **WHEN** the payload carries remembered nodes many cells away from the current node
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear as named markers on the canvas border rather than occupying lattice cells

#### Scenario: A remote remembered place marks the canvas edge at its true direction, with its name
- **WHEN** a coordinate-layer payload remembers a known place outside the drawn extent, e.g. 聖潔王都 to the north-east or a cave to the south-west
- **THEN** its remembered diamond renders on the corresponding border of the canvas, pointing along the true coordinate bearing, with that place's name drawn as visible text beside it in the marker gutter band, and no distance, angle, or coordinate figure appears with it

#### Scenario: The island presents each remembered place once, with no list beneath the map
- **WHEN** a wilderness payload carrying remembered gateways renders on the minimap island
- **THEN** no remembered-node list element exists anywhere in the island's DOM, each remembered gateway is drawn exactly once as a named edge direction marker, and no remembered place is presented both as a marker and as a list entry

#### Scenario: A lone gateway on an edge carries its whole authored name
- **WHEN** exactly one remembered gateway's bearing leaves through a given canvas edge and its authored label is the disambiguated form 西部丘陵與谷地（南門）
- **THEN** that marker's visible name is the complete label rather than a four-glyph node-label truncation, because the name is fitted to the free span its own marker holds along that edge

#### Scenario: Bounding the outward box leaves the island's own fitting untouched
- **WHEN** the island fits the marker names for a payload, declaring band depth only and no outward name box
- **THEN** its budget, its drawn names, and its marker geometry are exactly what they were before the outward term existed, because a term a surface does not declare cannot bind it

#### Scenario: A truncation that would make two places look alike is refused
- **WHEN** two remembered gateways whose payload labels differ only in a trailing qualifier — 西部丘陵與谷地（南門） and 西部丘陵與谷地（北門） — crowd one canvas edge so tightly that neither name can be drawn distinctly in its span
- **THEN** the surface does not draw the same string twice: each name it does draw is distinct from every other drawn marker name, any marker it cannot distinguish keeps its diamond, its bearing, and its landmark treatment with its visible name omitted, and both untruncated labels remain available to assistive technology

#### Scenario: A name the island cannot show is still reachable without assistive technology
- **WHEN** a sighted keyboard reader cannot read a full remembered/context label on the island
- **THEN** the one full-map button opens MapDrawer, where the full permitted name is readable at 16 CSS px or more through text disclosure without travel

#### Scenario: The disclosure chain ends at the largest surface's declared capacity
- **WHEN** an authored gateway label is longer than the declared name capacity of the surface with the largest one, so even that surface must fit it
- **THEN** that surface draws the fitted name with its overflow indicator and carries the untruncated label as the marker's accessible name, and it SHALL NOT instead draw the name past its reserved box: a name that overruns its box overprints the canvas rect — the node markers, the node labels and the axis the invariant above protects — or its neighbouring marker's name, so it discloses nothing, and the bounded name with its overflow indicator is the surface's final visible answer

#### Scenario: The binding term follows how the surface draws its names
- **WHEN** one surface draws its marker names outward across the band while another draws them along the band, and both fit the same authored label
- **THEN** the outward-drawing surface's budget is bounded by its declared outward name box as well as by its along-edge span, the along-drawing surface's budget is bounded by its span alone because it declares no outward box, and nthe island's drawn name exceeds the room its own declaration reserved

#### Scenario: Marker names never collide with each other, a node label, or the axis
- **WHEN** a lattice payload places remembered markers on several canvas edges, including two on one edge, while the drawn lattice carries in-view node labels at the renderer's truncation length and the island draws the axis cross that the invariant names
- **THEN** every marker name is rendered wholly inside the marker gutter band outside the canvas rect — the rect the coordinate-field padding grows, so the band stays outermost — so no marker name's box intersects any node marker, node label, or the drawn axis line, and no two marker names' boxes intersect each other

#### Scenario: Rank compression never skews a marker's direction
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A coordinate-free payload draws no edge markers and still presents its remembered nodes
- **WHEN** an interior or instance payload with remembered nodes renders on the island
- **THEN** no remembered directional marker or fabricated coordinate is drawn, island size stays fixed, each name has one untruncated non-focusable text alternative and drawer disclosure provides visible text

#### Scenario: An interior payload's remembered rooms do not vanish with the lattice's list
- **WHEN** the player, having walked twelve rooms of a building, stands in one whose interior payload carries those rooms as `remembered`, and the island renders
- **THEN** the island's rendered size and its canvas size are exactly what they are for the same building with no remembered room, no remembered room's name is drawn as visible text on the island, every one of those rooms is named once in the island's text alternative, and activating the island's full-map affordance opens a surface that names every one of them as visible text

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1451x790 and at 1741x948, on a lattice payload with named edge markers and on a graph payload with remembered nodes
- **THEN** the canvas renders at exactly 240 × 240 CSS px (S = 1) at the reference acceptance viewport and 288 × 288 CSS px (±1) at 1741x948 (S = 1.2), the title, orientation marks, marker names, and readout line remain readable, no node marker, marker name, or edge overprints other island content, the island's rendered box is identical for both payloads, and no required island content has to be scrolled to

#### Scenario: The island keeps the identifier its mode gating selects on
- **WHEN** the minimap island renders after a chrome change
- **THEN** its root element still carries the stable `local-map` component identifier, and the mode whose matrix hides the minimap still removes it from the layout and from the tab order

#### Scenario: The island states its convention and the current coordinates
- **WHEN** the committed payload layer is coordinate-bearing
- **THEN** the island retains its axis orientation marks and current-node-only coordinate readout; its scale caption or compressed rings state the mapping separately without adding any per-node distance or numeric bearing.

#### Scenario: The readout states the coordinate figure and nothing else
- **WHEN** a wilderness payload whose current node is labelled 西部丘陵與谷地 at (60, 107) renders on the island
- **THEN** the readout line reads exactly the two-integer coordinate figure for (60, 107), it carries no place name, no 目前所在 or other visibility-state word, and no movement destination, and the place name appears instead on the shell's own location surface

#### Scenario: Hovering or activating a node never changes the readout
- **WHEN** the player hovers a non-current node, then activates one, on a coordinate-bearing layer
- **THEN** the readout line still states the current node's coordinate figure and nothing else, no coordinate figure for the hovered or activated node is rendered anywhere, and the island holds no hovered-node or selected-node state that the readout could go stale on

#### Scenario: A node's name stays reachable without the readout
- **WHEN** an island node label is truncated or context is omitted
- **THEN** full accessible names and gateway stub naming remain intact and the drawer can disclose full permitted node/remembered labels without retargeting movement

#### Scenario: A screen-reader user can still reach every remembered place
- **WHEN** a screen-reader user reads the minimap island on a wilderness payload carrying several remembered gateways, none of which is focusable and each of which is drawn inside the map graphic
- **THEN** the island exposes one text-alternative entry per drawn marker, in a deterministic order, each stating that place's untruncated authored name and its direction as one of the eight octant names, so no remembered place is reachable only by sight

#### Scenario: Replacing the list adds no tab stop and no activation
- **WHEN** a keyboard user tabs through an island carrying remembered gateways
- **THEN** remembered markers and text alternatives add no tab stop or travel action; the full-map affordance and any actionable cross-layer gateway stub retain their own behavior and do not activate each other.

#### Scenario: A coordinate-free layer asserts no orientation and no coordinates
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure, the map title renders exactly as on a coordinate-bearing layer, and the readout line — having nothing to state — states nothing and paints no box

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Adjacent node markers, labels, and connector edges never visually collide
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A densely populated lattice keeps readable collision-free geometry
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A sparse lattice scaled up never reintroduces overlap
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** a graph-variant payload combines a two-ring in-view placement with the model's maximum of remembered nodes
- **THEN** the island lays out no remembered-node list at all, its canvas is still 240 × 240 CSS px at the 1451x790 reference viewport (the canvas never depends on payload content, and the chrome factor magnifies it uniformly at every larger viewport), its title and readout row keep their places, the island's size equals its size for the same placement with no remembered node, and no required island content has to be scrolled out of view

#### Scenario: The name gutter never hands the anchor a scrollbar
- **WHEN** remembered markers enlarge the required drawing
- **THEN** the coordinate-bearing island keeps its 240-unit projection, current at (120,120), all exits within the exit ring and readable text; remembered markers keep their existing edge-direction presentation and the anchor has no scrollbar.

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Draft marker ladder reads without colour
- **WHEN** the island renders current, visited, unvisited and gateway nodes
- **THEN** current retains its larger seal treatment, visited is solid and unvisited hollow; gateway nodes add the gate glyph, room name and `通往 <leads_to>` second line without relying on colour to identify a gateway.

#### Scenario: Map chrome colours resolve to design tokens
- **WHEN** the island renders its chrome
- **THEN** every marker, edge, label, and legend colour resolves to a design token value, and the draft seal pair and label tiers match the tokens added with this change

#### Scenario: The radial placement is deterministic and edge-honest
- **WHEN** the model computes the radial placement for a payload whose in-view nodes are joined by edges
- **THEN** the current node sits at the centre, every other in-view node sits on the ring of its BFS exit-hop distance (edgeless in-view nodes on the outermost ring), and re-running the pass on the same payload produces identical coordinates

#### Scenario: The resolved layout preserves nodes, edges, and actions
- **WHEN** coordinate-bearing and coordinate-free local_map payloads arrive
- **THEN** automatic projection applies only to grid/wilderness, context has no route and cross-layer target has only a stub; radial graph mechanics and canonical actions remain intact with no manual island zoom/layout control

#### Scenario: The orientation mark follows the resolved layout
- **WHEN** the payload's layer resolves to the graph variant (`interior`, `instance`)
- **THEN** the island renders no axis orientation mark and no coordinate figure, and on a layer resolving to the lattice (`grid`, `wilderness`) the mark renders alongside the current node's coordinate figure

#### Scenario: The island's canvas claims its content width as coordinate margin
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The island's name band is reserved as band depth, not as an outward box
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A sparse payload reads airy rather than magnified
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The height budget is spent as an equivalent width bound
- **WHEN** a tall coordinate-bearing payload renders on the island
- **THEN** the 240-unit island selects its automatic uniform/compressed projection for current/exits without height-derived width caps or below-floor text; drawer scope uses its own metric/radial view

#### Scenario: A graph payload is cropped to its footprint and never magnified
- **WHEN** an interior graph containing one node and then a graph containing many neighbors renders on the island
- **THEN** both use a fixed 240-unit square window centered on the current node, render labels at exactly 16 CSS px at reference, and leave every full name reachable through the full map

#### Scenario: Repeated budget measurements do not ratchet the canvas down
- **WHEN** the island re-renders across many successive payload commits and `map` anchor resizes
- **THEN** every render draws the canvas at exactly 240 × 240 CSS px at the stated reference acceptance viewport, because the island measures nothing to size itself — no anchor height, no section height, and no resize observation feeds its canvas — so no sequence of renders can walk the canvas down toward a floor

#### Scenario: The island's size never depends on the payload
- **WHEN** the island renders, in turn, a coordinate-bearing lattice payload with remembered gateways, a single-node lattice payload, and an interior graph payload carrying twelve remembered rooms
- **THEN** the island's rendered width and height are identical for every one of them and its canvas is 240 × 240 CSS px each time at the 1451x790 reference viewport

#### Scenario: A long authored title never reflows the island's header
- **WHEN** the committed payload's server-authored title is long enough that the title and the orientation marks together exceed the island's content width (e.g. `冒險者公會外街道圖` beside the axis marks in the island's reference-scale 240px content box)
- **THEN** the header stays a single row: the title renders on one line truncated with an overflow indicator while its complete string stays available as the element's tooltip/accessible text, the orientation marks keep their full size without wrapping, no full-map control occupies the row at all, and the island's card width is unchanged

#### Scenario: The readout follows the player after a move
- **WHEN** a newly committed payload replaces the rendered one with a different `current_node`
- **THEN** the readout line states the new payload's current node's coordinate figure rather than resolving to nothing or to the previous room, without any selection to re-seed, and the island shows no blank readout

#### Scenario: A readout with nothing to say draws no box
- **WHEN** the island's readout line has nothing to state
- **THEN** the line states nothing and paints no border or box, and its row keeps its one-line height so the island's size is the same as on a payload whose readout states a figure

#### Scenario: The island offers exactly one full-map affordance, with no visible button
- **WHEN** an available local-map payload renders
- **THEN** exactly one transparent full-bleed full-map button named 展開全地圖 exists; the root has no role or tab stop and no expand icon or labelled expand control is added. Separate exit-ring gateway buttons remain visible/focusable for their move action.

#### Scenario: A keyboard user opens the full map from the island
- **WHEN** a keyboard user tabs to the island's full-map affordance and presses Enter, and then repeats the run pressing Space
- **THEN** each activation opens the full-map surface exactly once through the button element's own platform behaviour, with no key handler on a non-button element involved, and the focus-visible indication while it is focused delineates the whole island rather than a small corner of it

#### Scenario: Activating a lattice node moves instead of opening the map
- **WHEN** the player clicks an actionable in-view lattice node, its marker, an edge direction marker, or the full-map affordance itself
- **THEN** a click on the node or its marker submits that node's move and emits no map-open, a click on an edge direction marker — which carries no behaviour of its own — falls through to the island body and opens the full-map surface exactly once, a click on the affordance opens the full-map surface exactly once, and a click on the island's plain body opens the full-map surface exactly once

#### Scenario: Closing the full map returns focus to the island affordance
- **WHEN** the player opens the full-map surface from the island and then closes it
- **THEN** the element captured as the opener is the island's full-map affordance, that element still exists after the payload commits that arrived while the surface was open, and focus is restored to it

#### Scenario: The readout renders in the draft's token-driven treatment
- **WHEN** the island renders its coordinate readout
- **THEN** the line is centred beneath the canvas at the island's smallest type step in the shared monospace font token, its colour resolves to a design token whose contrast against the island's panel background is at least 4.5:1, it draws no border, background fill, or padded box, and no draft hex value or draft-canvas pixel literal is hardcoded for it

#### Scenario: The coordinate field draws one dot per cell, registered to the placement
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A field whose pitch stopped meaning one cell is rejected
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A coordinate field that went invisible fails
- **WHEN** the uniform island dot field and axis are measured against ground
- **THEN** existing token contrast floors apply; compressed island correctly uses rings instead of dots

#### Scenario: The dot field never reads as a fifth node state
- **WHEN** uniform dots render beside node markers
- **THEN** each dot is materially smaller than the smallest marker, with no stroke, label, state class, node identity or activation; the visibility legend is unchanged. Compressed island rings use distance text and do not imply a node visibility state.

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** the island's lattice renders its canvas edges
- **THEN** exactly one vignette element darkens the canvas outward as a single full-canvas gradient wash, no per-cell fill, per-region fill, or shape tracing any terrain feature is introduced anywhere, with no fabricated terrain on the island

#### Scenario: The vignette never erases the far-field dots
- **WHEN** uniform island dots nearest canvas corners are measured through the vignette
- **THEN** they retain the existing contrast presence floor; compressed island mode uses rings in place of dots and the vignette cannot erase their distance information.

#### Scenario: The axis is drawn only where the convention is stated in words
- **WHEN** a coordinate-bearing island states 北↑ 東→
- **THEN** its full-width/full-height axis passes beneath the current marker, and a coordinate-free graph states/draws no axis

#### Scenario: The axis crossing the current marker is not a collision
- **WHEN** the island draws its axis through the `current` node
- **THEN** the axis passes beneath that node's own marker, which is what an origin is, the drawn edge direction markers stay wholly outside the canvas rect that contains the axis, and the non-overlap invariant that names the axis is satisfied

#### Scenario: The graph variant draws no coordinate field and no axis
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A node label never renders larger than the surface's own chrome
- **WHEN** a sparse or crowded payload renders on the island
- **THEN** every drawn node label is exactly its declared 16-unit step at reference scale, never smaller through SVG scaling and never larger than the island's title

#### Scenario: The pitch clears exactly what the drawn label set needs
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Vertical clearance is derived even above an unlabeled marker
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The drawn cell is square so the lattice and its bearings agree
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The decoration layers stay out of the audit and the accessibility tree
- **WHEN** geometry audit and assistive technology inspect island decoration
- **THEN** dots, rings, vignette and axis add no node-marker/node-label boxes or tab stops and intercept no pointer events; distance text supplies the scale information. Remembered markers remain inert while gateway exit stubs are separate named buttons.

#### Scenario: Reduced motion and the non-colour encoding are unaffected
- **WHEN** the island renders with the reduced-motion preference active and with the colourblind override on
- **THEN** none of the three new layers animates or transitions anything, none carries a visibility state, the four-state shape ladder and its non-colour redundancy are unchanged, and every focus treatment behaves exactly as before

#### Scenario: The lattice colours resolve to existing tokens with no draft literal
- **WHEN** the coordinate field, the vignette, and the axis render on the island
- **THEN** each layer's colour resolves to a design token already defined for the map surfaces, no new token is required, and no draft hex value and no draft-canvas pixel literal is hardcoded for any of them

#### Scenario: The island scales once with the desktop chrome factor
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Labels are budgeted in monospace cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD island
- **THEN** the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and unchanged remembered edge-direction markers. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The fixed island consumes automatic projection
- **WHEN** a grid/wilderness payload with one-hop and two-hop nodes renders in the island
- **THEN** current is centred at (120,120) in a 240-unit square, every same-layer exit including action-null exits is drawn inside radius 88, drawable context uses small background dots without connecting lines, and context outside the canvas is omitted; no window over a minimum-pitch lattice can hide an exit.

#### Scenario: The background states scale by shape and text
- **WHEN** the island changes between uniform and compressed mode
- **THEN** uniform mode draws world-anchored dots at M/5 metres (20 units) and a spacing caption; compressed mode draws labelled distance rings using its projection and no dot field. Scale text respects the 16 px floor and is distinct from the unchanged coordinate readout.

#### Scenario: Metric fixtures exercise actual renderer exits
- **WHEN** real Altoria, Ciaran, wilderness, gateway and extreme-ratio island stories render
- **THEN** all exit representations fit inside the canvas without overlapping each other; coordinate-free fixtures retain their radial contract and only the new drawer scope fixtures establish full-map behavior

#### Scenario: Labels are assigned in navigation priority
- **WHEN** island marker labels compete for space
- **THEN** eight candidate positions per marker are tried in exit, current, context priority; an exit label that fits nowhere remains drawn truncated to labelMax with a leader line, a context label that fits nowhere is omitted, and each full name remains in its accessible name. Gateway second-line labels respect the 16 px floor.

### Requirement: Minimap adjacent movement remains bound to authoritative descriptors
The WebClient `local-map` component SHALL make a currently traversable adjacent node with an exact `move` action descriptor actionable: activating it (click or Enter on the focused node) SHALL submit the `explore.move` UI action carrying that node's opaque `exit_ref` and the canonical `current_node` identity.

#### Scenario: Ineligible nodes stay inert or focus-only
- **WHEN** a node has `action: null`, is a remembered remote node, or its `visibility` is not a current-field-of-view state
- **THEN** it SHALL NOT submit any travel action and SHALL remain inert or focus-only exactly as before

#### Scenario: Submissions derive only from the validated payload
- **WHEN** the component submits a move
- **THEN** it SHALL derive the submitted `exit_ref` and `current_node` only from the validated `local_map` payload, SHALL NOT construct an exit reference, destination, or room identity from entity data or prose, and SHALL leave the `local_map` panel payload contract, the `未探索` unvisited-node rule, and the remembered-node no-travel rule unchanged

#### Scenario: The refreshed payload replaces the rendered minimap
- **WHEN** a submission succeeds or is rejected
- **THEN** the refreshed `local_map` payload at the newer revision SHALL replace the rendered minimap, and the component SHALL NOT keep a client-side canonical map cache

#### Scenario: The pitch fix never retargets an activation
- **WHEN** the corrected node-pitch geometry of this change is applied
- **THEN** it SHALL NOT alter which node an activation targets: the enlarged marker's clickable/focusable area SHALL remain centered on the same lattice coordinate the payload assigned it

#### Scenario: Activating an adjacent traversable node submits explore.move
- **WHEN** the player focuses an adjacent traversable node whose `action` is the exact `move` object and confirms it
- **THEN** the browser submits exactly one `explore.move` envelope with that node's `exit_ref` and the panel's `current_node`, and the refreshed `local_map` payload replaces the rendered map

#### Scenario: A remembered remote node still offers no travel action
- **WHEN** the player focuses a remembered remote node (which carries `action: null`)
- **THEN** its name/landmark is shown and no `explore.move` or other travel submission is possible, matching the pre-existing rule

#### Scenario: A map node never invents a destination
- **WHEN** a node's `action` is missing, malformed, or not the exact `move` object, or the payload is rejected by its validator
- **THEN** no travel action is submitted, only the minimap renderer disables itself with the single-sync recovery path, and narrative and text input remain usable

#### Scenario: The wider marker geometry still targets the correct node
- **WHEN** the player activates a node marker after the pitch/sizing fix has been applied
- **THEN** the `explore.move` submission carries the same node's `exit_ref` and destination as before the
  fix, unaffected by the marker's new visual size or position within its (now larger) cell

## MODIFIED Requirements

### Requirement: Map chrome and ordinary node labels are legible without dropping topology
The minimap island's title, orientation marks and readout SHALL render at the shared `--text-xs` step (16 CSS px at the reference scale), which is the island's one and smallest chrome step, and the map drawer's controls, legend, quest list and details SHALL render at 16 CSS px or more through the shared type tokens; neither surface SHALL hardcode a map chrome type size below that step.

#### Scenario: Node text keeps its declared floor at every scale
- **WHEN** the island draws node labels and marker names
- **THEN** each SHALL render at its declared 16-unit step with an effective rendered size of at least 16 CSS px at reference, and at least 22.4 CSS px at the desktop chrome cap

#### Scenario: Oversized drawings clip instead of shrinking
- **WHEN** a coordinate-bearing or graph island renders a large payload
- **THEN** the island automatically fits all same-layer exits at the declared text floor, may omit off-canvas context and never draws cross-layer targets as nodes; all payload nodes/actions remain in the model. The graph island retains its current-centred scale-1 window, and the drawer provides permitted names through its area/world text disclosure.

#### Scenario: The derived pitch clears the drawn label set
- **WHEN** metric nodes have dense screen-space projections
- **THEN** the island uses its metric projection with bounded overlap spreading, readable labels and authoritative action identity, without changing payload coordinates.

#### Scenario: Ordinary neighbourhood is readable
- **WHEN** a three-by-three grid lattice of distinct two- and four-glyph room names with no remembered gateway renders on the island at 1451x790 and at 2560x1440
- **THEN** the title, orientation marks and readout compute to 16 CSS px at the reference viewport, the drawing's scale is 1, every drawn node label is at least 16 CSS px at the reference viewport (and at least 22.4 CSS px at 2560x1440, the same labels at the 1.4 chrome cap) and at most the island's declared 16-unit step at the reference scale, and no node marker or node label overlaps another node's marker or label

#### Scenario: Dense knowledge stays available
- **WHEN** a bounded dense payload with remembered gateways renders on the island and map drawer
- **THEN** the island retains its 240-unit square and text floor, draws current and every exit, omits off-canvas context and preserves remembered edge-direction markers. The model retains all payload nodes and the drawer keeps permitted names readable.

### Requirement: Metric coordinates survive authoritative transport and uniform projection
Local-map transport SHALL accept physical settlement coordinates and the wilderness frame. The island SHALL use automatic uniform or compressed projection with exact bearings except bounded overlap spreading; area_map/world_map uniform viewport behavior is owned by their separate map capabilities; row/column rank compression SHALL be removed. Server coordinates and node/action identity SHALL remain authoritative.

#### Scenario: Unequal gaps survive real rendering
- **WHEN** nodes at (0,0), (100,0), (1000,0) and (1000,6500) pass both validators and render
- **THEN** the area drawer preserves its own metre-coordinate gap ratios; the island uses its exit-driven uniform/compressed mapping without changing wire coordinates or action identity; logarithmic island compression is permitted only under the approved threshold rules.

#### Scenario: Expanded bounds
- **WHEN** settlement (6500,6350) and wilderness (2699,2699) arrive over the real protocol
- **THEN** both validate; malformed noninteger/nonfinite coordinates remain rejected without guessed geometry.

#### Scenario: Visibility and remembered markers
- **WHEN** a viewport pans across remembered and unknown hidden locations
- **THEN** remembered boundary markers preserve physical orientation; unknown locations stay absent, movement descriptors retain actual traversable exits, and no action or knowledge is created by projection.

#### Scenario: Coordinate-free interiors
- **WHEN** an interior graph with no physical coordinates is shown
- **THEN** its existing graph semantics remain without invented meter positions.

### Requirement: The map surfaces state a place name only where it adds information
On the `wilderness` layer, an in-view `wild:` neighbour whose coordinates are a registered gate's approach cell SHALL be labelled with that entry's anchor display name — the place the gateway leads to — instead of the display name of the region the cell lies in, while retaining its identity and action. Island one-hop exit labels follow the never-dropped label-placement contract; context labels may be omitted while all exit labels stay available.

#### Scenario: The gate approach cell keeps every other field
- **WHEN** a gate approach cell is relabelled with its entry's anchor display name
- **THEN** its node ID, `action`, edges, visibility, and every other field SHALL be unchanged, so the payload states a better name for the same position and never invents an identity for it

#### Scenario: Every other cell keeps its region name and labels stay non-empty
- **WHEN** an in-view cell is not a registered gate's approach cell
- **THEN** it SHALL keep the region display name it carries today, and every emitted node label SHALL remain a non-empty string

#### Scenario: Duplicate region labels draw no visible text
- **WHEN** the island draws repeated wilderness region names
- **THEN** every exit label follows eight-candidate placement with truncated leader-line fallback; context labels may be omitted when no position fits. Full accessible names and marker/action identity remain unchanged.

#### Scenario: Suppression is scoped to shared region names
- **WHEN** the island draws repeated wilderness region names
- **THEN** every exit label follows eight-candidate placement with truncated leader-line fallback; context labels may be omitted when no position fits. Full accessible names and marker/action identity remain unchanged.

#### Scenario: Suppression touches no payload field
- **WHEN** label suppression is in effect
- **THEN** it is a drawing rule about the set on the canvas, not a payload rule: no payload field changes, and both validators keep their existing bounds and their non-empty label rules unchanged

#### Scenario: The wilderness neighbourhood stops repeating one region name
- **WHEN** the island draws repeated wilderness region names
- **THEN** every exit label follows eight-candidate placement with truncated leader-line fallback; context labels may be omitted when no position fits. Full accessible names and marker/action identity remain unchanged.

#### Scenario: An in-view gate approach cell names the place behind it
- **WHEN** the player stands one cell from a registered gate's approach cell, so the approach cell is
  an in-view neighbour
- **THEN** that neighbour's label is the entry's anchor display name rather than the region display
  name, its node ID is still the approach cell's `wild:` ID with its unchanged action and edge, and
  because the label differs from the current node's label the renderer draws it as visible text

#### Scenario: A cell in a different region still says so
- **WHEN** an in-view neighbour lies in a different wilderness region than the current cell
- **THEN** its region display name differs from the current node's label, so the renderer draws it as
  visible text and the region change stays visible

#### Scenario: Suppressed labels never weaken the state ladder or activation
- **WHEN** a node's visible label is suppressed as a duplicate of the current node's label
- **THEN** its marker shape, landmark treatment, `data-node` identity, move action, and accessible name
  are all unchanged, and the four visibility states remain distinguishable without colour

### Requirement: Island movement uses scale-aware effective motion
For unchanged mode and level, island movement SHALL retain its existing FLIP pan and move world-anchored dots with the drawing. A changed level or mode SHALL use a short crossfade for effective full motion and switch immediately for effective reduced or off motion. Instance/interior island transitions SHALL remain unchanged; the new drawer reveal follows its separate reduced-motion contract.

#### Scenario: Same scale pans the ground
- **WHEN** a move commits with unchanged projection level and mode
- **THEN** the existing pan transition is used and dots move with the same drawing transform instead of staying screen-fixed; final dot anchors still match world multiples.

#### Scenario: A changed level or mode never uses equal-scale FLIP
- **WHEN** a move changes uniform level or switches between uniform and compressed mode
- **THEN** full motion uses a short crossfade under the shared motion tokens; reduced/off commit the new projection immediately, without an animated scale interpolation or lingering previous-scale frame.

#### Scenario: Real gateway journey remains usable
- **WHEN** the player walks Altoria south gate to wilderness and back in the real client
- **THEN** each settled island shows current and every available adjacent exit, valid far-side gate labels and usable return controls; the map drawer uses its area/world views, and coordinate-free island layouts remain unchanged.
