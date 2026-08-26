# Browser-First MUD WebClient Suite — Design

**Date:** 2026-08-02
**Status:** Approved
**Scope:** Desktop WebClient presentation, versioned OOB protocol, keyboard-first finite-action
menus, combat selection, local minimap, player status, scene and portrait art, exploration,
services, and character-creation surfaces.

This document is the source of truth for the complete WebClient suite. The focused design documents
listed in section 14 refine individual delivery slices but may not contradict this document.

This design supplements and explicitly amends
`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` in four limited ways:

1. Phase 6 is split into multiple independently verifiable changes instead of one art queue and one
   WebClient panel change.
2. The scene-only art pipeline gains a separate portrait subject type. Decision D10 still applies to
   scene images: scene art remains keyed by archetype, never by room.
3. Instance rooms and ordinary interiors gain a coordinate-free local exit graph in the WebClient.
   They still never enter an xyzgrid or wilderness map and gain no invented coordinates.
4. The browser becomes the first-class graphical client. Telnet remains a fully playable text
   fallback and retains rule-level parity.

---

## 1. Product Context

The deterministic game is playable, but its current player interface is command-only. Starting a
combat session tells the player to type `cast <skill>[=<target>]` without showing the character's
active skills. The player cannot see combat resources, active modifiers, a persistent local map, or
the scene art anticipated by the engine design. The project contains the stock Evennia WebClient
extension points, but no project-authored OOB state protocol or panel
implementation.

The intended experience keeps the readable history and command vocabulary of a MUD while removing
the need to memorize finite command choices. A player should be able to navigate every ordinary
action whose choices the server can enumerate by using the arrow keys and Enter. Free-form values,
including character names and open-ended NPC dialogue, continue to use a text field. Administrative,
developer, and uncommon advanced commands remain available through the command drawer and Telnet.

The graphical client targets desktop browsers. It is designed for 1440x900 and supports a minimum
viewport of 1280x720. Mobile usability is not an acceptance criterion for this suite.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Make the browser the complete graphical experience while retaining a fully playable Telnet path.
- Preserve a large, scrollable narrative log as the primary surface.
- Show scene art, contextual character portraits, HP/MP/SP, active combat modifiers, and a local
  minimap without making the game depend on image or LLM services.
- Make all server-enumerable ordinary player actions available through a keyboard-first menu.
- Give combat a Pokemon-style hierarchy: action category, skill, target, and submission.
- Show every owned active skill, including unavailable skills with a stable disabled reason.
- Keep the browser thin: it renders server-authoritative presentation data and never computes game
  rules or writes canonical state.
- Use versioned, deterministic JSON payloads that can be tested without parsing narrative prose.
- Preserve the single-writer boundary and the existing atomicity guarantees of combat, quests,
  movement, guild operations, and shops.
- Split the suite into focused OpenSpec changes with independent panel acceptance tests.

### 2.2 Non-Goals

- No mobile or touch-first layout in this suite.
- No dedicated Mudlet package. Generic Telnet remains the text fallback.
- No client-side game simulation, combat formula, target validation, price calculation, or clock.
- No parsing of room prose, Narrator output, command messages, or ANSI text to infer UI state.
- No automatic pathfinding, remote travel, or map click that bypasses an actual Exit traversal.
- No new combat item-use or defend mechanic. Their root-menu entries are visibly disabled until
  separately specified deterministic APIs exist.
- No equipment-use behavior where the deterministic engine currently provides none.
- No generated art in tests and no network dependency in the required suite.
- No competing second client. The view layer is a Vue 3 SPA (Vite + Pinia) on the same Evennia
  extension points; the preserved dependency-free logic stays under `web/static/webclient/js/elosern/*`.

---

## 3. Design Decisions

| ID | Decision | Rationale |
|---|---|---|
| U1 | **Browser-first graphical client; Telnet text fallback.** | The existing design already selects the WebClient (Vue SPA), WebSocket, and OOB. A Mudlet-first client would add a separately distributed Lua UI and a second compatibility matrix. |
| U2 | **Classic MUD console layout.** | The narrative log receives the largest area. Art, map, and status support it rather than displacing it. |
| U3 | **Ink-night and vermilion visual language.** | Charcoal black, paper gray, and seal red fit the setting and remain readable for long sessions. Focus and status never rely on color alone. |
| U4 | **Menu-first keyboard focus.** | Arrow keys navigate, Enter confirms, Escape returns, and `/` opens the command drawer. Mouse input invokes the same controls, not a separate flow. |
| U5 | **Finite choices are menuized; free text stays text.** | Movement, targets, skills, quests, shops, and other enumerable choices need no memorized command. Names, custom values, and open-ended dialogue still require input. |
| U6 | **Versioned OOB snapshots and updates.** | Structured payloads are stable, replayable, and independent of Traditional Chinese prose changes. |
| U7 | **Server-provided action descriptors.** | The server supplies labels, enabled state, disabled reasons, costs, and target choices. The browser does not duplicate availability rules. |
| U8 | **Every submitted action is revalidated.** | Presentation is advisory. Tampered or stale IDs cannot bypass domain checks. |
| U9 | **Allowlisted action dispatcher, never arbitrary command strings.** | A stable action ID and bounded payload provide a smaller, auditable attack surface and avoid text-search ambiguity. |
| U10 | **Full snapshots on connection; panel replacements for normal updates.** | Reconnection is simple, while routine updates avoid replacing unrelated panels. JSON Patch complexity is unnecessary. |
| U11 | **Session revision and request deduplication.** | Stale menus do not execute, and key repeat or duplicate packets cannot perform a purchase or cast twice while connected. |
| U12 | **Combat-essential status is always visible.** | HP/MP/SP, buffs/debuffs, and sexual-state modifiers that currently affect combat are actionable information. Full details remain in the character panel. |
| U13 | **Nearby vision plus persistent exploration.** | Current surroundings remain prominent, visited places remain dimly visible, and unknown space is not leaked. |
| U14 | **Coordinate-free local graphs for non-map rooms.** | Instance rooms and interiors can show truthful Exit relationships without pretending to occupy xyzgrid or wilderness coordinates. |
| U15 | **Scene art plus contextual portrait overlay.** | The scene retains spatial context while the selected speaker or target gains identity in limited screen space. |
| U16 | **Unique portraits for players and explicitly named NPCs; shared portraits for generic monsters.** | This balances recognizability, queue size, storage, and GPU cost. Identity policy is explicit data, never inferred from display names. |
| U17 | **Desktop-only first release.** | A responsive mobile interaction model would be a second substantial design and test surface. |
| U18 | **Panel-level acceptance, plus one short shell smoke test.** | Each surface receives complete behavior coverage without creating one fragile, very long first-day browser test. |

---

## 4. System Architecture

```text
┌─ Desktop WebClient ────────────────────────────────────────────────┐
│ Vue SPA shell                                                     │
│ narrative | art+portrait | status | local map | action dock       │
│                                                                   │
│ ClientStateStore       KeyboardRouter       panel renderers       │
└───────────────────────────────────────────────────────────────────┘
                    ⇅ versioned WebSocket/OOB ⇅
┌─ Evennia WebClient presentation ──────────────────────────────────┐
│ server/conf/inputfuncs.py                                         │
│   ui_sync / ui_action ingress; session and envelope validation    │
│                                                                   │
│ web/webclient/presentation/       read-only panel presenters      │
│ web/webclient/actions/            allowlisted action adapters     │
└───────────────────────────────────────────────────────────────────┘
              ↓ read state                    ↓ call public APIs
┌─ Deterministic core ──────────────────────────────────────────────┐
│ world/rules/       actions, combat, movement, status, economy     │
│ world/maps/        map and instance lifecycle                     │
│ world/quests/      quest lifecycle                                │
│ registries         skills, lore, items, art subjects (read-only)  │
└───────────────────────────────────────────────────────────────────┘
                              ↓
                       ORM / SQLite / art store

Telnet or command drawer → existing Evennia Commands → same public APIs
```

### 4.1 Browser components

| Component | Responsibility | Dependencies |
|---|---|---|
| `ClientStateStore` | Validate protocol versions, hold the newest revision, replace panel payloads, expose render subscriptions | OOB transport only |
| `KeyboardRouter` | Maintain one menu focus stack; route arrows, Enter, Escape, Space, and `/`; prevent repeated submission | state store and action dock |
| `AppShell` (Vue) | Create required panels, persist dimensions, migrate layout versions, prevent required panels from being permanently closed | Vue AppShell + Pinia store |
| Narrative renderer | Preserve the existing text stream, scroll history, and unread marker | Evennia text output plugins |
| Panel renderers | Render status, map, art, menu, services, and creation payloads | state store; no direct transport |
| Command drawer | Send normal text input for free-form and advanced commands | existing `text` input function |

### 4.2 Server components

| Component | Responsibility | Dependencies |
|---|---|---|
| OOB input functions | Authenticate session/puppet, validate bounded envelopes, invoke sync or dispatch | Evennia session handler |
| Snapshot coordinator | Build full or changed-panel payloads, assign session revisions, isolate presenter failures | presenters |
| Presenters | Read canonical state and registries; return deterministic JSON-safe panel values | read-only domain APIs |
| UI action dispatcher | Check action allowlist, revision, request ID, and adapter payload schema | action adapters |
| Action adapters | Re-resolve referenced entities and invoke existing deterministic public APIs | `world/rules`, `world/maps`, `world/quests` |

Presenters never call a state-mutating API. Action adapters contain no game formula and never write
attributes directly. They translate a validated UI intent into the same deterministic API that a
command uses.

---

## 5. Visual Layout and Interaction

### 5.1 Default desktop layout

The default layout is a full-bleed cinematic stage, not a three-column dashboard. The binding visual
and information-architecture reference is the validated design draft (`docs/design/elosern-redesign/`,
`index.html` + `REDESIGN.md`), and the delivery document that owns this redesign is
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md`.

- **Stage:** a `.game` root (`position:fixed; inset:0`) filling the viewport; the scene backdrop from
  the committed `art` panel is the lowest layer.
- **Narrative:** a bounded caption card at the visual centre of the stage; the complete retained log is
  reachable in one action from the caption (the `完整日誌` full-log overlay).
- **HUD islands:** the left anchor carries the character head card, the vitals, and the condition chips
  as separate floating islands; the right anchor carries the minimap island, which the committed-mode
  matrix hides in combat (REDESIGN.md §2).
- **Action dock:** the single persistent `#action-dock` panel in the `dock` anchor — an icon tab bar with
  truthful count badges, a router-derived breadcrumb, the per-kind row vocabulary, the combat participant
  frame, and the bounded skill master-detail.
- **Command line:** the always-visible command line in the `command-line` anchor (prompt chevron, the
  input field, quick-word chips, and history/Tab hints), replacing the collapsed drawer entry.
- **Reference surfaces:** the skill book, bag + equipment, the shop, the quest board, the lore reference,
  and the character status render in a right-anchored drawer (scrim, focus trap, Escape) rather than in a
  permanently visible column.

Every surface's visibility is driven by the single committed attribute on the stage root
(`data-elosern-mode`): a surface the current mode hides is removed with `display:none` — never dimmed —
so it leaves the accessibility tree and the tab order, and it is present again when the mode returns.

The saved layout configuration (the Vue layout store) includes a
project layout version. When required component names or layout structure change, known old versions are
migrated. An unrecognized version is reset to the approved default. The action dock, connection state, and
command-line entry point cannot be removed by a stale localStorage layout.

### 5.2 Visual language

The visual language is implemented by the design-token system — the ink-night palette, the single
seal-red accent, the gold focus ring, the type ramps, the spacing, and the motion tokens in
`web/webclient-app/styles/tokens.css`, with the subsetted self-hosted `.woff2` faces in
`web/webclient-app/fonts/`. The validated design draft is the binding reference for any visual or
navigational detail this section leaves unstated.

- Backgrounds use charcoal and near-black rather than pure black.
- Primary text uses warm paper gray.
- Vermilion marks active focus, the current map position, and critical warnings.
- Status and health information is never conveyed by color alone: borders, icons, labels, and shapes
  accompany every color distinction (the not-color-only `.status-marker--*` utilities are enforced at the
  token level).
- Serif typography (self-hosted faces) may be used for narrative and headings; controls use a highly
  legible UI face.
- Art never carries text required to understand state.
- The reduced-motion preference disables nonessential transitions at the token level (the
  `prefers-reduced-motion` kill-switch in `tokens.css`).

### 5.3 Focus model

The action dock owns focus after initial sync and after every completed or rejected UI action.

- Arrow keys move within the current menu grid or list.
- Enter chooses the focused item or submits a complete action.
- Escape pops exactly one menu level.
- Space toggles a candidate in an AREA multi-target menu.
- The command line is a permanently present field with no open/closed state; `/` moves focus into it.
- Sending or cancelling text restores action-dock focus.
- Disabled entries remain focusable so their explanation can be read, but Enter performs no action.
- Holding Enter cannot submit repeatedly. The action dock locks while a mutation is in flight.

The mouse can focus, open, and submit the same controls. No mouse-only action exists.

---

## 6. OOB Protocol

The protocol uses explicit message names and integer versions. The exact transport representation must
follow Evennia's WebClient message conventions, but the logical envelopes are fixed here.

### 6.1 Full snapshot

```json
{
  "protocol_version": 1,
  "presentation_epoch": "9f55f20a",
  "revision": 42,
  "mode": "combat",
  "panels": {
    "status": {"schema_version": 1},
    "context_actions": {"schema_version": 1},
    "local_map": {"schema_version": 1},
    "art": {"schema_version": 1}
  }
}
```

> **Amended 2026-08-09 (change `webclient-combat-menu`).** The `context_actions` panel uses
> `schema_version: 2` in the implementation — its payload is richer than the version-1 example
> (participant tokens, recovery state, and the portrait catalog references added by the combat
> panel). Presenter and validator are self-consistent; the other panels keep version 1.

`ui.snapshot.v1` contains every panel allowed in the current mode. `ui.update.v1` carries the same
top-level fields but contains only replacement payloads for named panels. The client applies an update
only if its revision is newer than the currently rendered revision.

### 6.2 UI action

```json
{
  "protocol_version": 1,
  "presentation_epoch": "9f55f20a",
  "request_id": "session-7:19",
  "base_revision": 42,
  "action_id": "combat.cast",
  "payload": {
    "skill_key": "fire_ball",
    "target_ids": [271]
  }
}
```

The actor is never part of the payload. It is taken from the authenticated session's puppet. Every
adapter defines its own exact payload schema, maximum collection sizes, and allowed scalar lengths.
Unknown fields are rejected rather than ignored.

### 6.3 Action descriptors

Server-rendered menus contain stable descriptors:

```json
{
  "action_id": "combat.cast",
  "label": "影斬",
  "enabled": false,
  "disabled_reason": {
    "code": "insufficient_sp",
    "message": "SP 不足"
  },
  "cost": {"sp": 18},
  "target": {"kind": "single", "choices": []}
}
```

The displayed enabled state is a preview. Dispatch always rebuilds the action request and runs the
authoritative domain validation.

### 6.4 Revision and deduplication rules

- Each connected WebClient transport has a server-generated opaque `presentation_epoch` and one
  monotonically increasing revision within that epoch.
- The first valid full snapshot on a new active transport atomically replaces ClientStateStore state,
  adopts its epoch, and resets revision comparison. Packets from every older epoch are discarded.
- Every update and action carries the active epoch. An action with the wrong epoch is stale and is not
  dispatched.
- A mutation with a stale `base_revision` is not dispatched. The server returns the newest full
  snapshot.
- Only one mutation may be in flight per session.
- Recent `request_id` values and their results are cached for that live session. A duplicate receives
  the cached result and is not executed again.
- The client never automatically retries a mutation after transport loss. Reconnection obtains a
  canonical full snapshot and warns that the previous result could not be confirmed.
- Read-only focus and submenu operations remain client-local unless they require a new lazy server
  payload. Focusable entity descriptors reference entries in the server-authored portrait catalog, so
  local focus can switch a verified portrait without sending state or constructing an asset URL.

### 6.5 Synchronization sources

- Login, puppet change, reconnect, explicit sync, or layout reset sends a full snapshot. A new transport
  receives a new epoch; a puppet change within one transport also starts a new epoch before its snapshot.
- A completed or rejected UI action sends its result and all affected panel replacements.
- A normal text command sent by the WebClient is followed by a snapshot after synchronous command
  completion, so manual commands do not leave panels permanently stale.
- Art completion pushes only the art panel to connected sessions currently referencing that asset.
- Player-driven clock changes occur through player actions, so their resulting snapshot includes the
  new header, status, shops, and quests.

Narrative text continues through the existing text output path. No OOB consumer parses it.

---

## 7. Player-Facing Surfaces

### 7.1 Narrative log

The narrative log shows room appearance, scripted and generated dialogue, EventLog rendering,
Narrator prose, and command feedback. When the player has scrolled upward, new output increments an
unread marker without forcing the viewport to the bottom. The log remains usable if every structured
panel fails.

### 7.2 Character status

The compact status payload contains:

- HP, MP, and SP current and maximum values;
- active buffs and debuffs with duration or remaining ticks when defined;
- only sexual-state values currently crossing a combat modifier threshold, together with the exact
  applied modifier supplied by the deterministic core;
- active incapacity or zero-action reasons;
- current combat round and mode when relevant.

The compact panel always uses true combat state. It never uses `disguised_stats`. The expanded
character panel can show both true values and an explicit description of outwardly displayed values,
because the player must understand their own disguise without letting it influence resolution.

### 7.3 Exploration action dock

The exploration root contains Move, Look, Interact, Character, Quests, and Inventory.

- **Move** lists actual exits. Submission traverses the selected Exit and uses the existing movement
  clock path. It never sends a destination room ID for direct relocation.
- **Look** lists the room, present entities, and present objects.
- **Interact** first selects a present target, then shows only affordances supported by that target and
  existing deterministic APIs, such as talk, engage, take, guild, or shop.
- **Character** opens complete traits, passive skills, equipment state, disguise information, guild
  rank, and wallet.
- **Quests** opens active records and legal actions.
- **Inventory** lists repeated item keys and actions that already have a deterministic API. It does not
  invent item use or equipment effects.

Scripted dialogue keywords are buttons. Open-ended NPC dialogue opens the command drawer with the
target fixed by opaque server identity; the player types only the speech.

### 7.4 Combat action dock

The combat root contains Attack, Skills, Items, Defend, and Flee.

- Attack invokes the innate `basic_attack` after target selection.
- Skills lists all owned active skills in stored order and paginates without reordering them.
- Items and Defend are present but disabled with `not_implemented` explanations in this suite.
- Flee invokes the existing innate `flee` skill.
- Forfeit lives under a secondary combat menu and requires explicit confirmation because it differs
  from an ordinary resolver-backed flee attempt.

Passive skills are visible only in character details. Unavailable active skills remain in the skill
list with stable reasons for insufficient resources, target mismatch, combat restriction, or action
incapacity.

Target behavior follows `TargetSpec`:

| TargetSpec | UI behavior |
|---|---|
| `NONE` | Submit without a target screen |
| `SELF` | Bind the actor server-side and show the binding in the detail pane; send no target field |
| `SINGLE` | Choose one server-provided valid candidate |
| `AREA` | Use Space to select candidates; Enter submits the explicit list or approved shorthand |

`combat.cast` uses one unambiguous wire shape. NONE and SELF send only `skill_key`. SINGLE sends
`target_ids` with exactly one opaque ID. AREA sends either a nonempty bounded `target_ids` list or one
mutually exclusive `target_shorthand`. Any target field that conflicts with the registry's `TargetSpec`
rejects with `target_spec_mismatch` before a round starts.

The current combat-session facade accepts only one optional target, even though `ActionRequest`
supports a list or area shorthand. The combat UI change therefore expands the session facade to accept
multiple targets. Telnet receives deterministic session target tokens and the existing `all-enemies`,
`all-allies`, and `all` shorthands. The browser does not gain exclusive combat capability.

An overwhelm encounter still waits for the first player choice. Once submitted, the dock locks while
the deterministic compressed resolution runs. All resulting logs are rendered; the browser does not
simulate skipped turns.

### 7.5 Guild, quest, shop, and inventory menus

The guild surface covers registration, board listing, quest detail, acceptance, active log, abandon,
turn-in, merit, and guild examination. It uses stable quest and branch IDs and preserves every location,
rank, merit, and exactly-once reward check.

The shop surface covers stock, exact copper prices, wallet, quantity selection, buy, eligible inventory
items, and sell. Closed shops, insufficient funds, insufficient stock, and stock cap are visible disabled
reasons and are rechecked by the economy API.

Quantity fields accept only bounded positive integers. The browser never calculates price totals as
authority; it displays a server preview and receives the committed result.

### 7.6 Rest and wait

The action dock offers common rest durations and the four named time boundaries supported by the
current commands. A custom duration uses a validated form field. Combat and safety restrictions remain
server checks. The menu cannot sleep in an unsafe location merely because the option was rendered
earlier.

### 7.7 Character creation

Pending characters receive a creation mode rather than the normal exploration dock. Presets, race,
and allocation choices are finite controls. Name and other free-form values are text fields. The UI
invokes the same creation state service and all-or-nothing activation flow as the command wizard.

The adult invariant remains non-negotiable. Both `age < 18` and `apparent_age < 18` are rejected by the
server even if client validation is disabled or bypassed.

---

## 8. Map Knowledge and Minimap

### 8.1 Persisted knowledge

The player stores a versioned set of visited node IDs with first-seen and last-seen world ticks. It
does not persist copies of room names, map glyphs, exits, or static geometry. Presentation derives those
facts from current map data, preventing duplicated map truth.

Successful arrival routes through `world/rules/map_knowledge.py`, the sole writer for character map
knowledge. Each movement layer calls that service from its existing successful-arrival seam. Teleports
used by activation may record the destination without charging movement time. Failed or rolled-back
movement never records discovery.

### 8.2 Node identities

| Layer | Stable identity | Geometry source |
|---|---|---|
| Anchor/Grid | `grid:<z-map-key>:<x>:<y>` | XYMap nodes, links, options, and configured visual range |
| Wilderness | `wild:<name>:<x>:<y>` | wilderness coordinates and cardinal availability |
| Instance | `room:<dbref>` | current `InstanceRoom` and real Exits only |
| Ordinary interior | `room:<dbref>` | current room and real Exits only |

Unknown nodes are not sent to the browser. The current node uses the vermilion marker. Visible but
unvisited nodes are bright gray. Previously visited nodes outside current vision are dimmed.

For Instance and ordinary interior graphs, every currently visible and traversable one-hop Exit is sent
as an edge to a `visible_unvisited` destination node even when that room has not been entered. Until
visited, the destination label is `未探索`; only the Exit key/direction is revealed. The canonical room
name and other details appear after discovery.

Only an adjacent, currently traversable exit is actionable. Selecting it submits the ordinary movement
adapter. Remote known nodes can show a name and landmark but cannot trigger travel.

### 8.3 Instance amendment

The 2026-08-01 map-instance design deliberately excluded `InstanceRoom` from every map rendering. This
design explicitly narrows that exclusion. Instance rooms remain absent from xyzgrid ASCII maps,
wilderness maps, shortest-path calculations, and world maps. The WebClient may render a coordinate-free
local graph containing the current node, its origin, and known real Exit relationships.

When an ephemeral room is reclaimed, its `room:<dbref>` knowledge is pruned. A promoted room keeps its
dbref and visited identity. The current implementation supports one-room instances; the graph renderer
does not imply support for nested or multi-room instances.

---

## 9. Art and Portraits

### 9.1 Subject keys

The art subsystem uses namespaced keys:

| Kind | Key | Reuse policy |
|---|---|---|
| Scene | `scene:<archetype>` | Every room with the same scene archetype shares the asset |
| Named character | `portrait:character:<stable-key>` | One asset for the player or explicitly named NPC |
| Generic monster | `portrait:monster:<archetype>` | Every generic monster of that archetype shares the asset |

Whether an NPC is named is explicit creation/import metadata. Display-name shape or uniqueness is not a
policy. A subject lacking validated identity and description data is not enqueued.

### 9.2 Adult image invariant

Portrait prompt data may be built only from a character record that has passed both adult gates. Prompt
construction never invents a younger apparent age. A missing or invalid age record produces no portrait
job and leaves the placeholder in the UI.

### 9.3 Queue and worker

Scenes and portraits share one serialized, locked queue and one external worker command. Jobs use the
approved contract:

```json
{
  "kind": "portrait",
  "key": "portrait:monster:gray_wolf",
  "description": "validated natural-language subject description",
  "out_path": "server/.art/...",
  "aspect_ratio": "3:4"
}
```

Scene jobs use 16:9 and portrait jobs use 3:4. The project is unreleased, so the scene-only worker
contract is replaced directly without a compatibility adapter. Completed keys are idempotent. Retry and
forced regeneration remain staff operations, never ordinary player actions.

`world/art/service.py` is the only art queue writer. Startup idempotently ensures registered scene and
generic-monster subjects plus existing eligible unique character policies. Successful character
creation/import and validated named-NPC spawn schedule unique portrait ensure after their gameplay
transaction commits. Successful room entry ensures its validated scene subject. A queue failure logs and
degrades to a placeholder without rolling back gameplay; later startup/entry synchronization retries the
missing idempotent record. Presenters and workers never enqueue as a side effect of rendering.

The generated asset root is `server/.art/`. It is gitignored and mounted persistently at
`/app/server/.art` in containers. The `art-assets` delivery replaces the bootstrap compose mount at
`/app/world/art`, because that location would mask the future importable `world/art/` Python package.

### 9.4 UI behavior

The server sends an asset status, same-origin media URL, and meaningful alternative text, never a local
filesystem path. The art panel payload contains the current scene plus a bounded `portrait_catalog`
keyed by the opaque IDs of currently focusable, present entities. Each catalog value contains the
server-resolved subject key, status, URL/placeholder, and alternative text. Menu descriptors reference
only those catalog IDs.

The current scene fills the art panel. The KeyboardRouter emits a client-local focus event, and the art
renderer selects the corresponding catalog entry for the current dialogue speaker or highlighted combat
target. It never derives a portrait key or URL from entity data. Art completion replaces the catalog and
scene payload at a newer revision.

When no contextual character exists, the portrait is absent. Pending, failed, invalid, or offline portrait
assets use named placeholders. When a scene is pending and prior scene art is already rendered, that art
remains visibly dimmed and labelled "目前場景圖片生成中"; without prior art, the panel uses a scene
placeholder. Failed or invalid scene assets always use the placeholder. Gameplay never blocks on a job.

---

## 10. Error Handling, Reconnect, and Degradation

| Situation | Required behavior |
|---|---|
| Initial sync | Show a synchronization state and disable mutation actions until a valid full snapshot arrives |
| WebSocket disconnect | Preserve the rendered view under an offline overlay; submit nothing; do not advance the player-driven clock |
| Combat reconnect | Restore the persisted session, round count, participants, status, targets, and combat menu from a full snapshot |
| Stale action revision | Perform no mutation; return the newest snapshot and explain that state changed |
| Duplicate live request ID | Return the cached result without executing again |
| Disconnect after submit | Never auto-retry; resync canonical state and warn that the result could not be confirmed |
| Domain rejection | Return stable code and Traditional Chinese message; unlock the menu; preserve atomicity |
| Unknown panel schema | Disable only that panel, retain narrative/command access, and request a full sync |
| Incompatible protocol | Disable graphical actions and ask for a reload; keep text input available |
| Presenter failure | Log a diagnostic and mark only that panel unavailable when isolation is possible |
| Internal dispatcher error | Log a correlation ID, return a generic player error, unlock, and full-sync; never expose traceback |
| LLM unavailable | Use the existing deterministic template renderer |
| Art service unavailable | Use placeholders; queue status may remain pending/failed |
| OOB UI unavailable | Preserve normal WebClient text input and Telnet playability |

---

## 11. Security and Accessibility

### 11.1 Input security

- `ui_action` requires an authenticated WebSocket session with an active puppet.
- Actor identity is always read from the session.
- Envelope depth, field count, string lengths, list sizes, numeric ranges, and action IDs are bounded.
- Unknown actions and payload fields are rejected.
- Every target, exit, quest, merchant, item, skill, and quantity is re-resolved and re-authorized.
- Same-room, alive, faction, rank, stock, balance, safety, and ownership checks remain domain concerns.
- Narrative and player text use the existing ANSI/HTML escaping path before DOM insertion.
- Art URLs must be same-origin media URLs generated by the server.
- localStorage contains layout and harmless display preferences only, never canonical state or secrets.

### 11.2 Accessibility

- Every finite ordinary action is keyboard reachable.
- Focus is visible by shape and border in addition to color.
- Disabled reasons use `aria-describedby` and remain keyboard readable.
- Resource bars include numeric current/maximum text.
- New action results use a non-interrupting live region.
- Reduced-motion preference removes nonessential transitions.
- Art supplies useful alternative text; no required information exists only inside an image.

---

## 12. Testing Strategy

### 12.1 Server tests

- Pure presenter and protocol tests use `unittest.TestCase` and deterministic JSON fixtures.
- Protocol tests cover epoch adoption, revision ordering inside one epoch, and delayed old-epoch packets.
- Database, session, command, movement, combat, service, and OOB tests use `EvenniaTest`.
- Every action adapter tests authentication, stale revision, duplicate request, unknown fields, tampered
  IDs, domain rejection, success, and resulting panel replacements.
- Presenter isolation tests inject one malformed surface and assert other panels still render.
- New main-spec requirements carry canonical `covers_requirement` annotations.

### 12.2 Client tests

State reduction, revision gating, menu stacks, focus movement, disabled entries, and keyboard routing are
kept in DOM-independent JavaScript modules and tested with Node's built-in `node --test`. This adds no npm
runtime dependency.

Dev-only Python Playwright and Chromium test the real WebClient at 1440x900 and 1280x720. Browser tests
use localhost only and deterministic placeholders. They cover keyboard-only panel journeys, focus
restoration, reconnect, incompatible schema, layout-version migration, and action locking.

`webclient-oob-foundation` owns making these gates executable. It adds Playwright through
`uv add --dev playwright`, commits the resulting `pyproject.toml` and `uv.lock` changes, and provides a
`unittest` browser harness that starts an isolated Evennia database/server, seeds deterministic accounts
and characters, polls `http://127.0.0.1:4001/webclient/` for readiness, and always stops the server. CI
installs Chromium with `uv run --locked playwright install --with-deps chromium`, runs DOM-independent
JavaScript with `node --test web/static/webclient/js/tests/*.test.js`, and runs browser tests with
`uv run --locked python -m unittest discover -s web/tests/browser -t .`. The quality-gate workflow adds
those steps; browser tests do not silently become local-only checks.

### 12.3 Panel acceptance

| Panel | Acceptance boundary |
|---|---|
| Combat | Complete basic attack, skill selection, SINGLE/SELF/NONE/AREA targeting, flee, disabled reason, rejection, and reconnect without typing a command |
| Map/Exploration | Verify vision, visited knowledge, legal adjacent movement, time charging, and layer-specific rendering for grid, wilderness, instance, and interior rooms |
| Services | Complete guild, quest, shop, and inventory success/rejection/stale flows independently |
| Art | Verify done, pending, failed, offline, client-local catalog focus switching, URL restriction, and adult prompt gate |
| Creation | Complete preset and custom forms; permanently reject either age below 18 |
| Shell | Run one short smoke journey through mode changes and shared panel updates |

No required test calls a live LLM, Stable Diffusion, or remote service. Python remains subject to the
existing 90% branch-coverage gate. Node and Playwright entry points are additional required checks.

---

## 13. Delivery Roadmap

The suite is intentionally not one implementation plan.

| Order | OpenSpec change | Depends on | Delivers |
|---|---|---|---|
| Wave 1 | `webclient-oob-foundation` | current deterministic milestone | protocol, input functions, snapshot coordinator, state store, keyboard router, Vue SPA shell, status panel |
| Wave 2A | `webclient-combat-menu` | foundation, player combat sessions | combat presenters/actions, targets-list session facade, Telnet target parity, combat browser tests |
| Wave 2B | `map-knowledge-minimap` | foundation, all current map layers | persistent visited nodes, four layer adapters, local map presenter, instance amendment |
| Wave 2C | `webclient-service-menus` | foundation, guild/economy/quest APIs | guild, quest, shop, inventory menus |
| Wave 2D | `webclient-character-creation-ui` | foundation, current creation/onboarding APIs | pending-character mode, preset/custom forms, activation transition |
| Wave 3 | `webclient-exploration-menu` | foundation, map knowledge, NPC dialogue | movement, look, interaction, scripted/free-form dialogue, rest/wait menus |
| Wave 4 | `art-assets` | SceneBuilder, current room/character/archetype seams | scene and portrait subjects, generated named-NPC portrait lifecycle, generic queue, worker contract, placeholders |
| Wave 5 | `webclient-art-panel` | foundation, art assets | scene renderer, portrait overlay, zoom, OOB art updates |

Delivery uses dependency waves rather than waiting for every Phase 5 change before UI work:

1. `llm-client` and `webclient-oob-foundation` start in parallel.
2. After `llm-client`, Narrator, NPC dialogue, and ScenarioDirector proceed in parallel. After the UI
   foundation, combat menu, map knowledge, service menus, and character-creation UI proceed in parallel.
3. SceneBuilder follows ScenarioDirector. Exploration menu joins completed NPC dialogue with map knowledge.
4. Art assets follows SceneBuilder so its generated named-NPC portrait hook lands against a real owner.
5. The art panel follows both art assets and the UI foundation.

This yields independent critical paths: combat UI is `foundation → combat`; complete exploration joins
`llm-client → NPC dialogue → exploration` with `foundation → map knowledge → exploration`; generated art
display is `llm-client → ScenarioDirector → SceneBuilder → art assets → art panel`. Narrator does not block
the UI because deterministic EventLog templates remain the required fallback. Every change has its own
delta specs, tasks, traceability, and strict verification.

---

## 14. Focused Design Documents

- `2026-08-02-webclient-oob-foundation-design.md`
- `2026-08-02-webclient-combat-ui-design.md`
- `2026-08-02-webclient-map-exploration-ui-design.md`
- `2026-08-02-webclient-service-creation-ui-design.md`
- `2026-08-02-webclient-art-portrait-ui-design.md`

These documents define each unit's interface, dependencies, and test boundary. The OpenSpec proposal
for a unit must be based on both this document and its focused design.

---

## 15. Risks and Trade-offs

- **The Vue layout-store localStorage can preserve obsolete structures.** Layout versions and required-panel
  migration prevent an old configuration from hiding the action dock.
- **Enumerating every skill-target combination can become expensive.** Presenters build bounded,
  context-specific menus and may load a submenu lazily. They never enumerate unbounded room contents.
- **Client availability can become stale between render and submit.** Base revisions reject known stale
  state, and domain validation always runs again.
- **A transport drop can hide an action result.** The client never auto-retries a mutation and instead
  resynchronizes canonical state.
- **Portraits increase queue and storage pressure.** Only explicitly named characters receive unique
  portraits; generic monsters reuse archetype assets; one serialized worker remains the GPU boundary.
- **Local instance maps revise an earlier design.** The amendment is restricted to real Exit graphs and
  introduces no coordinate, world-map membership, pathfinding, nested instance, or multi-room support.
- **Playwright adds CI weight.** It is dev-only and justified by keyboard focus, reconnect, and layout
  behavior that server tests cannot establish.
- **Desktop-only excludes mobile users.** This is an explicit first-release constraint, not accidental
  responsiveness debt. A mobile design requires a separate specification.
