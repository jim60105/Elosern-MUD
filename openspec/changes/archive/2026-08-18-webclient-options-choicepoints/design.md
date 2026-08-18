## Context

The AI action-options slicing (overview `2026-08-15-ai-action-options-overview-design.md`,
decision A-6) dual-places `ready` suggestion cards: a persistent dock section
(`webclient-options-surface`, shared card component) and a **narrative choice-point** — the VN
moment where the player is reading the story. This change lands the stream placement.

Schema-version note (roadmap amendment from the affordance-contract change): `context_actions`
is already v3 (combat); the affordance-contract change lands **v4** (exploration form, no
suggestions); the sibling roadmap change `context-actions-suggestions` lands **v5** (adds the
`suggestions` section). Throughout this change, "context-actions-suggestions" refers to that
roadmap change name, not a wire schema version; the old design set's "v3 validator" wording is
superseded (see affordance-contract proposal.md).

Facts the change builds on:

- The narrative stream is owned by `window.Elosern.narrativeInput` (`web/static/webclient/js/
  plugins/goldenlayout.js:1282`), currently exposing `appendInput` for player-input echo lines;
  scroll-keep plus the polite unread marker are single-owner there (design D5).
- The presentation store (`elosern/protocol.js`) replaces panels wholesale per
  `commitPresentation` (update or snapshot), then notifies `subscribe` listeners; the choice-point
  reads `panels["context_actions"].suggestions` from committed state only.
- `suggestions` has four statuses — `generating` / `ready` / `degraded` / `unavailable` — with the
  card count contract (ready 3–5, degraded ≥ 1 in v1) owned by the schema change; the payload
  lands with the context_actions v5 change, the dock + shared card renderer with the surface
  change. This change consumes both, adds no protocol surface.
- `options.dismiss` (dismiss change) is the sole eviction path; the dock section and the stream
  group both carry the "✕ 清除建議" control.
- Evennia-side server runs of the browser suite boot one server per *file*; an
  exploration-only test file keeps the shared-server reuse rule (no combat sessions).

## Goals / Non-Goals

**Goals:**
- The stream-end block lifecycle: append generating line → in-place ready replacement →
  removal (unavailable / dismiss / degraded / non-exploration / reconnect).
- The movable end-block invariant: later narrative appends relocate the block to the new end;
  scroll-keep/unread stay single-owner through the facade.
- One card renderer, one click path, one dismiss action across dock and stream (envelope parity).
- Deterministic, committed-state-only behavior; no transport hints; safe per page; Node-testable
  core.

**Non-Goals:**
- Any change to the `suggestions` payload, panel version, server validator, or protocol
  (`degraded` in the dock, `ready`/`generating` in the stream — unchanged from the webclient doc).
- Rules for producing the cards (LLM/gen layer) or the dock section itself (surface change).
- Option interpretation, reordering, rating, streaming output, or per-player personalization.
- A second narrative append path: the block is the facade's responsibility, not a new raw
  container writer.

## Decisions

- **Movable stream-end block owned by the `narrativeInput` facade.** The facade grows
  `mountChoicePoint(element)`, `moveChoicePointToEnd()`, `replaceChoicePoint(element)`, and
  `unmountChoicePoint()` (names illustrative) implemented inside goldenlayout.js so the stream's
  end geometry, scroll-keep, and unread marker stay one owner. The internal path appends new
  narrative text and relocates the block within **one** scroll/unread decision: text lands before
  the block, the block stays last, no relocation-triggered scroll or extra unread marker occurs.
  *Alternative considered:* the choice-point module appends/relocates the block itself — rejected:
  two writers on the same container is exactly the multi-writer hazard the D5 facade exists to
  prevent, and the text-after-update ordering test would be untestable without a single geometry
  owner.
- **Choice-point state derives exclusively from committed `context_actions`.** The module
  subscribes to the store's `subscribe` notifications; on each notify it diffs
  `state.panels["context_actions"].suggestions` against its remembered status. Every transition is
  a pure function of (old status, new status, new cards) — Node-testable without a DOM. No
  generation-side metadata, no dispatch interception.
  *Alternative considered:* a separate OOB push targeted at the stream — rejected: `ui_update`
  already replaces the whole panel; a second message type is explicitly out of scope in the
  overview.
- **Stream shows only `generating` and `ready`; everything else removes.** `degraded` is a
  reference surface (dock); `unavailable`, combat/creation modes, panel absence, unknown status,
  and malformed card shapes all map to removal. This is the declared v1 behavior from webclient
  doc §4 (the §7 open question about degraded choice-points stays open; flipping it later is a
  one-line change in the transition table).
- **In-place replacement, never stacking.** generating → ready replaces the single line element
  with the card group node (same facade call-site). generating → generating renders nothing (the
  trigger service already publishes generating only once per transition).
- **One card renderer shared with the dock.** The surface change owns the card group factory
  (module + exported factory name pinned there); this change consumes it via a fixed loading
  order (see "Sibling-slice integration contract" below). Envelope parity is asserted in Node by
  running the same click-handler unit against dock and stream instances (spec scenario
  "A stream card and its dock twin dispatch identically").

## Sibling-slice integration contract (review fix)

Two sibling changes provide contracts this change consumes, and their artifacts are not all
landed yet — the following is the fixed integration contract this change depends on, so the last
slice never copies a renderer or invents a module:

- `context-actions-suggestions` (roadmap name): `context_actions` wire schema **v5** with the
  `suggestions` section (`{status, cards}`; statuses `generating`|`ready`|`degraded`|
  `unavailable`; cards with `kind`/`action_code`/`label`/`params`/`hint`) and the client mirror
  that rejects out-of-contract payloads at commit time.
- `webclient-options-surface`: exports the shared card group factory (a single entry point,
  e.g. `renderSuggestionCards(cards, handlers)` returning a node), the dock's dismiss control
  wiring (dispatching `options.dismiss`), and registers both the dock module and the shared
  factory in the page script set. The factory SHALL be the only place that creates card
  elements; this change imports it and never constructs card DOM itself.
- Loading order in the page script set: clock/protocol store, goldenlayout (facade), actions
  (action client), surface (shared renderer), then the choice-point module — the module's
  init SHALL be a no-op until the store, the facade, and the shared renderer are all present
  (explicit readiness gate, not load-order luck), and the base.html script registration for the
  choice-point module is part of this change's task list.
- The action-client lock (`mutationsLocked`, in-flight marker) is the single admission rule for
  both dock and stream card clicks; the stream path reuses the exact same client entry point,
  so a stream card click while locked is rejected by the same code path as a dock card click.

If a sibling contract drifts (e.g. the surface change exports a different factory name), this
change's tasks fail loudly at the import/parity test rather than degrading silently.
- **Dismiss control in the stream group, same action.** Reuses `options.dismiss`; removing the
  block is the client-side mirror of the server's `unavailable` publish (the dismiss adapter
  already publishes unavailable, so removal rides the same commit path — no direct unmount on
  click; the click dispatches, the subsequent commit removes).
  *Alternative considered:* optimistically unmounting on click — rejected: the committed-state
  invariant means the server publish (or a race-safe no-op) is the single source of truth for
  both surfaces.

## Risks / Trade-offs

- **Async race between narrative text and choice-point commits** (look output, talk replies,
  scene-flavor pushes landing after a ready commit) → the movable end-block semantics: any
  append relocates the block to the new end; the text-after-update Node test pins the ordering;
  the browser file asserts it once against a live server.
- **Two surfaces can disagree transiently** (dock shows ready while stream is mid-removal, or
  vice versa) → both read the same committed panel; the transition diff is idempotent (a
  repeated identical status commit is a no-op), so any later commit reconciles; worst case the
  next snapshots both surfaces together.
- **Facade contract creep** (goldenlayout.js gains block APIs) → the API is a tiny fixed set of
  four operations used by exactly one consumer; the facade keeps `appendInput` semantics
  byte-identical (existing Node/browser narrative tests stay green).
- **Unknown-status payloads reaching the module** → the v5 client mirror already rejects
  out-of-contract suggestions at commit time; the module additionally treats anything outside
  the four known statuses as removal (defense in depth, Node fixture).
- **Browser-suite cost** → one exploration-only file, shared server, existing shard owner
  conventions; no combat-boot per test.

## Migration Plan

No released users and no data: this is a client-only addition behind the existing protocol
surface. Deploy order within the slicing: land `context-actions-suggestions` (suggestions payload) and
`webclient-options-surface` (dock + shared card renderer) first, then this change; the module is
inert until a committed suggestions status arrives. Rollback: remove the module registration —
older payloads (no suggestions section) map to removal and leave the stream exactly as before
this change.

## Open Questions

- Whether `degraded` rule cards later become a stream affordance (webclient doc §7) — v1 keeps
  the stream AI-only; the transition table isolates the one-line change.
- Whether future narrative surfaces (e.g. a log pane filter) need the block to participate in
  their layout — the facade API is the seam.