# WebClient Map and Exploration UI — Focused Design

**Date:** 2026-08-02
**Status:** Approved as part of the Browser-First MUD WebClient Suite
**Parent:** `2026-08-02-webclient-ui-design.md`
**Delivery units:** `map-knowledge-minimap`, then `webclient-exploration-menu`
**Dependencies:** `map-knowledge-minimap` depends on `webclient-oob-foundation`, existing map layers, and
the movement clock. `webclient-exploration-menu` depends on map knowledge and `npc-dialogue` so scripted
and free-form dialogue ship as one complete exploration surface.

---

## 1. Intent

This design gives the player a truthful local map and keyboard access to ordinary exploration without
turning the MUD into remote map-click navigation. The map remembers visited places, reveals only current
vision, and dispatches movement only through real adjacent Exits. It adapts separately to coordinate maps,
wilderness coordinates, instance rooms, and ordinary interiors.

The work is split into two delivery units. `map-knowledge-minimap` owns persisted discovery and read-only
map payloads. `webclient-exploration-menu` consumes those payloads and adds movement, look, interaction,
scripted/free-form dialogue, and wait/rest action adapters. Map knowledge can proceed while Phase 5 is in
flight; the exploration menu waits for NPC dialogue but does not wait for Narrator, ScenarioDirector,
SceneBuilder, or art.

---

## 2. Goals and Non-Goals

### Goals

- Persist visited node identity without duplicating static map truth.
- Render nearby vision plus dimmed previously visited nodes.
- Support Anchor/Grid, Wilderness, Instance, and ordinary interior spaces.
- Explicitly provide a coordinate-free local graph for Instance and ordinary rooms.
- Make adjacent movement, look, nearby-target selection, scripted dialogue, engage, take/drop where
  supported, and wait/rest available through keyboard menus.
- Charge movement and time through existing deterministic paths.
- Keep free-form dialogue and unbounded custom values in the text drawer.
- Prune knowledge for reclaimed ephemeral instance rooms.

### Non-Goals

- No world atlas, continent overview, quest GPS, or unknown-node disclosure.
- No shortest-path UI, auto-walk, or click-to-travel beyond one adjacent Exit.
- No invented coordinates for plain or instance rooms.
- No nested or multi-room instance support.
- No remote NPC interaction.
- No generic verb system that allows the client to invoke arbitrary commands.

---

## 3. Explicit Map-Instance Amendment

The approved 2026-08-01 map-instance design states that an `InstanceRoom` never appears in any map
rendering. This design explicitly amends that statement only for a WebClient local-exit graph.

The unchanged constraints are:

- no `(x, y, z)` or wilderness coordinate;
- no appearance in xyzgrid ASCII maps;
- no appearance in the wilderness minimap;
- no world-map membership;
- no shortest-path matrix or `goto` support;
- no travel shortcut;
- no nested or multi-room instance implication.

The new permission is limited to rendering the current room, its origin, and actual known Exit edges as
coordinate-free nodes. This same representation serves permanent `Room` interiors such as the guild hall
and general store.

---

## 4. Map Knowledge Model

### 4.1 Persisted data

The player stores a JSON-safe versioned record containing node identities and observation ticks:

```json
{
  "schema_version": 1,
  "visited": {
    "grid:capital_altoria:2:0": {
      "first_seen_tick": 0,
      "last_seen_tick": 30
    }
  }
}
```

The record does not store room names, descriptions, glyphs, exits, coordinates as independent fields,
terrain, or map geometry. Those remain in room data, XYMap, wilderness providers, and current objects.

`world/rules/map_knowledge.py` is the only writer to the character's knowledge attribute. It validates
schema, normalizes deterministic ordering for output, records successful arrival, and removes reclaimed
room IDs. Presenters read through its public parser rather than reading raw attributes.

### 4.2 Node IDs

| Layer | Format | Notes |
|---|---|---|
| Grid/Anchor | `grid:<z-map-key>:<x>:<y>` | XYMap's Z/map key identifies the map; Anchor is an annotation on a real grid node |
| Wilderness | `wild:<wilderness-name>:<x>:<y>` | Coordinates are bounded by the provider |
| Instance/interior | `room:<dbref>` | Valid only while that ObjectDB room exists |

Components are escaped or restricted so delimiters cannot produce ambiguous IDs. Grid/wilderness X and Y
must be integers in provider/map bounds; Z/map and wilderness names must be registered bounded strings.
Parsing rejects extra, missing, unknown, non-integer coordinate, or out-of-bounds components. A deleted
room ID resolves as unavailable and is eligible for pruning.

### 4.3 Arrival writers

Discovery occurs only after a successful location change:

- grid Exit traversal records the destination after the existing movement transaction/path succeeds;
- wilderness stepping records the provider coordinate after the contrib has committed the move;
- ordinary and instance Exit traversal records the destination through the common successful-arrival
  seam;
- activation relocation records the South Gate without charging movement time;
- startup/reconnect changes neither first-seen nor last-seen; only successful arrival records an
  observation.

Failed traversal, blocked combat movement, rolled-back movement charge, search, map rendering, and remote
inspection do not record discovery.

### 4.4 Reclamation

When an ephemeral instance room is deleted, reclamation removes its `room:<dbref>` from affected player
records in the same database transaction as room/entity cleanup. Attribute caches are snapshotted and
restored on rollback. A pruning or deletion failure rolls back both operations, leaves the room eligible
for a later reclamation attempt, and emits a diagnostic. A promoted room is not deleted and retains its
identity.

---

## 5. Local Map Payload

The version 1 payload contains:

- layer kind and stable current node ID;
- localized map title;
- a bounded list of nodes with ID, label, position in renderer-local coordinates, visibility state,
  current/anchor/landmark flags, and optional adjacent action reference;
- a bounded list of edges with source, destination, direction/label, known state, and traversability;
- a legend containing text labels in addition to style tokens;
- explicit unavailable reason if the current room cannot be represented.

Renderer-local coordinates are presentation geometry, not canonical world coordinates. Grid and
wilderness payloads use their actual coordinate relation. Local graphs assign deterministic layout
positions from Exit order solely to draw the graph; those positions are never sent back as movement
authority.

### 5.1 Visibility states

| State | Meaning |
|---|---|
| `current` | Player's current node |
| `visible_unvisited` | In current field of view but not previously entered |
| `visible_visited` | In current field of view and previously entered |
| `remembered` | Previously entered but outside current field of view |

Unknown nodes are omitted, not sent as hidden records. The browser cannot reveal them through DOM
inspection.

### 5.2 Layer adapters

**Grid/Anchor.** Read the current XYMap, node/link model, configured `map_visual_range`, and Anchor
registry annotations. Do not parse the rendered ANSI map string.

**Wilderness.** Use the current wilderness name and coordinates, provider bounds, adjacent legal
coordinates, terrain labels, and visited coordinate set. The map remains coarse at the established
10-km cell scale.

**Instance/interior.** Resolve the current room and real Exits. Render current, origin/return, and visited
adjacent rooms. Every currently visible and traversable one-hop Exit also produces a
`visible_unvisited` destination node before discovery, labelled `未探索`; its edge may show only the Exit
key/direction. The destination's canonical room name and details are withheld until it is visited. The
current implementation's one-room instance yields a deliberately small graph.

---

## 6. Map Interaction

Only nodes associated with a currently present, traversable Exit receive a movement descriptor. Clicking
or pressing Enter on such a node submits the stable movement action with opaque Exit identity and current
room guard. The server re-resolves the Exit from the actor's location, applies locks and combat movement
blocking, traverses through the existing Exit method, and charges movement through the shared movement
clock path.

Remembered remote nodes can be focused for name and landmark information but have no movement action.
There is no auto-route assembled from known nodes.

---

## 7. Exploration Menus

### 7.1 Root categories

| Category | Children |
|---|---|
| Move | Current Exits and adjacent actionable map nodes |
| Look | Room, present characters/NPCs/monsters, present objects |
| Interact | Present target, then target-specific affordances |
| Character | Expanded player state; read-only in this unit |
| Quests | Opens service panel registered by its delivery unit |
| Inventory | Opens service panel registered by its delivery unit |

Menus are composed from registered server affordances. If a later service unit is absent, the root does
not display a dead functional entry except for explicitly approved future placeholders.

### 7.2 Look and focus

Looking at the room invokes the same appearance path used by the command and preserves onboarding look
hooks. Looking at an entity uses ordinary display/access rules. Selecting an entity updates portrait
focus if the art unit knows a subject key; absence of art never blocks look.

### 7.3 Interaction

The presenter offers only legal, locally available categories. Examples include:

- scripted talk for an NPC with a dialogue component;
- free-form talk for an eligible NPC dialogue surface;
- engage for a living hostile Monster and no active session;
- guild or shop service when the current room has one unambiguous authorized host;
- take/drop only where existing object access and inventory behavior support it.

The browser does not infer an affordance from typeclass names or displayed prose. Server adapters repeat
location, access, hostility, host ambiguity, and object checks.

### 7.4 Dialogue

Scripted keyword choices are finite buttons and invoke the existing deterministic dialogue API. Free-form
dialogue opens the text drawer with a server-held target reference. The player types speech, not an NPC
dbref. Generated dialogue can fail to silence/greeting exactly as the existing degradation contract
states. Illegal AI intent remains discarded by the deterministic guardrail.

### 7.5 Wait and rest

The exploration context menu provides common durations and named day boundaries. Custom duration is a
bounded form value and is parsed server-side. Safety, combat, hostile targeting, and unsafe-location
gates are rechecked. The browser never advances its own clock.

---

## 8. Action IDs

| Action ID | Essential payload | Required revalidation |
|---|---|---|
| `explore.move` | current node guard, Exit ID | actor location, Exit location/destination, locks, combat block, movement charge |
| `explore.look` | target ID or room marker | presence, access, display path |
| `explore.talk_scripted` | NPC ID, keyword ID | presence, dialogue component, keyword registry |
| `explore.talk_freeform` | NPC ID, bounded speech | presence, dialogue eligibility, content handling |
| `explore.engage` | Monster ID | existing `engage` contract |
| `explore.wait` | approved boundary or bounded duration | existing skip safety and clock API |

Take/drop actions are registered only if their deterministic ownership/access API is explicitly included
in the owning OpenSpec change. This design does not authorize a generic object mutation action.

> **Amended 2026-08-09 (change `party-core`).** The action table gains `explore.party_invite` and
> `explore.party_leave` — the WebClient surfaces for the party-core `invite` / `leave` commands.
> The invite adapter submits the finite invitation request (no free speech) through the same
> guarded dialogue seam, and both adapters go through the deterministic `world/rules/party.py`
> APIs with the same re-verification (co-location, bound, membership) as the commands.

---

## 9. Error Handling

- Corrupt map knowledge makes the minimap unavailable and logs a diagnostic; it does not reset or
  silently overwrite player history during a read.
- An unresolved remembered room is omitted and scheduled for deterministic cleanup, not exposed as a
  broken actionable node.
- A stale move runs no traversal and returns a current room/map snapshot.
- An Exit that disappears or changes after render is rejected by ordinary re-resolution.
- A map adapter failure leaves narrative, command drawer, status, and non-map exploration menus usable.
- On reconnect, current location and persisted knowledge rebuild the map; no client map cache is
  authoritative.

---

## 10. Tests and Acceptance

### Map knowledge tests

- Node ID round trips and malformed IDs.
- First/last seen behavior at fixed world ticks.
- Successful arrivals for each layer; blocked/failed movement records nothing.
- No duplicate geometry or room names in persisted knowledge.
- Reclaimed room pruning and promoted-room retention.
- Corrupt-record read isolation.

### Presenter tests

- Grid visual range and anchor annotation.
- Wilderness bounds, terrain labels, and remembered cells.
- Instance one-room local graph without coordinates.
- Ordinary guild/store interior graph.
- Unvisited one-hop interior/instance destination is actionable but labelled only `未探索`; its room
  name and details remain absent until arrival.
- Unknown nodes absent from payload.
- Only adjacent traversable Exits receive movement descriptors.
- Deterministic ordering and bounded payloads.

### Action integration

- Keyboard movement traverses the same Exit and charges the same 30 seconds as the command path.
- Combat blocks menu and map movement.
- Look preserves onboarding progression.
- Scripted dialogue buttons use existing keyword behavior.
- Free-form dialogue retains target and degrades offline.
- Wait/rest obey safety gates.
- Tampered remote target/Exit IDs produce no state change.

### Browser acceptance

- Navigate grid, wilderness, instance, and interior examples using keyboard only.
- Current, visible, and remembered states are distinguishable without color alone.
- Focus a remembered remote node and verify no travel action exists.
- Select an adjacent map node and observe location, clock, narrative, and map update together.
- Disconnect/reconnect and retain server-persisted exploration.

Each delivery unit receives its own OpenSpec requirements and traceability. The instance local-graph
requirement must explicitly modify the prior absence-from-map requirement rather than silently adding a
contradictory test.
