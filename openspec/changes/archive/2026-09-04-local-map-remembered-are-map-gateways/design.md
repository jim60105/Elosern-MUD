# Design — Remembered Nodes Are Map Gateways, Not Visited Ground

## Context

`web/webclient/presentation/local_map.py` builds the `local_map` panel from
canonical room, map, and knowledge data. Three of its four layer adapters end
with the same shape of loop:

```
for visit in builder.remembered(MAX_NODES - len(builder.nodes)):
```

`_GraphBuilder.remembered(cap)` (`:333`) returns every entry of the player's
visit record whose ID is not already in the payload, most-recent
`last_seen_tick` first, tie-broken by ascending node ID. `_grid_layer` (`:477`)
keeps the `grid:` ones and labels each with the room key at that coordinate;
`_wilderness_layer` (`:843`) keeps the `wild:` ones more than one cell away and
labels each with
`WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].display_name_zh`;
`_interior_graph` keeps the `room:` ones and labels each with the room key.

The wilderness case is the reported defect. `region_for_coordinates`
(`world/maps/wilderness_provider.py:72`) is a pure integer partition of the
224 × 224 continent into **seven** regions, so a whole region — tens of
thousands of cells — shares one display name. Every visited cell therefore
produces a chip that is textually identical to every other chip from the same
region. The screenshot shows seven 「西部丘陵與谷地」 chips; the ceiling is the
64-node payload bound.

The domain that the feature actually wants is already authored.
`world/lore/wilderness_entry.py` holds `WILDERNESS_ENTRY_REGISTRY`, a
module-level source of truth (AGENTS.md) mapping an `anchor_key` to a
`WildernessEntryPoint(shape, origin_xy, gates)`. A one-`#` mask is documented in
that file as cave semantics; a larger mask is a city footprint.
`entry.approach_cell(gate)` is the exterior wilderness cell a traveller stands
on to take the gate, and `gate.grid_xy` / `gate.z_map_key` name the grid room on
the far side. Today's registry holds one entry: `capital_altoria`, a 5 × 5 mask
at `origin_xy = (58, 98)`, anchor cell `(60, 100)`, with gates whose approach
cells compute to `(60, 97)` (south gate, grid room `南門` at `(2, 0)`) and
`(60, 103)` (north gate, grid room `北門` at `(2, 4)`). `_grid_gate_candidates()`
(`:497`) already reads exactly this registry for the grid layer's in-view gate
nodes.

Two constraints bound every decision below.

1. **`NodeVisit` carries nothing but identity and ticks.**
   `world/rules/map_knowledge.py:62` is `(node_id, first_seen_tick,
   last_seen_tick)`, and `map_knowledge.py` is the sole writer of the record
   (its own spec requirement). "Is this visited node a boundary?" therefore
   cannot be read off the record; it must be resolved at presentation time
   against the registries, from the node ID alone.
2. **The edge direction marker is a raw-coordinate ray.** Spec `:177` requires
   the marker to be placed where "the ray from the current node through that
   node's **raw payload coordinate delta**" crosses the canvas border, "and
   never from rank-compressed columns or rows". Spec `:175` scopes that
   permission: on `grid` and `wilderness` the payload `x`/`y` "are validated
   world coordinates and MAY drive relative-direction geometry"; on every other
   layer they "SHALL NOT be read as direction, distance, or place". A wilderness
   cell's `(x, y)` and a grid room's `(x, y, z_map_key)` are different
   coordinate spaces, so a delta taken across them is not a direction — it is
   noise the renderer would draw as a confident bearing.

## Goals / Non-Goals

**Goals:**

- `remembered`, on the coordinate-bearing layers, names the ways out of the map
  the player is looking at, and nothing else.
- The predicate, the coordinates, and the name of every remembered gateway are
  derivable from the stored visit record plus the module-level registries, with
  no new persisted state and no new payload field.
- Every remembered node the payload plots has coordinates in the same coordinate
  space as the `current` node, so the shipped raw-delta bearing is sound by
  construction rather than by luck.
- A remembered gateway is named by where it goes, so two of them are never
  textually identical.
- The set stays bounded and deterministically ordered, as the shipped spec
  requires.

**Non-Goals:**

- Changing the persisted `map_knowledge` record, its writers, or its grammar.
- Changing the in-view gateway pair rendering, which the "minimap gate nodes
  match traversal in both directions" requirement pins on both sides.
- Changing the instance/interior remembered set.
- Deleting the island's remembered list or naming the edge markers
  (`webclient-minimap-05-edge-markers-replace-list`), the island's affordance
  and readout (`webclient-minimap-04-island-single-affordance`), or the
  lattice's draft visual fidelity (`webclient-minimap-06-draft-lattice-fidelity`).
- Any change to the shared Python/JavaScript validators or their parity
  contract.

## Decisions

### D1 — A gateway is a registered `WildernessGate`, resolved per layer against `WILDERNESS_ENTRY_REGISTRY`

The predicate is evaluated on the candidate's canonical node ID, decoded with
`decode_node`, against the one registry that already defines map boundaries:

| Drawn layer | Candidate ID | Gateway when |
| --- | --- | --- |
| `wilderness` | `wild:<name>:<x>:<y>` | `(x, y) == entry.approach_cell(gate)` for some `entry` in `WILDERNESS_ENTRY_REGISTRY` and some `gate` in `entry.gates` |
| `grid` | `grid:<z>:<x>:<y>` | `(x, y) == gate.grid_xy` and `z == gate.z_map_key` for some `entry`/`gate` in the same registry |

Both sides read `WILDERNESS_ENTRY_REGISTRY` and nothing else, so the two ends of
one gateway can never disagree, and the presenter derives the same
`(approach_cell, grid_xy, z_map_key)` triple the traversal code and
`_grid_gate_candidates()` already read. The lookup is a pure, DB-free pass over
a validated in-memory registry (`validate_wilderness_entries` runs at sync
time), so it costs nothing per payload and cannot fail on live data.

*Alternatives rejected:*

- **Flag gateways in the knowledge record.** Would require `map_knowledge.py` to
  learn what a gateway is and to rewrite existing records; the record's own spec
  makes it the sole writer of a versioned visited log, and a stored flag would
  go stale the moment the registry is edited. Presentation-time resolution is
  also strictly better on the retroactive case: a player who walked a cell
  before it became a gate approach cell gains the gateway, which is correct.
- **Derive gatewayness from the live database** (probe each visited coordinate
  for a `WildernessGateExit`). Requires a DB query per remembered candidate,
  depends on provisioning rather than on authored truth, and contradicts
  AGENTS.md's rule that the module registry is the source of truth and the DB is
  a projection.

### D2 — An `AnchorRoom` alone is not a gateway; `landmark` already covers it

`_grid_coord_is_anchor()` flags the capital's plaza `(2, 2)`, and the grid layer
sets both `anchor` and `landmark` on it. Walking into the plaza does not leave
the map, so it is not a boundary. Admitting anchors would put a node on the
canvas border that promises a way out and is not one — the exact failure the
change exists to remove. The `landmark` flag stays what it is: an in-map place
worth the gold treatment.

Conversely a remembered **gateway** is emitted with `landmark: true` and
`anchor: false`. `landmark` is the only payload signal the shipped edge-marker
clause (`:177`) reads for its gold ornament, and a way onto another map is
precisely the thing worth marking; `anchor` keeps its `AnchorRoom` meaning and a
gate room (`南門`, a plain `GridRoom`) is not one.

*Alternative rejected:* **a third boolean, `gateway`.** It would be a payload
schema change, mirrored in the JS validator, breaking the parity contract and
the exact-fields rule, to carry information the `remembered` visibility state
already carries on these layers.

### D3 — A remembered gateway is carried at its coordinate **in the layer being drawn**, or not at all

This is the trap, and the rule that closes it: *a payload node's `x`/`y` on a
coordinate-bearing layer are only ever coordinates of that layer's own space.*

- On the `wilderness` layer, a remembered gateway is the **approach cell**:
  node ID `wild:elosern:<ax>:<ay>` at `x = ax`, `y = ay`. Standing at
  `(60, 107)` with `(60, 103)` remembered, the delta is `(0, -4)` — cleanly due
  south, in one space, and the marker lands on the south border.
- On the `grid` layer, a remembered gateway is the **gate room**: node ID
  `grid:<z>:<gx>:<gy>` at `x = gx`, `y = gy`, with `z` equal to the drawn map's
  own `z_map_key`. Standing in the plaza at `(2, 2)` with `北門` remembered, the
  delta is `(0, +2)` — north, in grid space.
- A gateway with **no coordinate in the drawn layer** — a gate whose
  `z_map_key` is not the map currently being drawn — is **omitted from the
  payload entirely**. It is not plotted at a probed slot, not plotted at the
  registry's coordinates from the other space, and not plotted at the current
  node. Omission is already the payload's answer for a node it cannot represent
  ("Unknown nodes SHALL be omitted entirely"), and the gateway remains fully
  presented on its own layer's payload, which is the surface it is a boundary
  of.

Note what this does **not** change: the shipped in-view gateway node keeps its
renderer-local slot. Spec `:10` explicitly allows "a gateway node shown on a
layer other than its home layer keeps the adjacent position of the step that
reaches it" — that node is one step away, so its slot *is* its true bearing, and
the "Wilderness side shows the gate room" / "Gate side shows the wilderness
approach cell" pair depends on it. The renderer-local slot is sound exactly
because adjacency pins it; a remembered node has no step to pin it, which is why
it must carry a real coordinate or nothing.

*Alternatives rejected:*

- **Keep the far-side identity and give it a renderer-local slot** (the in-view
  treatment, generalised). The slot would have to be invented from something —
  the free-slot probe, or the raw cross-space delta — and either way the edge
  marker would draw a confident bearing computed from a number with no
  directional meaning. The shipped spec forbids exactly this.
- **Normalise both spaces into one** (project grid coordinates into wilderness
  coordinates through the anchor's footprint). The anchor's footprint is a 5 × 5
  wilderness mask standing for a 5 × 5 grid map today, but nothing in the domain
  guarantees that correspondence, `anchor_cell` is a bounding-box midpoint, and
  the projection would be a fabricated geometry the world does not author.
- **Emit the node with `x`/`y` of the current node.** Zero delta, so the marker
  helper has no ray at all; it would either divide by zero or pick an arbitrary
  octant. A lie with a fallback is still a lie.

### D4 — Remembering a gateway means having entered the node the drawn layer carries it as

The check is `visit.node_id in visited` for exactly the ID the payload will
emit — the approach cell on the wilderness layer, the gate room on the grid
layer. It needs no new state, reads the record through `parse_knowledge` exactly
as today, and is the same identity the shipped visibility rule already keys on
("Visibility SHALL be keyed on the node's canonical identity — the same ID the
resolver and the knowledge record use").

It is also the right rule on the merits, because of how arrivals are recorded.
`record_arrival` records the node the player arrives at. To take a gateway from
the wilderness you must be standing on its approach cell, which was recorded
when you arrived there; the traversal then records the gate room. To take it
from the grid you must be standing in the gate room, which was recorded when you
entered it; the traversal then records the approach cell. **A completed
traversal in either direction records both ends**, so anyone who has actually
used a gateway remembers it on both layers. The rule differs from "either end
visited" only for a player who has stood in the gate room and never gone
through — who then sees the gateway on the grid layer (they have seen the gate)
and not on the wilderness layer (they have no idea where in the wilds it comes
out). That is the honest reading of what they know.

*Alternatives rejected:*

- **"Seen it from an adjacent cell."** The knowledge record stores arrivals
  only; sightings are not persisted, so this is not checkable without a new
  writer in a module whose spec makes it the sole writer. It would also
  contradict the in-view rule, where an adjacent cell is `visible_*`, not
  `remembered`.
- **"Either end visited."** Costs an extra registry hop to derive the far-side
  ID for every candidate, and reports a wilderness position the player has never
  occupied. As shown above it differs from D4 only in the case where the honest
  answer is "you don't know".
- **"Anywhere in the region / near the footprint."** Not a boundary predicate at
  all; it re-derives the defect with a radius.

### D5 — A remembered gateway is named by the place on the far side, from the lore registries

| Drawn layer | Label |
| --- | --- |
| `wilderness` | `ANCHOR_REGISTRY[entry.anchor_key].display_name_zh` — 「聖潔王都」 for the capital's gates, and the anchor's own name for a one-`#` cave entry |
| `grid` | `WILDERNESS_REGION_REGISTRY[region_for_coordinates(*entry.approach_cell(gate))].display_name_zh` — the wilderness region the gate opens onto |

The wilderness side is the case the owner asked for: standing in the wilds, the
border marker says 「聖潔王都」 or 「魔導遺跡」, the name of the place you would arrive
at, from `world/lore/anchors.py`. The grid side names the wilderness the gate
opens onto, which is both the far side and exactly the label the shipped in-view
grid gate node already carries (`_wild_region_label(*landing_cell)`), so one
gateway reads the same whether it is in view or remembered.

**Distinctness clause.** Either side can repeat, not just the grid side:
`WildernessEntryPoint.gates` is a tuple, so one anchor can register more than
one gate — the capital already does, both onto one region on the grid side
AND both from `ANCHOR_REGISTRY["capital_altoria"].display_name_zh` on the
wilderness side (a `rubber-duck run 2` finding: an earlier draft of this
clause assumed the anchor's display name was "already unique on the
wilderness layer," which is only true for a single-gate entry). Within a
single payload, remembered gateway labels SHALL be distinct; where the
far-side name would repeat, each colliding node is qualified with the gate
room's own canonical name (its `key`) — the same qualifier on both layers,
since it is the one identity that is always unique per gate regardless of
which side is drawn — in the exact form `<far-side name>（<gate room name>）`:
「西部丘陵與谷地（南門）」/「西部丘陵與谷地（北門）」 on the grid side, and
「聖潔王都（南門）」/「聖潔王都（北門）」 on the wilderness side. Both halves are
authored strings (the region/anchor registry and the room's prototype key);
the presenter composes presentation text, never an identity, and the result
stays far inside the 256-code-point node-string bound. Without this clause
on BOTH layers the change would have reproduced the reported defect at a
smaller scale — two identical chips instead of seven.

*Alternatives rejected:*

- **The terrain/region name on both sides.** On the wilderness layer that is
  literally the defect: the approach cell `(60, 103)` sits in 西部丘陵與谷地 like
  its neighbours, and labelling the gateway with it says nothing about the city
  behind it.
- **The boundary node's own name on both sides** (`南門` on the grid layer, the
  approach cell's region on the wilderness layer). Distinct by construction, but
  it names the door rather than the destination, which is what the owner
  explicitly ruled out; a player reading 「南門」 on a border marker learns
  nothing about where it leads.
- **Always qualifying** (`西部丘陵與谷地（南門）` even when unique). Longer labels for
  no gain; the label ramp truncates at 4 glyphs on the island, so a qualifier
  that is never needed is a qualifier that is never seen.

### D6 — Bounded by 16 and by the remaining node budget, ordered as shipped

`_GraphBuilder.remembered(cap)`'s ordering contract is unchanged: descending
`last_seen_tick`, then ascending `node_id`, so the same record always yields the
same bytes. The gateway filter is applied to those ordered candidates, and the
result is truncated to `min(MAX_REMEMBERED_GATEWAYS, MAX_NODES - len(nodes))`
with `MAX_REMEMBERED_GATEWAYS = 16`.

16 is a presenter-side ceiling, not a payload bound: it is not mirrored in the
JS validator (which continues to enforce the 64-node payload bound), so the
parity contract is untouched. It exists so a future registry with hundreds of
gateways cannot let the remembered set crowd out in-view nodes on a large map;
the structural bound is much tighter — at most one node per registered gate per
layer, which is 2 today.

The in-view collection order is unchanged: current node, in-range nodes, then
reserved gate capacity, then remembered — so the shipped guarantee that
"current/visible nodes always included first" holds without modification.

*Alternative rejected:* **no explicit cap, relying on the node budget alone.**
The budget is shared with the in-view set, so a payload with a wide lattice and
a gateway-rich registry would have its ordering decided by whatever was left
over. A declared number is testable; a residue is not.

### D7 — The coordinate-free layers keep the shipped meaning

`instance` and `interior` payloads keep "a previously entered node outside the
current field of view", and `_interior_graph`'s remembered loop is untouched.
Three reasons: those layers' `x`/`y` are renderer-local layout values that spec
`:175` forbids reading as direction, so they draw no edge markers and the
coordinate-space problem does not arise; their remembered set is the rooms of
one building, which are individually named and do not duplicate; and there is no
boundary registry for them — an interior's "way out" is an ordinary Exit, which
the graph already draws. The visibility-state requirement therefore becomes
explicitly layer-scoped, which the spec already does for `x`/`y` semantics.

*Alternative rejected:* **redefine `remembered` uniformly and drop it from the
coordinate-free layers.** It would delete a working, informative readout (the
rooms of an inn you have walked) to satisfy a symmetry nobody asked for, and the
owner's instruction names the coordinate layers.

### D8 — FLAGGED, STRIKEABLE: the same duplication inside the field of view

**The owner has not ruled on this.** It was raised in review of this change's
brief and is kept as its own requirement and its own task wave so it can be
struck without touching anything else.

The 3 × 3 wilderness neighbourhood labels all nine cells with one region name,
for the same reason the remembered list did. Two clauses fix it:

- **(a) Presenter.** An in-view `wild:` neighbour that is a registered gate
  approach cell is labelled with the far-side anchor's display name (D5's
  wilderness rule) instead of its region name. Its node ID stays
  `wild:<name>:<x>:<y>` — only the label changes, so nothing about identity,
  action, or the gateway pair rendering moves. Standing at `(60, 104)`, the cell
  south of you stops reading 「西部丘陵與谷地」 and starts reading 「聖潔王都」, which is
  the true and useful statement.
- **(b) Renderer.** On a `wilderness` payload, the shared renderer draws no
  visible label text for an in-view node whose label string is identical to
  the `current` node's label, while keeping the node's full label as its
  accessible name (`MapLattice.vue` already emits
  `<text><title>{{ node.label }}</title>…</text>`, so the `<title>` stays and
  only the visible text goes). Markers, actions, and the shape ladder are
  untouched, so state remains distinguishable without colour. Scoped to
  `wilderness` deliberately: on `grid`/`instance`/`interior` a node's label is
  an individual room name (`GridRoom.key`/`Room.key`), not a shared region
  name, so two distinct rooms that happen to share a name are still two
  distinct places and both must keep their visible label — this clause exists
  to hide a repeated *region*, not to deduplicate coincidentally identical
  *room* names.

The result on the reported screen: one region name at the current node, a
different name where the region changes, 「聖潔王都」 where the city gate is, and
nothing repeated.

*Alternative rejected — and the reason (b) is client-side:* **have the presenter
emit an empty `label` for a cell that says nothing new.** The JavaScript
validator rejects it: `validateLocalMapNode` in
`web/static/webclient/js/elosern/protocol.js:1566` throws
`"node.label must be non-empty"`, while the Python validator's `_require_str`
enforces only the 256-code-point ceiling. An empty label would therefore fail
the client's exact schema and disable the minimap. Relaxing it means editing a
preserved UMD bundle covered by the dependency-free Node gate and by the
validator parity contract — real scope, for a rule that reads better on the
renderer anyway, since "don't draw the same word twice" is a presentation
statement about a drawn set, not a fact about a cell. (That the two validators
disagree on this rule at all is noted under Open Questions; it is not this
change's to fix.)

*Alternative also rejected:* **label same-region neighbours with the direction
word** (「東」, 「東北」…). Non-empty and unique, but the lattice position already
states the direction, so it is chrome that repeats the geometry, and it sits
uncomfortably beside the spec's ban on bearing readouts.

### D9 — No storage change, confirmed against the record

`world/rules/map_knowledge.py` persists
`{"schema_version": 1, "visited": {<node_id>: {"first_seen_tick": int,
"last_seen_tick": int}}}` and `parse_knowledge` returns `NodeVisit` triples
sorted by node ID. Nothing in this change writes, prunes, reinterprets, or
re-grammars a stored ID: the presenter reads the same IDs and filters them
differently. Every existing player record therefore keeps working with no
migration, and the project is pre-release with zero users besides. The only
observable consequence of the reinterpretation is the intended one — visited
cells that are not boundaries stop being drawn as remembered nodes.

## Risks / Trade-offs

- **The grid layer's remembered set becomes almost always empty on the shipped
  map.** The capital is 5 × 5 with `map_visual_range: 2` in `nodes` mode, so both
  gate rooms are usually already in view and are drawn as `visible_*`, leaving
  nothing remembered. → Accepted and intended: the island stops showing a list
  of rooms the player can see anyway. The rule earns its keep on larger maps and
  as the registry grows; the delta scenarios pin the behaviour rather than the
  current world data, and a test seeds a visited gate room out of visual range.
- **Only one entry is registered today** (`capital_altoria`, two gates), so the
  cave case (a one-`#` point-shape entry, `approach_cell` = the anchor cell) has
  no live data. → The predicate treats it uniformly by construction — the
  point-shape branch of `approach_cell` returns the anchor cell, which is a
  walkable wilderness cell — and a delta scenario plus a unit test cover it with
  a constructed registry rather than waiting for world data.
- **The distinctness qualifier composes a label from two authored strings.** →
  Bounded (both halves are short authored names, far inside 256 code points),
  deterministic (the collision set is ordered before qualification), and applied
  only on collision. It composes presentation text, never an identity: the node
  ID is untouched.
- **A registry edit retroactively changes what a player remembers.** Adding a
  gate makes a previously walked cell appear as a gateway; removing one makes it
  disappear. → This is the correct behaviour for a predicate resolved against
  authored truth, and it is the behaviour a stored flag could not give. It is
  called out in the spec text so it is not read as a bug.
- **The reported screenshot's remembered list will look empty in many
  positions.** → That is the point of the change, and
  `webclient-minimap-05-edge-markers-replace-list` removes the list surface
  entirely; this change must not pre-empt that decision, so it leaves the list
  exactly where it is and only changes what goes into it.

## Migration Plan

None. The project is pre-release with zero users, no stored data changes shape
(D9), no payload field is added or removed, and the two validators are untouched,
so there is nothing to migrate and nothing to roll back beyond reverting the
presenter change.

## Open Questions

1. **Does the owner want D8 at all?** It is flagged in the proposal and isolated
   in its own requirement and task wave. Striking it leaves the rest of the
   change intact.
2. **Should the two validators be reconciled on `node.label`?** The JavaScript
   validator rejects an empty node label and the Python one accepts it, which is
   an undocumented divergence in a pair the spec calls "shared unchanged". This
   change works around it (D8) rather than fixing it; the fix belongs to whoever
   owns the parity contract next.
3. **Should a future non-wilderness boundary kind** (an instance portal, a
   ship route) **join the predicate?** D1 is written against one registry
   because that is the only boundary the world authors today; a second registry
   would extend the table in D1 without changing the coordinate, naming,
   bounding, or knowledge rules.
