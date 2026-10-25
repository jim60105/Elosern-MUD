# Spec Delta

## MODIFIED Requirements

### Requirement: Affordance params are validator-normalized
Action descriptors SHALL be validator-normalized. Authored topic descriptors SHALL omit selection identity and pass a descriptor validator; dispatch SHALL add the admitted request identity before full action validation. Native freeform composition SHALL retain its existing exception. Other normalized payloads SHALL remain byte-identical through dispatch.

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
  `{"target_id"}` or `{"room": true}`, `explore.talk_scripted` authored descriptor `{"npc_id", "topic_id", "context_id"}` or native generated `{"npc_id", "keyword_id"}`; the dispatcher injects request-derived selection identity into authored requests before full validation,
  `explore.party_invite` `{"npc_id", "message"}` (message empty by construction),
  `explore.party_leave` `{"npc_id"}`, `explore.engage` `{"monster_id"}`, `explore.wait`
  `{"daypart": "noon"}`, `explore.possess` `{"npc_id"}`, `explore.possess_release`
  `{"npc_id"}`, and `explore.deliver` `{"npc_id", "item_key"}`

#### Scenario: Freeform retains its native composition exception
- **WHEN** an `explore.talk_freeform` entry is considered
- **THEN** no registered full validator produces its shape without
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

#### Scenario: Deliberate picks differ from transport retries
- **WHEN** two deliberate activations reuse one projected authored descriptor and a transport retry repeats the first envelope
- **THEN** deliberate requests get distinct admitted request-derived selection identities, the retry retains its original identity, and the builder never allocates one
