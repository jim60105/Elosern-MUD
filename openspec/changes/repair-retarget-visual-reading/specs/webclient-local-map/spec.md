## MODIFIED Requirements

### Requirement: The browser minimap renders states without relying on color alone
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels on the full-map overlay, inside that surface's legend popover (the minimap island mounts no state legend), SHALL make every `remembered` remote node's name readable without any travel action and without any activation — as visible text on a map surface (the island's named edge marker on the lattice variant, the full-map surface's remembered list on the graph variant) and, wherever the island does not draw that name as visible text, wherever that visible text can be truncated, or wherever it is drawn inside a graphic, as an assistive-technology text alternative on the island carrying the untruncated name — and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. The island SHALL have a constant size that no payload changes: a single 1px hairline frame, a padding no larger than the shared spacing scale's smallest step, a single-row header, a square map canvas of 240 CSS px on each side at the 1451x790 reference scale, multiplied once by the desktop chrome factor above the reference height, and a readout row that always reserves its one line. The island SHALL NOT stretch to its anchor's width, SHALL NOT measure its anchor or any other surface to size itself, and SHALL NOT draw a second frame around its canvas inside its own frame. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

The island and the full-map overlay SHALL present the redesign draft's map visual language: every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value. On either placement's canvas the `current` node SHALL render as a seal-deep filled circle with a seal-light stroke, strictly larger than the other on-canvas markers; `visible_visited` SHALL render as a small ink-filled circle; `visible_unvisited` SHALL render as a small hollow circle keeping the `未探索` rule; a landmark node SHALL additionally carry the gold landmark treatment. The resulting shape ladder (large stroked circle / small solid circle / small hollow circle / out-of-canvas diamond for `remembered`) SHALL keep the states distinguishable without colour at both the island and the overlay scale, and the new marker footprints SHALL remain within the geometry guarantee so the non-overlap invariant is unaffected. Node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far). Each surface SHALL declare its own node-label type size, and that size SHALL NOT resolve to drawn text larger than the surface's own smallest chrome type step, so a node label can never out-weigh the island's own title at any payload. The island declares a 16-unit node-label step — equal to its 16px chrome step — and a 16-unit marker-name step; the full-map overlay declares 16 and 16. A fitted drawing SHALL never render a node label or marker name below its surface's declared step at the reference scale: where the fitted uniform scale would carry a label below the step, the drawing holds the label at the step rather than shrinking it, and pitch/footprint clearing accounts for the labels actually drawn.

The lattice variant SHALL additionally draw the redesign draft's coordinate-field layers, which are pure decoration: each SHALL be non-interactive, SHALL be excluded from the accessibility tree, SHALL carry neither the node-marker nor the node-label component class that the geometry audit pairs every box of, SHALL introduce no tab stop, activation, or `data-node` identity, SHALL be static so the reduced-motion preference has nothing to disable, and SHALL encode no visibility state — the four-state shape ladder, its non-colour redundancy, the colourblind override, and every focus treatment SHALL be unaffected by their presence. Every colour they use SHALL resolve to a design token and no draft hex value SHALL be hardcoded for any of them. The three layers are:

1. **The coordinate dot field.** The lattice SHALL paint one dot per coordinate cell across its whole canvas, beneath every connector edge, node marker, node label, and axis line. The field's horizontal and vertical dot pitch SHALL equal the drawn column and row pitch, so one dot spacing is exactly one coordinate cell on each axis and the field states the coordinate space the lattice claims rather than a decorative texture; the field SHALL be registered to the exported placement, so for every drawn node a dot position coincides with that node's centre. Because the field is painted beneath the markers, an occupied cell SHALL show its node marker and never a marker and a dot together. The dot SHALL NOT read as a fifth node state: its radius SHALL scale with the marker ladder and SHALL remain strictly and materially smaller than the smallest node marker's radius, it SHALL carry no stroke, no label, and no state class, and the state legend SHALL gain no entry for it, so the legend's four states stay closed exactly as the beyond-state note rule requires.
2. **The knowledge-edge vignette.** Each map surface SHALL paint exactly ONE vignette treatment that darkens the canvas toward its edges, and that treatment SHALL be the knowledge edge — the limit of what the payload knows — and SHALL NOT be, or be styled as, terrain. It SHALL be a single full-canvas gradient wash with no fabricated geometry: no per-cell fill, no per-region fill, and no drawn shape tracing any terrain feature. The vignette SHALL NOT reduce the coordinate dot field below the presence floor below at any point of the canvas, so the far-field dots it is meant to make faint stay visible rather than being erased.
3. **The axis cross.** A surface SHALL draw a full-width and full-height axis line through the `current` node's drawn position ONLY where that same surface states the axis convention in words; a surface that states no orientation marks SHALL draw no axis, and the radial graph variant SHALL draw none on any surface because a graph asserts no axis. The axis SHALL be drawn beneath every node marker — it necessarily passes through the `current` node's own marker, which is what an origin is, and that crossing SHALL NOT be read as a violation of the non-overlap invariant, whose axis clause governs the edge direction markers in the gutter band.

The dot field's and the axis's presence and contrast SHALL be pinned as a band against the canvas ground, so neither an invisible layer nor one that out-shouts the drawing can ship. Each SHALL be present as a painted element whose resolved colour differs from the canvas ground; each SHALL keep a contrast ratio against that ground of at least 1.15:1 at every point of the canvas and at least 1.35:1 within the vignette's un-darkened inner field; and neither SHALL exceed the contrast that the connector-edge ink itself keeps against the same ground, so the coordinate decoration never reads louder than the topology it decorates. These layers are decoration, not information: the coordinate claim they picture is carried redundantly by the node placement itself, by the header's axis orientation marks, and by the readout's coordinate figure, so no reader depends on them — but the lattice's geometry is its claim, so they SHALL NOT be invisible.

Layout SHALL be computed in the DOM-independent render model, not as a rescaling of payload coordinates into a fixed pixel box, and the model SHALL export two placements for the same committed payload: a bounded integer lattice and a radial connected-graph. The lattice placement SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on it, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts; when that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The radial placement SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas; ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates. The radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant below is constructible from the model alone; neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning. The renderer SHALL size the map canvas from the exported placement and from the surface's own declared canvas geometry. A surface MAY declare a **fixed square canvas**; the island SHALL declare one of 240 CSS px, and the full-map surface declares none. A surface MAY instead declare a **fitted view**; the full-map surface SHALL declare one, and the island declares none. A fitted view SHALL show the placement's unchanged drawing — the same user-unit geometry, gutter, pitch, and type sizes the surface declares — through a uniformly scaled, translated window, and its opening fit, zoom bounds, pan, and recentre SHALL follow the full-map fit-view requirement. On a surface that declares a fixed square canvas, the canvas SHALL always render at exactly that size, its drawing SHALL be laid out in a square coordinate extent whose side is the larger of the declared size and the side the drawing requires, and the drawn uniform scale SHALL therefore be the declared size divided by that side: exactly 1 whenever the drawing fits and below 1 only when it does not, and NEVER above 1 — so no payload, however sparse, can inflate the designed marker radii, label size, marker-name size, or gutter offsets above the sizes the surface declares, and no maximum-upscale bound SHALL be needed or declared. Such a surface SHALL fill its square as follows, and SHALL NOT meet the fill by magnification:

- **Lattice variant — pitch before margin.** The drawn square pitch SHALL start from the derived minimum pitch below and SHALL grow, never shrink, toward the largest whole-unit pitch at which the node core — every lattice column and row plus the node-label band beneath the bottom row — fits inside the declared square less an inset: the edge-marker gutter band where the payload draws edge direction markers, and 8 CSS px on each side otherwise. The drawn pitch SHALL NOT exceed one and a half times the surface's declared pitch, so a sparse payload's coordinate cells stay recognisable as cells. Whatever room remains after the pitch is chosen SHALL be taken as **coordinate margin**, padded symmetrically around the node core on both axes up to the square, with the edge-marker band remaining the canvas's outermost band and the padded extent between the core and that band being coordinate space that the dot field paints. Where even the derived minimum pitch does not fit, the drawing SHALL keep that minimum pitch and the square extent SHALL grow to the required side. The island SHALL show a square window of side `canvasSize` over the drawing at scale 1, centred on the current node and clamped inside the drawing, clipped to the fixed canvas. Every drawn label SHALL remain at least 16 CSS px at the reference; the full-map surface SHALL keep the complete drawing reachable through its existing view operations.
- **Graph variant — readable window.** The fixed square window SHALL be centred on the radial placement's current node at one CSS pixel per user unit, clipping oversized radial drawings rather than shrinking their labels. The complete graph and every full name SHALL remain reachable on the full-map surface.

A surface that declares neither a fixed square canvas nor a fitted view SHALL draw at the placement's own size. The renderer SHALL accept no maximum-width or maximum-height cap and SHALL NOT resolve any cap into a width bound: no surface sizes its canvas by a cap, so there is no definite width to reconcile against a height cap and no engine-specific replaced-element constraint resolution can letterbox or distort a drawing. The canvas's own natural size SHALL NOT be able to breach the island's square however much the edge-marker gutter grows it: the gutter enlarges the drawing's required side, which the square window absorbs as clipping, never as a larger canvas or smaller text. No island size, pitch, or scale SHALL be derived from a measurement of the island's anchor, of the island's other rows, or of any other surface. The renderer SHALL NOT allow map content to overlap the island's title, its orientation marks, the readout line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The renderer's geometry — column pitch, row pitch, and marker sizing on the lattice, and ring radii, angular slots, and marker sizing on the radial graph — SHALL be chosen so that, at every placement the model can produce for either variant, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label — this holds independently of clipping by the island's fixed square canvas, independently of any uniform scale and translation the full-map surface's fitted view applies at any zoom level it permits, and independently of any pitch the island's fill grows beyond the derived minimum (radial ring radii SHALL grow with ring member count so the angular arc between adjacent slots bounds the label footprint). A connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects.

The lattice's pitch SHALL be **derived from what actually needs clearing at the drawn placement, not asserted as a constant**, and the derivation SHALL be constructible from the model and the drawn label set alone so the invariant above holds at every placement the model can produce. Three clearance terms SHALL be honoured. The **bare term** applies to every adjacent pair: the pitch SHALL clear the widest drawn footprint of each of the two markers — including any decoration drawn over a marker, such as the actionable halo, not merely the marker shape itself — with a strictly positive gap, SHALL leave a strictly positive visible connector segment between them, and SHALL keep each node's own label box clear of its own node's widest drawn footprint. The **vertical term** applies whenever an upper drawn node has a visible label and the cell directly below it contains a marker, even if that lower node has no visible label. The pitch SHALL reserve the label baseline, its descent, the lower marker's widest footprint and a strictly positive gap; it SHALL grow rather than allow the upper label to overprint the lower marker. The **label term** applies only where two horizontally adjacent cells BOTH draw visible label text: there the pitch SHALL additionally clear both label boxes actually drawn side by side with a half-em gap, `(cells(a) + cells(b)) / 2 × CELL_EM × labelFont + labelFont / 2` rounded up to a whole unit, where the visible (truncated) label is measured in monospace cells at the surface's declared label type size — a code point that the bundled monospace face draws one cell wide counts as one cell, and every other code point — East Asian Wide or Fullwidth characters, and characters the face lacks, which fall back to a wider face — counts as two cells, a cell being CELL_EM, the shipped face's Latin cell advance that the font manifest publishes — and the largest such need over every adjacent labelled pair binds. Two truncated labels of `labelMax` wide glyphs plus the narrow overflow indicator therefore need `(2 × labelMax + 1) × CELL_EM × labelFont + labelFont / 2`, never less than the former worst-case term `(labelMax + 1) × labelFont + 3`, while shorter or narrower names ask only for the room they occupy. Where the drawn label set contains no such adjacent pair — which a payload whose neighbouring cells state no place name of their own produces — the label term SHALL NOT bind, and the derived minimum pitch SHALL NOT be inflated to clear labels that are not drawn. The pitch these three terms derive is the **minimum**: a surface that declares a fixed square canvas MAY draw a larger pitch to fill its square, as the canvas-sizing rule above states, and SHALL NEVER draw a smaller one. The renderer SHALL NOT satisfy any term by truncating node labels more aggressively: `labelMax` is a legibility contract, and shortening it to buy pitch was rejected when the pitch was first derived. All applicable terms SHALL be satisfied by the same pitch on both axes, so a drawn lattice cell is **square**: an unequal pitch would draw a node at `(+1, +1)` along a different line than the edge direction marker for the same delta, which is computed from the raw coordinate delta, and the drawing and its bearings SHALL agree.

The map-rendering logic (node/marker placement consumption, connector edges, and per-node labels) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale and by layout variant (`lattice` or `graph`) rather than duplicated: the variant SHALL be resolved once, in the render-model layer, as a pure function of the payload's `layer` — the closed coordinate-bearing set (`grid`, `wilderness`) resolves to the lattice and every other layer resolves to the graph — and both surfaces consume that one resolved value, so island and overlay can never disagree. The state legend SHALL NOT be part of that shared canvas rendering: the full-map surface SHALL be the only surface that renders it, inside a legend popover it opens on request, and no legend element SHALL be mounted on the island for any payload. No map surface SHALL offer a layout switch or any other means for the player to choose a layout, and no layout choice SHALL be kept as a preference or in any client-side storage: the layout follows the data the world ships, not a setting. Both surfaces SHALL render the resolved variant's identical in-view nodes and edges for the same committed payload, the overlay's drawing shown whole through its fitted view within its own available space rather than on the minimap island's fixed small canvas, with the same non-overlap guarantee applying at every zoom level that view permits. The full-map overlay SHALL NOT render the island's coordinate readout line, since it states no coordinate figure at all. On the graph variant the full-map overlay SHALL render the payload's `remembered` nodes as a visible list outside its canvas — each entry pairing the remembered state's non-colour indicator with the node's full payload label as visible text, carrying no travel action, no activation, and no tab stop — and the minimap island SHALL NOT render that list in any visible form. On the lattice variant neither surface renders a remembered-node list.

The full-map overlay's map surface SHALL be framed in the draft `mapcanvas` treatment: a dark radial-gradient background painted with pure CSS (no fabricated terrain geometry), a rounded ink border, and a thin seal-toned ring concentric with the `current` node marker, drawn inside that node's own group at 10.5 units × the marker scale — an ornament of the real marker within its reserved footprint, not a second position claim; no teardrop or other pin is drawn above or beside the marker. That background IS the overlay's one knowledge-edge vignette, so the overlay SHALL NOT paint a second wash over it, and the dot field's contrast against the overlay's own canvas ground SHALL satisfy the same presence band as on the island. The overlay legend SHALL render inside its legend popover as draft dot-chips (a small colour chip paired with its text label); the chip border style SHALL additionally distinguish the remembered entry from the visited entry so the legend's distinctions do not rely on colour alone.

The island SHALL carry the payload's `title`, and its header SHALL stay a single row at every authored title length. `title` is server-authored and bounded only by the payload's 128-code-point ceiling, so the header SHALL be a localization-safe container: the title SHALL be the row's only elastic item — rendered on one line, truncated with an overflow indicator when it does not fit, and keeping its complete string available as the element's own tooltip/accessible text — while the orientation marks and every other header item SHALL be fixed-size items that neither shrink nor wrap. The header SHALL carry no full-map control of its own: the island's single full-map affordance is the full-bleed element specified below, so the header's fixed-size items are the orientation marks and nothing else unless a later change adds one. No authored or translated title SHALL be able to reflow the header onto a second line, and the island's card SHALL keep its constant width rather than being sized by its widest row, so neither the card's width nor the canvas's is a function of the title's length. On the lattice variant — which exactly the coordinate-bearing layers select — the island SHALL state the renderer's own axis orientation as orientation marks in its header and SHALL omit those marks otherwise rather than assert a direction or an axis the presentation does not support (a radial graph asserts no axis). Node `x`/`y` carry layer-scoped semantics: on the closed coordinate-bearing set (`grid`, `wilderness`) they are validated world coordinates and MAY drive relative-direction geometry; on every other layer they are renderer-local layout values and SHALL NOT be read as direction, distance, or place. The island's readout line SHALL state the `current` node's coordinates as a two-integer figure — that node's payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — whenever the payload layer is coordinate-bearing, and SHALL state nothing else: it SHALL NOT state the current node's place name, its visibility state, a movement destination, or any other label, because the canvas already marks the current node and the shell's own location surface already names the place. The readout SHALL NOT be driven by pointer hover or by node selection: the island SHALL hold no hovered-node and no selected-node state, and the readout SHALL be a pure function of the committed payload, so it describes where the player is after every move without any re-seeding and cannot go stale when a payload replaces the rendered one. The island SHALL NOT state a coordinate figure for any node other than the `current` node, on any layer, and the full-map overlay SHALL NOT state a coordinate figure at all. No surface SHALL render a compass angle, a bearing angle, a distance, or any coordinate figure beyond the permitted current-node figure; in particular the remembered-node edge markers convey direction only and never gain a coordinate readout. On a coordinate-free layer there is no coordinate figure, so the readout resolves to nothing and the empty-readout rule governs it unchanged: when the readout has nothing to state it SHALL state nothing and SHALL render no framed container, painting no box, rather than presenting an empty bordered widget; its row SHALL keep its one-line height so the island's size does not change with the layer. Removing the readout's label content SHALL NOT make any node's name unreachable: each in-view node's full label SHALL remain available as its on-canvas accessible name, and a remembered node's name SHALL remain readable — as the visible text of its edge marker on the lattice variant and of its entry in the full-map surface's remembered list on the graph variant — with its untruncated form always available to assistive technology on the island.

The island's readout SHALL adopt the redesign draft's closing-readout treatment as a token-driven rule rather than as a copy of the draft's declarations: it SHALL render at the island's smallest type step in the shared monospace font token, centred beneath the canvas, at a de-emphasised paper tier whose contrast against the island's panel background is at least 4.5:1, separated from the canvas by a step from the shared spacing scale, with no border, no background fill, and no padded box. No draft hex value and no draft-canvas pixel literal SHALL be hardcoded for it.

The island SHALL present exactly one full-map affordance, and that affordance SHALL carry no visible button chrome — no labelled control, icon button, or other visible trigger anywhere on the island. The affordance SHALL be a real `<button>` element spanning the island's whole box, transparent and layered beneath the island's visual content so the button element itself contains no focusable descendant, carrying 展開全地圖 as its accessible name. Activating it by pointer, by Enter, or by Space SHALL open the full-map surface through the platform's own button behaviour; no key handler on a non-button element SHALL stand in for it. The affordance SHALL be reachable in the island's tab order without the island's root element gaining a role or a tab stop of its own, and its focus-visible indication SHALL delineate the whole island rather than a small region of it. The affordance element SHALL be stable across committed payloads, so the full-map surface's opener — the focused element captured when that surface opens — still exists when it closes and focus is restored to it. The island's existing pointer convenience SHALL be unchanged: a click on the island's body SHALL open the full-map surface, a click that originates in an interactive descendant — an actionable lattice node or the affordance itself — SHALL run only that descendant's own behaviour, and every activation path SHALL open the full-map surface exactly once. The island SHALL carry no other tab stop and no other interactive descendant: neither an edge direction marker, nor a marker name, nor an entry of either text alternative SHALL be focusable or activatable, so the affordance remains the island's single keyboard path on every layout variant.

The presentation of `remembered` nodes SHALL follow the resolved layout variant, and each such node SHALL be presented exactly once on a given surface. Their payload coordinates SHALL NOT influence either exported node placement.

On the lattice variant, the named edge direction marker SHALL BE the presentation: each remembered node whose coordinates fall outside the drawn extent SHALL render as the remembered-node diamond ornament (carrying the gold landmark treatment when flagged) placed where the ray from the current node through that node's **raw payload coordinate delta** crosses the canvas's marker-safe border, with the direction computed by a pure helper over the raw delta (`+y = 北`, eight octants with deterministic sector bounds) and never from rank-compressed columns or rows, since compression preserves order, not ratios. The marker SHALL convey direction only — no distance figure, angle, or coordinate readout — and SHALL carry no activation of its own. The island SHALL NOT render a remembered-node list on this variant: the list is removed outright, and no surface SHALL present a remembered node both as a marker and as a list entry.

On every surface that draws edge direction markers — the island as well as the full-map overlay — each marker SHALL carry its place name as visible text beside it. The name SHALL be drawn wholly inside the marker gutter band that lies outside the canvas rect containing every node marker, every node label, the coordinate dot field's registered cells, and the axis — the rect the surface's coordinate-field padding grows, so the band stays the canvas's outermost band however much margin is taken — so a marker name can never intersect a node marker, a node label, or the axis line that surface now draws. Markers and their names SHALL be positioned deterministically so that no marker overlaps another marker and no name overlaps another name. The room a name may occupy SHALL be declared in the terms the placement helper consumes — the band depth every surface reserves, and, on a surface that draws its names OUTWARD across that band rather than along it, an outward name box — so the room is reserved before the names are drawn rather than discovered afterwards. **Each name SHALL then be fitted to what that same declared geometry reserved for it, and no surface SHALL draw a name longer than the room its own declaration set aside.** The fit budget SHALL be the lesser of two terms measured in the same monospace cells (one for a code point the bundled monospace face draws one cell wide, two for every other code point, each CELL_EM of the shipped face's Latin cell advance) at the surface's declared name type size: the free span the marker holds along its own edge, and — only where that marker's name is drawn outward across the band — the declared outward name box, which SHALL be declared wide enough for `labelMax + 1` wide glyphs. A surface that declares band depth alone, drawing its names along the band, has no outward term and is bound by its span alone. The number that budgets the fit SHALL be the same number that sizes the drawn glyph, so a surface cannot size its text by one measure and reserve room by another. Where a name does not fit that budget it SHALL be truncated with an overflow indicator, and **no surface SHALL draw two equal marker names while the payload labels behind them differ**: rather than asserting that two distinct places are one place, it SHALL drop the visible name of a marker it cannot distinguish, keeping that marker's position, bearing, and state indicator. That rule binds every surface that fits names, not only the smaller one. A dropped or truncated visible name SHALL NOT reduce what a reader can obtain: every drawn marker's untruncated payload label SHALL remain available through the surface's assistive-technology text alternative.

Because the markers carry no activation and are drawn inside a graphic, the lattice variant's complete reading path SHALL be a text alternative that mirrors the drawn marker set one entry per drawn marker, in a deterministic order, each entry stating that marker's untruncated payload label together with its direction as one of the eight octant names (`北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北`). Naming the octant in words is permitted on that mirror; a numeric bearing, an angle, a distance, and any coordinate figure beyond the permitted current-node figure remain forbidden on every surface. The mirror SHALL be derived from the same marker set the surface draws, so it can neither omit a drawn marker nor invent one, and SHALL introduce no additional tab stop: the island's tab order SHALL remain exactly its single full-map affordance, and neither the markers nor the mirror SHALL be focusable.

Coordinate-free payloads SHALL render no edge direction markers, because a radial graph draws no canvas edge for a bearing to cross and its node `x`/`y` are renderer-local layout values. On the graph variant, therefore, the island SHALL present its remembered nodes only through an assistive-technology text alternative: a visually hidden, non-focusable list with one entry per `remembered` node in payload order, each stating that node's untruncated payload label and no direction, no distance, and no coordinate figure. The island SHALL render no visible remembered-node list, chip, or entry on any variant, so the number of places the player has visited can never change the island's size or crowd its canvas. The visible presentation of those nodes is the full-map surface's remembered list, which the island's single full-map affordance opens in one activation, so a sighted reader without assistive technology can always read every remembered place. No remembered node on that variant SHALL be placed on the canvas or on its border, since a position there would assert a bearing the payload does not carry. Edges SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer. The `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged.

#### Scenario: The island mounts no state legend
- **WHEN** an available `local_map` payload renders on both the minimap island and the full-map overlay
- **THEN** no legend element exists anywhere in the island's DOM, and once the reader opens the overlay's legend popover it renders the payload's full legend with its dot-chips and text labels

#### Scenario: A remembered place is readable and offers no travel action
- **WHEN** a remembered remote node is presented — as a named edge direction marker on the island's lattice variant, as a text-alternative entry on the island and a visible list entry on the full-map surface on the graph variant
- **THEN** its name and its landmark treatment are shown wherever it is drawn, its untruncated name is available to assistive technology on the island, and there is no move or travel control for it and no activation of its own on either surface

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (marker shape, border, or text label) on the island without any legend — the remembered state by its diamond ornament on the canvas border, named beside it — and the overlay legend's text labels are readable

#### Scenario: Reconnect rebuilds from persisted knowledge
- **WHEN** the WebSocket reconnects and a new-epoch snapshot arrives
- **THEN** the minimap is rebuilt from the server-persisted visited record and current location, and no client-stored map state is treated as authoritative

#### Scenario: Unknown panel schema disables only the minimap
- **WHEN** a received `local_map` payload fails its exact schema
- **THEN** only the minimap renderer is disabled, the browser requests at most one full resynchronization, and narrative and text input remain usable

#### Scenario: In-view nodes occupy distinct lattice cells
- **WHEN** a grid-layer payload places several in-view nodes at distinct coordinates
- **THEN** each node occupies its own lattice cell, no two node markers overlap, and their relative row and column order matches the payload coordinates

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
- **WHEN** the island omits or truncates a marker's visible name — the fit-to-span rule shortened it, or the ambiguity rule dropped it — and the reader is a sighted keyboard-only user with no assistive technology running, so neither the visually-hidden mirror nor a hover tooltip on the `pointer-events: none` marker layer can serve them
- **THEN** activating the island's single full-map affordance opens a readable full-map window at scale 1; its pan and focus-reveal paths reach the gateway's visible name and accessible name at 16 CSS px or more, and its declared name capacity SHALL be strictly larger, on the same payload, than the island's span capacity, so the reader can read strictly more of the name and read it whole whenever the authored label is within the overlay's capacity

#### Scenario: The disclosure chain ends at the largest surface's declared capacity
- **WHEN** an authored gateway label is longer than the declared name capacity of the surface with the largest one, so even that surface must fit it
- **THEN** that surface draws the fitted name with its overflow indicator and carries the untruncated label as the marker's accessible name, and it SHALL NOT instead draw the name past its reserved box: a name that overruns its box overprints the canvas rect — the node markers, the node labels and the axis the invariant above protects — or its neighbouring marker's name, so it discloses nothing, and the bounded name with its overflow indicator is the surface's final visible answer

#### Scenario: A drawn marker name never exceeds the room its surface reserved
- **WHEN** the full-map overlay draws an edge direction marker whose authored payload label is longer than the outward name box that surface declared to the placement helper — the box the helper used to size the marker band and the along-edge slots
- **THEN** the drawn name is fitted to that declared capacity with an overflow indicator rather than drawn at full length past the reserved box, so the geometry the helper reserved and the text the renderer draws agree on every surface instead of only on the island

#### Scenario: The binding term follows how the surface draws its names
- **WHEN** one surface draws its marker names outward across the band while another draws them along the band, and both fit the same authored label
- **THEN** the outward-drawing surface's budget is bounded by its declared outward name box as well as by its along-edge span, the along-drawing surface's budget is bounded by its span alone because it declares no outward box, and neither surface's drawn name exceeds the room its own declaration reserved

#### Scenario: A crowded overlay edge keeps its names apart
- **WHEN** several remembered gateways carrying long authored labels leave through one canvas edge of the full-map overlay, enough that the placement helper's along-edge slots reach their floor
- **THEN** each name is fitted to its own slot, no two drawn marker-name boxes intersect, and no name box leaves the marker band for the canvas rect

#### Scenario: Marker names never collide with each other, a node label, or the axis
- **WHEN** a lattice payload places remembered markers on several canvas edges, including two on one edge, while the drawn lattice carries in-view node labels at the renderer's truncation length and the island draws the axis cross that the invariant names
- **THEN** every marker name is rendered wholly inside the marker gutter band outside the canvas rect — the rect the coordinate-field padding grows, so the band stays outermost — so no marker name's box intersects any node marker, node label, or the drawn axis line, and no two marker names' boxes intersect each other

#### Scenario: Rank compression never skews a marker's direction
- **WHEN** an in-view span forces rank compression while a remembered remote sits at a lopsided raw delta such as (+100, +1)
- **THEN** its edge marker renders on the near-due-east border rather than on the 45° diagonal that the compressed ranks would suggest

#### Scenario: A coordinate-free payload draws no edge markers and still presents its remembered nodes
- **WHEN** an interior or instance payload with remembered nodes renders the radial graph on the island and on the full-map surface
- **THEN** no edge direction marker is rendered and no remembered node is placed on either canvas or its border, the island renders no visible remembered-node list element and exposes one visually hidden, non-focusable text-alternative entry per remembered node stating its untruncated name, and the full-map surface renders a visible list with one entry per remembered node, each showing the node's full name with its non-colour state indicator and no travel action

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
- **WHEN** the committed payload's layer is coordinate-bearing
- **THEN** the island states the renderer's axis orientation marks in its header, the readout line states the current node's two payload coordinates as its entire content, and no compass angle, distance, or other-node coordinate figure is rendered anywhere in the island

#### Scenario: The readout states the coordinate figure and nothing else
- **WHEN** a wilderness payload whose current node is labelled 西部丘陵與谷地 at (60, 107) renders on the island
- **THEN** the readout line reads exactly the two-integer coordinate figure for (60, 107), it carries no place name, no 目前所在 or other visibility-state word, and no movement destination, and the place name appears instead on the shell's own location surface

#### Scenario: Hovering or activating a node never changes the readout
- **WHEN** the player hovers a non-current node, then activates one, on a coordinate-bearing layer
- **THEN** the readout line still states the current node's coordinate figure and nothing else, no coordinate figure for the hovered or activated node is rendered anywhere, and the island holds no hovered-node or selected-node state that the readout could go stale on

#### Scenario: A node's name stays reachable without the readout
- **WHEN** an in-view node's label is truncated on the island's canvas and a remembered node is presented alongside it
- **THEN** the in-view node's full label is still available as its on-canvas accessible name and the remembered node's name is still readable — as its marker's visible text on the lattice variant, as its full-map list entry's visible text on the graph variant, and untruncated through the island's text alternative on both — so removing the readout's label content makes no node's name unreachable

#### Scenario: A screen-reader user can still reach every remembered place
- **WHEN** a screen-reader user reads the minimap island on a wilderness payload carrying several remembered gateways, none of which is focusable and each of which is drawn inside the map graphic
- **THEN** the island exposes one text-alternative entry per drawn marker, in a deterministic order, each stating that place's untruncated authored name and its direction as one of the eight octant names, so no remembered place is reachable only by sight

#### Scenario: Replacing the list adds no tab stop and no activation
- **WHEN** a keyboard user tabs through the island on a payload carrying the maximum number of remembered gateways
- **THEN** the island still offers exactly one tab stop — its full-map affordance — neither an edge direction marker nor the text alternative is focusable, and activating anything on the island still opens only the full-map surface or submits only a lattice node's own move

#### Scenario: A coordinate-free layer asserts no orientation and no coordinates
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure, the map title renders exactly as on a coordinate-bearing layer, and the readout line — having nothing to state — states nothing and paints no box

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a schema-valid payload places in-view nodes at coordinates whose span exceeds the lattice bound
- **THEN** the model falls back to rank compression, the lattice stays within its bound, and every node is still rendered exactly once

#### Scenario: Adjacent node markers, labels, and connector edges never visually collide
- **WHEN** a grid-layer payload places two or more nodes in adjacent lattice cells (sharing a row or a column), each carrying a label at the renderer's normal truncation length
- **THEN** the rendered bounding box of each node's marker and label does not intersect the bounding box of any other node's marker or label, and the connector edge between two adjacent nodes remains visually distinguishable rather than being fully covered by their markers

#### Scenario: A densely populated lattice keeps readable collision-free geometry
- **WHEN** the derived pitch of a dense lattice exceeds the island's 240px square
- **THEN** its unchanged geometry is clipped through a scale-1 window around the current node, every drawn label remains at least 16 CSS px, and the full-map view operations reach the complete drawing without marker/label collisions

#### Scenario: A sparse lattice scaled up never reintroduces overlap
- **WHEN** the payload's node core at its derived minimum pitch is smaller than the island's square, so an earlier revision of this surface would have scaled the whole SVG up to fill it
- **THEN** no scale above 1 is produced at all: the island's fill is taken first as pitch grown from the derived minimum and then as symmetric coordinate margin around the node core, never as magnification, so the drawn scale is `canvas side / side ≤ 1` and the upward direction of the non-overlap question cannot arise

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** a graph-variant payload combines a two-ring in-view placement with the model's maximum of remembered nodes
- **THEN** the island lays out no remembered-node list at all, its canvas is still 240 × 240 CSS px at the 1451x790 reference viewport (the canvas never depends on payload content, and the chrome factor magnifies it uniformly at every larger viewport), its title and readout row keep their places, the island's size equals its size for the same placement with no remembered node, and no required island content has to be scrolled out of view

#### Scenario: The name gutter never hands the anchor a scrollbar
- **WHEN** remembered markers grow the lattice's drawing beyond the fixed island canvas
- **THEN** the canvas stays 240 × 240 CSS px, its current-centered scale-1 window clips the oversized drawing, its effective text remains at least 16 CSS px, and the anchor has no scrollbar

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** the in-view lattice contains exactly one node
- **THEN** its marker and label render with no neighboring node to collide with, and the fix's pitch and sizing changes produce no regression versus the single-node case

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay while a committed `local_map` payload is available
- **THEN** the overlay retains the identical in-view nodes and edges in the same resolved layout variant, opens a readable current-centered window at scale 1 with the complete drawing reachable through pan and focus reveal, offers the state legend in its popover, has no marker or label collisions at any permitted zoom, and has no coordinate figure on the overlay surface

#### Scenario: The full-map overlay omits the remembered-node list and the readout line
- **WHEN** the full-map overlay is open with an available lattice payload carrying remembered gateways
- **THEN** the overlay body shows only its guide row, the map canvas with its view controls and legend popover control floating over the canvas's top-right corner, in the lattice variant with its named edge markers, and does not render a remembered-node list or the island's coordinate readout line

#### Scenario: The full-map overlay lists a graph payload's remembered rooms
- **WHEN** the full-map overlay is open with an available interior payload carrying remembered rooms
- **THEN** the overlay body shows its guide row, the map canvas in the graph variant with its view controls and legend popover control floating over the canvas's top-right corner, and a visible remembered list outside the canvas and below it with exactly one entry per remembered room in payload order, each pairing the remembered state's non-colour indicator with the room's full name, carrying no tab stop, no role that invites activation, and no travel action, and the body renders no coordinate readout line

#### Scenario: Draft marker ladder reads without colour
- **WHEN** the island renders a current node, a visited node, an unvisited node, and a landmark node
- **THEN** the current node is the large seal-stroked circle, the visited node is a smaller solid circle, the unvisited node is a smaller hollow circle, the landmark carries the gold treatment, and no two states share a shape

#### Scenario: Map chrome colours resolve to design tokens
- **WHEN** either map surface renders its chrome
- **THEN** every marker, edge, label, and legend colour resolves to a design token value, and the draft seal pair and label tiers match the tokens added with this change

#### Scenario: The overlay pin adorns the current marker without claiming a position
- **WHEN** the full-map overlay renders a payload with a current node
- **THEN** exactly one current-location ring renders, as a child of the current node's own group and concentric with its marker, no teardrop pin renders anywhere, and the ring carries no node label, accessible name, pointer target, or activation of its own

#### Scenario: Overlay legend chips stay text-labelled with non-colour redundancy
- **WHEN** the overlay legend renders for a payload
- **THEN** each chip pairs its colour swatch with its text label, and the remembered chip's border style differs from the visited chip's

#### Scenario: The radial placement is deterministic and edge-honest
- **WHEN** the model computes the radial placement for a payload whose in-view nodes are joined by edges
- **THEN** the current node sits at the centre, every other in-view node sits on the ring of its BFS exit-hop distance (edgeless in-view nodes on the outermost ring), and re-running the pass on the same payload produces identical coordinates

#### Scenario: The resolved layout preserves nodes, edges, and actions
- **WHEN** payloads on a coordinate-bearing layer and on a coordinate-free layer are committed in turn
- **THEN** each renders the resolver's variant with the same in-view nodes, edges, and per-node move actions, no marker or label overlaps in either, no compass angle or distance figure appears in either, and the map chrome exposes no layout control element at any point

#### Scenario: The orientation mark follows the resolved layout
- **WHEN** the payload's layer resolves to the graph variant (`interior`, `instance`)
- **THEN** the island renders no axis orientation mark and no coordinate figure, and on a layer resolving to the lattice (`grid`, `wilderness`) the mark renders alongside the current node's coordinate figure

#### Scenario: The island's canvas claims its content width as coordinate margin
- **WHEN** a wilderness payload whose three-by-three in-view core carries no remembered gateway and no horizontally adjacent labelled pair renders on the island, where its derived minimum pitch is 40 user units
- **THEN** the drawn square pitch is 60 user units — the grown pitch reaches the 60-unit cap of one and a half times the declared pitch at the 240px square's roomier inset box (three columns, three rows, and the 14-unit label band fit 240px less its 16px inset) — so the node core spans 180 of the canvas's 240 CSS px instead of 120, the remaining room is painted as coordinate margin by the dot field registered to the 60-unit pitch, the uniform scale is exactly 1, and every marker radius and label renders at the size the island declares

#### Scenario: The island's name band is reserved as band depth, not as an outward box
- **WHEN** the reported three-by-three wilderness shape renders with remembered gateways and vertically adjacent visible labels
- **THEN** the marker band reserves name depth, the square pitch satisfies the derived vertical clearance as well as horizontal clearance, and the 240px current-centered window draws labels at 16 CSS px without overlap

#### Scenario: A sparse payload reads airy rather than magnified
- **WHEN** the committed payload contains a single node and renders on the island
- **THEN** the pitch grows only to its 60-unit cap of one and a half times the declared 40-unit pitch, the rest of the 240px square is coordinate margin, so roughly three and a half coordinate cells of dot field surround one marker drawn at its designed radius with its label at the island's declared 16-unit type size — exactly 16 CSS px, the island's own 16px chrome step and never above it — and neither the marker ladder nor the label is inflated
- **AND** no maximum-upscale bound is declared for the island at all, and the island's canvas carries no width or height bound derived from a measurement

#### Scenario: The height budget is spent as an equivalent width bound
- **WHEN** a two-column, sixty-four-row lattice renders on a natural mount, the island, and the full map
- **THEN** the natural mount has no inline size cap; the island clips it at scale 1 inside its 240px square; and the full map opens a readable window with pan/zoom/recentre, never an equivalent width cap or below-floor text

#### Scenario: A graph payload is cropped to its footprint and never magnified
- **WHEN** an interior graph containing one node and then a graph containing many neighbors renders on the island
- **THEN** both use a fixed 240-unit square window centered on the current node, render labels at exactly 16 CSS px at reference, and leave every full name reachable through the full map

#### Scenario: The overlay keeps its geometry and gains only the coordinate field
- **WHEN** the same committed payload renders in the full-map overlay, which declares neither a fixed square canvas nor an axis
- **THEN** the overlay's column pitch, row pitch, label truncation length and marker scale are all exactly what they were before this change, its node-label and marker-name type steps rise to the same 16-unit legibility floor the island declares, no pitch-fit or footprint crop is applied to it, its drawing is shown through its fitted view rather than stretched to the overlay body's width, it paints no second vignette over its `mapcanvas` background, and it draws no axis — the one layer it carries beyond the markers is the coordinate dot field, because the dot pitch's meaning belongs to the lattice variant rather than to a surface
- **AND** the conditional label term of the pitch derivation never binds there, because the widest truncated label (`2 × labelMax + 1` cells) plus its half-em gap at the overlay's label type size is smaller than either of its declared pitches

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
- **WHEN** an available `local_map` payload renders on the island
- **THEN** exactly one full-map affordance exists in the island, it is a `<button>` element spanning the island's whole box with 展開全地圖 as its accessible name, no labelled control or icon button is rendered in the island's header or anywhere else in the island, and the island's root element carries no role and no tab stop of its own

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
- **WHEN** a wilderness payload renders the lattice on the island and in the full-map overlay
- **THEN** each surface paints a coordinate dot field across its whole canvas whose horizontal dot spacing equals that surface's drawn column pitch and whose vertical spacing equals its drawn row pitch, and for every drawn node a dot position coincides exactly with that node's centre, so one dot spacing is one coordinate cell and the field is registered to the exported placement rather than being an unregistered texture

#### Scenario: A field whose pitch stopped meaning one cell is rejected
- **WHEN** the drawn pitch changes — because the payload's drawn label set moves the lattice from the field pitch to the label-cleared pitch, because the island's square fill grows the pitch beyond its derived minimum, or because a surface declares a different pitch
- **THEN** the dot field's spacing changes with it on both axes and stays registered to the node centres, so no rendering exists in which the dot spacing and the coordinate cell step differ

#### Scenario: A coordinate field that went invisible fails
- **WHEN** the island's lattice renders and the resolved colours of the dot field and the axis are measured against the canvas ground
- **THEN** each layer exists as a painted element whose resolved colour differs from the ground, each keeps a contrast ratio of at least 1.15:1 at every point of the canvas and at least 1.35:1 in the vignette's un-darkened inner field, and neither exceeds the contrast the connector-edge ink keeps against the same ground — so a layer shipped at zero opacity, at the ground colour, or louder than the topology all fail

#### Scenario: The dot field never reads as a fifth node state
- **WHEN** the island and the overlay render a payload carrying current, visited, unvisited, and landmark nodes over the coordinate field
- **THEN** every dot is materially smaller in radius than the smallest node marker, carries no stroke, no label, no state class, no `data-node` identity, and no activation, an occupied cell shows its node marker with no dot drawn over or beside it, the state legend gains no entry for the field, and the four visibility states remain distinguishable without colour exactly as before

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** the island's lattice renders its canvas edges
- **THEN** exactly one vignette element darkens the canvas outward as a single full-canvas gradient wash, no per-cell fill, per-region fill, or shape tracing any terrain feature is introduced anywhere, and the overlay — whose `mapcanvas` background already is its one vignette — paints no second wash

#### Scenario: The vignette never erases the far-field dots
- **WHEN** the payload renders on the island and the dots nearest the canvas corners are measured through the vignette
- **THEN** those dots still clear the presence floor against the darkened ground there, so the layer that makes the far field faint does not delete it, and an outer vignette opacity strong enough to take them below the floor is not permitted

#### Scenario: The axis is drawn only where the convention is stated in words
- **WHEN** a coordinate-bearing payload renders on the island, which states `北↑ 東→` in its header, and in the full-map overlay, which states no orientation marks
- **THEN** the island draws a full-width and full-height axis line through the current node's drawn position beneath every node marker, and the overlay draws none — asserting no axis on a surface that names none

#### Scenario: The axis crossing the current marker is not a collision
- **WHEN** the island draws its axis through the `current` node
- **THEN** the axis passes beneath that node's own marker, which is what an origin is, the drawn edge direction markers stay wholly outside the canvas rect that contains the axis, and the non-overlap invariant that names the axis is satisfied

#### Scenario: The graph variant draws no coordinate field and no axis
- **WHEN** an interior or instance payload renders the radial graph on either surface
- **THEN** no coordinate dot field and no axis line is drawn anywhere on that surface, because a radial placement has no coordinate cells and asserts no axis, its markers, edges, and labels render exactly as before, and the full-map surface's legend popover lists the same entries as on a lattice payload

#### Scenario: A node label never renders larger than the surface's own chrome
- **WHEN** a sparse or crowded payload renders on the island
- **THEN** every drawn node label is exactly its declared 16-unit step at reference scale, never smaller through SVG scaling and never larger than the island's title

#### Scenario: The pitch clears exactly what the drawn label set needs
- **WHEN** a wilderness payload suppresses shared-region labels and another payload shows distinct adjacent names
- **THEN** horizontal clearance binds only for pairs of visible names, vertical clearance binds for every labeled upper node above a lower marker including an unlabeled one, and the square pitch satisfies all applicable footprint terms without more aggressive truncation

#### Scenario: Vertical clearance is derived even above an unlabeled marker
- **WHEN** visible labels occur on vertically adjacent lattice rows
- **THEN** the derived square pitch grows above the declared floor enough to keep every upper label clear of the marker beneath it, even if that marker has no label, and a fixed canvas clips rather than defeating clearance or reducing text size

#### Scenario: The drawn cell is square so the lattice and its bearings agree
- **WHEN** a lattice payload places a node one cell east and one cell north of the current node while a remembered gateway sits at the same raw coordinate delta
- **THEN** the node is drawn along the same line the edge direction marker's raw-delta ray follows, because the drawn column and row pitch are equal, and the dot field's cells are square on that surface

#### Scenario: The decoration layers stay out of the audit and the accessibility tree
- **WHEN** the browser geometry audit collects every node-marker box and every node-label box on the island's canvas, and a screen reader reads the island
- **THEN** the dot field, the vignette, and the axis contribute no box to either collection because they carry neither component class, they intercept no pointer event, they add no tab stop and no accessible name, and the island still exposes exactly one tab stop — its full-map affordance

#### Scenario: Reduced motion and the non-colour encoding are unaffected
- **WHEN** the island renders with the reduced-motion preference active and with the colourblind override on
- **THEN** none of the three new layers animates or transitions anything, none carries a visibility state, the four-state shape ladder and its non-colour redundancy are unchanged, and every focus treatment behaves exactly as before

#### Scenario: The lattice colours resolve to existing tokens with no draft literal
- **WHEN** the coordinate field, the vignette, and the axis render on either surface
- **THEN** each layer's colour resolves to a design token already defined for the map surfaces, no new token is required, and no draft hex value and no draft-canvas pixel literal is hardcoded for any of them

#### Scenario: The island scales once with the desktop chrome factor
- **WHEN** the same payload renders on the island at 1451x790 and at 2560x1440
- **THEN** the canvas is 240 × 240 CSS px at 1451x790 and 336 × 336 CSS px (±1) at 2560x1440 (the 1.4 cap), the SVG's viewBox, pitch, marker radii and label sizes in user units are identical for both, and the drawing is only uniformly magnified

#### Scenario: Labels are budgeted in monospace cells
- **WHEN** two horizontally adjacent lattice cells draw the labels `霧骨渡口` and `NPC 7`, and an edge marker's name mixes CJK and ASCII
- **THEN** the pitch clears `(8 + 5) / 2 × CELL_EM × labelFont + labelFont / 2`, where `CELL_EM` is the shipped face's Latin cell advance in em, each CJK code point counting as two cells and each ASCII code point as one, and the marker name is fitted to its span and outward box by the same cell measure, so a monospace face whose wide glyphs are two Latin cells wide stays inside every reserved box


### Requirement: The full-map surface opens fitted to its body and offers zoom, pan, and recentre
The full-map overlay SHALL present its map through a clipped viewport that takes the overlay body's
height left after its one-line guide row and, on the graph variant, its remembered list, so neither
row can push the map out of the body and the body needs no scrolling to show the map. The map SHALL
be drawn inside that viewport through a window onto the unchanged drawing: zooming and panning SHALL
change only a uniform scale and a translation of the whole drawing, never the placement, the pitch,
the edge-marker gutter, the marker radii, the label and marker-name type sizes, the name fitting, or
any other geometry the surface declares, so every rule the shared renderer states about that
geometry — including the non-overlap invariant — holds at every zoom level.

Each time the overlay opens, the view SHALL open at one CSS pixel per user unit, so every declared 16-unit label remains at least 16 CSS px. A drawing smaller than the viewport SHALL be centred on each non-overflowing axis; an oversized drawing SHALL open around the current node, clamped to the drawing's edges, rather than shrinking text to show all nodes at once. The zoom level SHALL be bounded below by one and above by two CSS pixels per user unit. The complete drawing SHALL remain reachable by the existing pan, zoom, focus-reveal and remembered-list paths without dropping topology.
While the reader has not zoomed, panned, or recentred, a viewport resize or moved-current payload SHALL recreate that default readable view. Once touched, a resize SHALL preserve the viewport's center point subject to bounds, a moved-current payload SHALL center the new current node at the reader's scale, and any other replacement SHALL only re-clamp the view. No zoom, window position or popover state SHALL persist between openings; each opening SHALL restore the default readable view and close the legend popover.

The surface SHALL offer these view operations:

- **Zoom.** A mouse wheel over the viewport SHALL zoom about the pointer, keeping the drawing point
  under the pointer fixed, and SHALL NOT scroll the body or the page. The `+` key (and `=`) and the
  `-` key SHALL zoom in and out by a fixed step about the viewport's centre while focus is inside
  the overlay; a key pressed with Ctrl, Meta, or Alt SHALL be left to the browser. Labelled
  `放大` and `縮小` buttons in the view-control group floating over the map's top-right corner SHALL do the same.
- **Pan.** Dragging with the primary pointer button SHALL move the window with the pointer, and SHALL
  stop at the drawing's edges so no empty space opens beyond a canvas edge on an axis where the
  drawing is larger than the viewport. A press that moves more than a small threshold is a drag: it
  SHALL NOT activate the node it started or ended on, so a drag never submits a move. A press that
  stays within the threshold is an ordinary click, so pointer travel on an actionable node is
  unchanged.
- **Recentre.** A labelled `置中` button in that view-control group SHALL centre the `current` node in the
  viewport at the current zoom level, clamped to the drawing's edges.

Each view control SHALL be a real `<button>` with an accessible name. A control whose operation
cannot apply — zoom in at the upper bound, zoom out at the readable bound, `置中` on a payload with no
current node — SHALL state that it is unavailable to assistive technology and SHALL do nothing when
activated, and SHALL stay focusable so focus never falls out of the overlay's focus trap. The
keyboard path SHALL remain: every actionable node stays a tab stop in the overlay's focus order and
still moves on Enter or Space, and when a node receives focus outside the visible window the view
SHALL pan — at the current zoom level, only as far as needed — so that node's marker and label are
visible with a margin. The guide row SHALL name the gestures in words. No view operation SHALL
animate, so the reduced-motion preference has nothing to disable and a reduced-motion reader sees
exactly the same frames.

The state legend SHALL NOT occupy the overlay body's layout. It SHALL open from a `?` disclosure
button in that view-control group named 圖例, which states whether the popover is expanded; the popover SHALL
float above the top-right of the map viewport, SHALL hold the payload's full legend with its
dot-chips and text labels and no focusable content, and SHALL be absent from the DOM while closed.
It SHALL close on a second activation of its button, on a pointer press inside the overlay outside
the popover and its button — without consuming that press, so a drag or a node activation still
proceeds — and on Escape. Escape while the popover is open SHALL close only the popover and SHALL
NOT close the overlay; the next Escape closes the overlay.

#### Scenario: A tall map opens readable around the current node
- **WHEN** the player opens an oversized tall lattice or wilderness map with named edge markers at 1451x790
- **THEN** the current node is visible at a scale of 1, labels and marker names draw at least 16 CSS px, the overlay body has no scrollbar, and panning reaches every node and edge marker

#### Scenario: A small map opens at its declared size, not magnified
- **WHEN** the player opens the full-map overlay on a single-node payload
- **THEN** the node is centred in the viewport, its marker and label render at the overlay's declared
  sizes at one CSS pixel per user unit, and nothing is scaled above that

#### Scenario: The remembered list never pushes the map out of view
- **WHEN** the player opens the full-map overlay on an interior payload carrying sixteen remembered
  rooms
- **THEN** the remembered list renders below the viewport, the radial drawing remains reachable through the readable viewport, and the overlay body shows no scrollbar

#### Scenario: Wheel and keys zoom within bounds
- **WHEN** the reader turns the wheel forward over a node, then presses `-` repeatedly, then presses
  `+` repeatedly
- **THEN** the wheel enlarges the drawing while the node under the pointer stays under the pointer,
  `-` stops at scale 1 with readable text and the zoom-out control stating it is
  unavailable, `+` stops at two CSS pixels per user unit with the zoom-in control stating it is
  unavailable, and the page and the overlay body never scroll

#### Scenario: A drag pans and never moves the player
- **WHEN** the reader zooms in, presses the primary button on an actionable node, drags well past the
  threshold, and releases over another actionable node
- **THEN** the drawing moves with the pointer, stops at the drawing's edges, and no move is submitted;
  a subsequent press-and-release on an actionable node without movement submits that node's move
  exactly once

#### Scenario: 置中 returns to the current node
- **WHEN** the reader zooms in, pans the current node out of the viewport, and activates `置中`
- **THEN** the current node's marker is at the viewport's centre, or as near it as the drawing's edges
  allow, and the zoom level is unchanged

#### Scenario: Keyboard travel reveals the focused node
- **WHEN** a keyboard user zooms in so that an actionable node lies outside the viewport and then tabs
  to that node and presses Enter
- **THEN** the view pans at the same zoom level until the node's marker and label are inside the
  viewport, and Enter submits that node's move exactly once

#### Scenario: Travel recentres only a touched view
- **WHEN** a payload moving the current node commits once while the view is still fitted, and again
  after the reader has zoomed in; and a payload with the same current node commits while the reader
  has panned elsewhere
- **THEN** the first restores the readable current-centered default, the second centres the new current node at the reader's
  zoom level, and the third leaves the reader's window where it was

#### Scenario: The legend opens in a popover and Escape closes it first
- **WHEN** the reader opens the full-map overlay, activates the 圖例 button, presses Escape, and presses
  Escape again
- **THEN** no legend element exists before the button is activated and the map viewport's box does
  not change when the popover opens; the button states it is expanded while the popover shows the
  full legend; the first Escape closes only the popover with focus still on the 圖例 button; and the
  second Escape closes the overlay and restores focus to its opener

#### Scenario: Nothing about the view is remembered
- **WHEN** the reader zooms, pans, and opens the legend popover, closes the overlay, and opens it again
- **THEN** the overlay opens fitted with the popover closed, and no preference, client storage, store
  field, or server message carries a zoom level, a window position, or a popover state

#### Scenario: Reduced motion loses nothing
- **WHEN** the reader zooms, pans, recentres, and opens the legend with the reduced-motion preference
  active
- **THEN** every operation takes effect in the same frame as without the preference, because no view
  operation animates


### Requirement: Map chrome and ordinary node labels are legible without dropping topology
The minimap island's title, orientation marks and readout SHALL render at the shared `--text-xs` step (16 CSS px at the reference scale), which is the island's one and smallest chrome step, and the full-map overlay's guide, input hint, view controls, legend and remembered list SHALL render at 16 CSS px or more through the shared type tokens; neither surface SHALL hardcode a map chrome type size below that step. The island SHALL draw every node label and marker name at its declared 16-unit step with an effective rendered size of at least 16 CSS px at reference, and at least 22.4 CSS px at the desktop chrome cap. Oversized lattice and graph drawings SHALL be clipped through a current-centered scale-1 window rather than shrinking labels; all nodes and edges SHALL remain in the model, every node SHALL retain its full text alternative, and the full map SHALL make every full name and remembered gateway reachable at its readable scale floor through existing view controls. The derived lattice pitch SHALL satisfy horizontal and vertical footprint clearance for the actual drawn label set.

#### Scenario: Ordinary neighbourhood is readable
- **WHEN** a three-by-three grid lattice of distinct two- and four-glyph room names with no remembered gateway renders on the island at 1451x790 and at 2560x1440
- **THEN** the title, orientation marks and readout compute to 16 CSS px at the reference viewport, the drawing's scale is 1, every drawn node label is at least 16 CSS px at the reference viewport (and at least 22.4 CSS px at 2560x1440, the same labels at the 1.4 chrome cap) and at most the island's declared 16-unit step at the reference scale, and no node marker or node label overlaps another node's marker or label

#### Scenario: Dense knowledge stays available
- **WHEN** a payload at the model's 64-node bound — 48 in-view nodes and 16 remembered gateways — renders on the island and then in the full-map overlay
- **THEN** the island stays a 240 × 240 CSS px canvas retaining every in-view node with its full label as its text alternative and every remembered gateway; its drawn labels are at least 16 CSS px, and the overlay makes every full name reachable at 16 CSS px or more at every permitted zoom level

