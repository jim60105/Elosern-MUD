## MODIFIED Requirements

### Requirement: Affordance params are validator-normalized
Every action entry's `params` SHALL be the normalized output of that action's registered
validator in `web/webclient/actions/exploration_actions.py` applied to a candid payload the
builder constructs (exact shapes: `explore.move` `{"exit_ref", "current_node"}`, `explore.look`
`{"target_id"}` or `{"room": true}`, `explore.talk_scripted` `{"npc_id", "keyword_id"}`,
`explore.party_invite` `{"npc_id", "message"}` (message empty by construction),
`explore.party_leave` `{"npc_id"}`, `explore.engage` `{"monster_id"}`, `explore.wait`
`{"daypart": "noon"}`) — so the dispatched payload is byte-for-byte the payload the dispatcher
accepts. The `explore.talk_freeform` entry SHALL be the single exception: its `params` SHALL be
exactly `{"npc_id": int}` (binding-only), because no registered validator produces that shape
without `speech`; the full validator SHALL run only on the client-composed dispatch payload
(`speech` = the label text) defined by the later suggestions slices. A builder whose candid
payload is rejected by its validator SHALL be treated as a logging bug in tests, never silently
omitted. Both a move entry's `current_node` and its destination-node derivation SHALL call the
shared pure node-ID encoder (`web/webclient/actions/node_ids.py::node_id_for_location`). The move
adapter's `stale_location` check and every ordinary-room, `GridRoom`, and `TerrainRoom` move
affordance SHALL therefore share one byte-identical encoding implementation.

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
