# Design

## Context

`MovementCostMixin.at_traverse` preflights before relocation and delegates to `settle_movement`. `after_successful_movement` invokes `charge_movement`, map arrival and party following. `settle_relocation` is the explicit GM teleport owner and already records population transitions. `wilderness_neighbor` rejects blocked diagonals; `resolve_wilderness_destination` resolves real gateways. `TravellerState.detached()` already supports canonical pricing from projected physiology.

## Goals / Non-Goals

One new mechanism records completed physical edges. Shared read-only discovery is used by production movement in this change, so later escape code does not get a second legality calculator. Do not change prices, authorize retreat, move monsters or bypass sleep/access gates.

## Decisions

### Stable edge contract

Create `world/rules/movement_edges.py` with frozen values and strict JSON codecs. `LocationRef` is a tagged mapping, exactly `{"kind":"wilderness","map":str,"x":int,"y":int}` or `{"kind":"room","id":int}`. Integers exclude bool. A room locator is legal only for a persistent authored room, never a pooled TerrainRoom. Reuse existing canonical map-node codecs inside adapters; this owner representation is not a browser node ID.

`PhysicalEdge(source: LocationRef, destination: LocationRef, route: str)` uses `direction:<normalized direction>` for a wilderness departure and `exit:<positive dbref>` for an authored Exit. A gate remains its actual registered crossing; adjacency does not invent a wall entrance.

Public signatures are `location_ref(entity: Any) -> LocationRef`, `legal_edges(actor: Any, source: LocationRef, members: tuple[Any,...]) -> tuple[PhysicalEdge,...]`, `quote_edge(actor: Any, edge: PhysicalEdge, members: tuple[Any,...], *, states: tuple[TravellerState,...] | None = None) -> TraversalResolution`, `read_previous_edge(body: Any) -> PhysicalEdge | None`, `record_completed_edge(body: Any, edge: PhysicalEdge) -> None`, `invalidate_previous_edge(body: Any) -> None`. `TraversalResolution` is the existing `resolve_traversal_cost` return type, reuse it rather than define new arithmetic. Edges sort by canonical serialized source/destination/route. Discovery and quoting do not create rooms, tick gauges or write Attributes. A named topology/physiology error propagates; ordinary blocked edges are excluded.

Delegate to `wilderness_neighbor`, gateway registry lookup, real Exit access/receive and movement restrictions, and execution `resolve_traversal_cost`/`plan_traversal`. Refactor only the duplicated preflight portions of `typeclasses/exits.py` to use this contract. Expose locator-based adapters for unmaterialized wilderness cells without fabricating rooms. Preserve authorized flight waivers and absence-versus-partial physiology rules. Routing-only weights never enter these APIs. Do not use disclosure/reveal as physical legality for monsters.

### History and traversal visibility

Only the movement owner writes `db.previous_traversal = {"source":LocationRef,"destination":LocationRef,"route":str}` on the active player-driven body, after the whole edge, costs and following succeed. Possession uses the actual controlled body and source-present following set; record each physically transported present party body consistently, remote bodies stay unchanged. Reads validate destination equality with current logical location; return None for absent history and raise a named state error for malformed history. Failed traversal and rollback retain the previous record. `settle_relocation` and every discovered nontraversal move of a controlled body invalidate it in the same operation. Inventory those callers with CodeGraph during the task; do not add a raw move_to patch globally.

Within `settle_movement`, bind a rules-owned immutable traversal scope `(member_ids, source, destination, departure_tick, arrival_tick)` before stock relocation. `field_presence(body, tick)` returns no idle-cell contact during the committed half-open passage interval, even if the pooled room has relocated early. Arrival becomes present only at the accepted arrival tick. This scope joins the full-window snapshot and publication group; no browser timer writes it. Later contact integration consumes this already-executable movement visibility seam.

### Observability

Add `movement_edge_completed` and `movement_history_invalidated` catalog rows in the approved observability design during implementation. Named imports from `world.observability`; outer-commit info includes body/commander, source/destination, route and tick. Unchanged reads and failed operations emit no success. Snapshot history and traversal scope alongside existing Attributes, clock, room contents and coordinate caches.

## Risks / Trade-offs

Pooled-room identity and possession make post-relocation source discovery unsafe. Capture source before stock traversal. Do not replace existing topology or cost policy with a parallel implementation.

## Verification

Existing modules `world.rules.tests.test_movement_settlement`, `test_party_follow_possession`, `test_movement` and `typeclasses.tests.test_exit_movement_cost` establish history/route mechanisms. New `world.rules.tests.test_movement_edges` is registered once in evennia-shards. Synthetic diagonal/corner, locked gate, exact-zero/depletion and no-physiology cases compare actual execution acceptance to quotes. Inject failure after history/arrival writes; reload and live caches must retain the old edge. Teleport, pooled recycle, gate reversal and possession cannot select an unrelated location.

## Implementation evidence contract

The canonical proposal ID for this requirement is `movement-edge-history::completed-physical-edges-retain-stable-player-history`, obtained by running the traceability list tool with `--repo-root /tmp/mud-field-proposed-specs` and `--json-output /tmp/mud-field-proposed-ids.json`. All four scenarios map to tasks1.1-3.1 and test_movement_edges plus the existing movement/possession modules. This is one retained-edge mechanism requirement, not a requirement for code layout or test health.

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
