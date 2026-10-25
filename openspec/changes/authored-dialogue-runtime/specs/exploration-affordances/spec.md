# Spec Delta

## MODIFIED Requirements

### Requirement: Affordance params are validator-normalized
Every action entry's `params` SHALL be the normalized output of that action's registered
validator in `web/webclient/actions/exploration_actions.py` applied to a candid payload the
builder constructs, so the dispatched payload is byte-for-byte the payload the dispatcher
accepts. Exact candid payload shapes are scenario-pinned.

#### Scenario: Every emitted entry executes against its real adapter
- **WHEN** a unit or integration test takes the vocabulary emitted for a fixture room and
  dispatches each suggestible action entry through the production dispatcher
- **THEN** no `malformed_payload` rejection occurs, and the move entry passes the adapter's
  `stale_location` comparison unchanged

#### Scenario: Move source and destination use one encoder
- **WHEN** a move affordance is built for an ordinary room, `GridRoom`, or `TerrainRoom`
- **THEN** its current node and destination node are derived only through `node_id_for_location`,
  with no duplicate room-type encoder in the affordance module

#### Scenario: The freeform entry stays a binding shape
- **WHEN** an `explore.talk_freeform` `AffordanceView` is constructed
- **THEN** its `params` equals `{"npc_id": <present LLMNPC id>}` and no validator normalization
  is applied to it

#### Scenario: The delivery entry carries its normalized dispatch payload
- **WHEN** an `explore.deliver` `AffordanceView` is constructed for a co-located bound recipient
- **THEN** its `params` is the registered delivery validator's normalized output for
  `{"npc_id": <recipient id>, "item_key": <objective item key>}`, and dispatching it through the
  production dispatcher produces no `malformed_payload` rejection

#### Scenario: Candid payload shapes are exact per action
- **WHEN** a builder constructs the candid payload for each action
- **THEN** the shapes are: `explore.move` `{"exit_ref", "current_node"}`, `explore.look`
  `{"target_id"}` or `{"room": true}`, `explore.talk_scripted` authored `{"npc_id", "topic_id", "context_id", "selection_id"}` or native generated `{"npc_id", "keyword_id"}`,
  `explore.party_invite` `{"npc_id", "message"}` (message empty by construction),
  `explore.party_leave` `{"npc_id"}`, `explore.engage` `{"monster_id"}`, `explore.wait`
  `{"daypart": "noon"}`, `explore.possess` `{"npc_id"}`, `explore.possess_release`
  `{"npc_id"}`, and `explore.deliver` `{"npc_id", "item_key"}`

#### Scenario: Freeform is the single validator exception
- **WHEN** an `explore.talk_freeform` entry is considered
- **THEN** it is the single exception — no registered validator produces its shape without
  `speech` — so the full validator SHALL run only on the client-composed dispatch payload
  (`speech` = the label text) defined by the later suggestions slices

#### Scenario: A rejected candid payload is a logged test bug
- **WHEN** a builder's candid payload is rejected by its validator
- **THEN** it SHALL be treated as a logging bug in tests, never silently omitted

#### Scenario: All move node IDs share one encoder
- **WHEN** a move entry's `current_node` and its destination-node derivation are computed
- **THEN** both SHALL call the shared pure node-ID encoder
  (`web/webclient/actions/node_ids.py::node_id_for_location`), and the move adapter's
  `stale_location` check and every ordinary-room, `GridRoom`, and `TerrainRoom` move affordance
  SHALL therefore share one byte-identical encoding implementation
