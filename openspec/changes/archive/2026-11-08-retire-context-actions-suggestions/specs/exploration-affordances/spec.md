## MODIFIED Requirements

### Requirement: Affordance params are validator-normalized
Action descriptors SHALL be validator-normalized. Authored topic descriptors SHALL omit selection identity and pass a descriptor validator; dispatch SHALL add the admitted request identity before full action validation. Native freeform composition SHALL retain its existing exception. Other normalized payloads SHALL remain byte-identical through dispatch.

#### Scenario: Every emitted entry executes against its real adapter
- **WHEN** a unit or integration test takes the vocabulary emitted for a fixture room and
  dispatches each emitted action entry through the production dispatcher
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
  `{"target_id"}` or `{"room": true}`, `explore.talk_scripted` static/generated scene descriptor `{"npc_id", "topic_id", "context_id"}`; the dispatcher injects request-derived selection identity before full validation,
  `explore.party_invite` `{"npc_id", "message"}` (message empty by construction),
  `explore.party_leave` `{"npc_id"}`, `explore.engage` `{"monster_id"}`, `explore.wait`
  `{"daypart": "noon"}`, `explore.possess` `{"npc_id"}`, `explore.possess_release`
  `{"npc_id"}`, and `explore.deliver` `{"npc_id", "item_key"}`

#### Scenario: Freeform is the single validator exception
- **WHEN** the native non-authored affordance vocabulary considers an `explore.talk_freeform` entry
- **THEN** no registered full validator produces its shape without `speech`, so the vocabulary
  carries only the `{"npc_id": int}` binding and the full validator runs only on the composed
  dispatch payload that adds `speech`

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

### Requirement: The idle baseline guarantees at least one executable entry
In exploration mode with a puppeted player inside a location, the vocabulary SHALL always emit an
`explore.look` action entry with `params {"room": true}`. The vocabulary SHALL additionally emit
an `explore.wait` action entry with `params {"daypart": "noon"}` only when the wait adapter's
`unsafe_rejection(actor)` is absent.

#### Scenario: An empty room still yields a nonempty executable baseline
- **WHEN** a room has no exits, no NPCs, no monsters, and no objects
- **THEN** the vocabulary emits the `explore.look` room entry (and, in a safe room, the
  `explore.wait` entry), so the context form always carries at least one executable entry

#### Scenario: An unsafe room never offers wait
- **WHEN** a living Monster is present but no combat session is active
- **THEN** the vocabulary contains no `explore.wait` entry and the room-look entry remains
  eligible

#### Scenario: Baseline entries stay out of the v1 panel payload
- **WHEN** the version-1 `exploration` panel payload is serialized
- **THEN** these idle-baseline entries are members of the affordance vocabulary only and SHALL NOT
  appear in it — look is a section there and wait has no panel affordance

#### Scenario: Baseline entries reach the context form and fallback
- **WHEN** the `context_actions` exploration form is rendered
- **THEN** the idle-baseline entries SHALL appear in it

### Requirement: The shared read-only affordance vocabulary supports possessed shop access
A shared module (`web/webclient/presentation/affordances.py`) SHALL own the canonical
affordance rules for a puppeted player in exploration mode. Every emitted entry SHALL be an
`AffordanceView` that is exactly one of two shapes: an **action entry** (action code, label,
params, freeform, navigation false, enabled, nullable disabled_reason) or a **navigation entry**
(surface, label, navigation true, enabled, nullable disabled_reason). Exact field sets and
emission rules are scenario-pinned.

#### Scenario: The exploration panel and the context form share one vocabulary
- **WHEN** the same room is presented to the same puppeted actor through both the `exploration`
  panel and the `context_actions` exploration form
- **THEN** both surfaces enumerate the same eligible targets and the same non-talk actions with
  identical ids, labels, gates, and disabled states; every target that has talk entries in the
  context form carries exactly one 交談 `explore.talk_open` affordance in the panel with the same
  enabled state and possession reason; and both serializations are unchanged before and after a
  canonical-state comparison

#### Scenario: A dead monster stays visible as a disabled entry
- **WHEN** a present Monster is dead
- **THEN** the vocabulary contains its `explore.engage` action entry with `enabled` false and a
  stable `target_dead` disabled reason, exactly as the v1 panel rendered it

#### Scenario: A navigation entry carries no dispatcher code
- **WHEN** an unpossessed actor sees a guild or shop host, or a possessed actor sees a shop host
- **THEN** the vocabulary contains a navigation entry with `surface` `"guild"`/`"shop"` as applicable,
  `navigation` true, and no `action_id` and no `params`, and no `ui_action` registry lookup exists for it

#### Scenario: Possess entries mirror the deterministic gates
- **WHEN** a bound companion stands beside the player while a combat session is active
- **THEN** the vocabulary carries that companion's `explore.possess` entry disabled with the
  combat gate's stable code, and the same entry is enabled once combat ends

#### Scenario: Release is offered exactly once, only while possessing
- **WHEN** the actor possesses a companion and the vocabulary is emitted
- **THEN** exactly one `explore.possess_release` entry is present, and no unpossessed-emission
  vocabulary contains it

#### Scenario: The possessed actor keeps engage disabled and normal shop access
- **WHEN** the puppeted actor is a possessed NPC and a live monster and an available shop host are present
- **THEN** the engage entry remains visible disabled with `possessed_engage` and its fixed message,
  while the shop navigation entry is enabled with no possession-specific disabled reason

#### Scenario: The possessed actor has no guild navigation entry
- **WHEN** the puppeted actor is a possessed NPC and a guild host is present
- **THEN** neither the exploration panel nor the context vocabulary emits a guild opener, disabled guild row, or synthetic guild refusal message

#### Scenario: Possessed shop navigation retains ordinary service gates
- **WHEN** a possessed actor is beside a merchant whose service is off-anchor or has a malformed binding
- **THEN** the shop entry carries the same disabled state and fixed service-gate message as without possession

#### Scenario: An available delivery is offered for the bound recipient
- **WHEN** the puppeted actor holds an active `DELIVER` stage bound to a co-located recipient and
  holds the objective's item
- **THEN** the vocabulary contains one `explore.deliver` action entry for that recipient, enabled,
  carrying validator-normalized params naming the recipient identity and the item key

#### Scenario: A delivery the actor cannot perform is not invented
- **WHEN** the bound recipient is co-located but the actor no longer holds the objective's item
- **THEN** the vocabulary contains that delivery entry disabled with a stable reason code and a safe
  Traditional Chinese message, and no enabled delivery entry exists

#### Scenario: No delivery entry exists without an active bound stage
- **WHEN** the actor has no active `DELIVER` stage bound to any co-located entity
- **THEN** the vocabulary contains no `explore.deliver` entry

#### Scenario: The conversation-opening code is allowlisted but never emitted
- **WHEN** the vocabulary is emitted for a room holding a scripted host and an `LLMNPC`
- **THEN** it contains the hosts' `explore.talk_scripted` and `explore.talk_freeform` entries and no
  `explore.talk_open` entry, and `explore.talk_open` is a member of `ACTION_CODE_ALLOWLIST` while
  never being emitted by the vocabulary

#### Scenario: The vocabulary exposes exactly two view shapes
- **WHEN** any vocabulary is serialized
- **THEN** every action entry carries exactly `action_id`, `label`, `params`, `freeform`,
  `navigation` (false), `enabled`, and nullable `disabled_reason`, with `action_id` one member of
  `ACTION_CODE_ALLOWLIST`, which contains exactly the exploration verbs listed here plus the in-conversation acknowledgement action `explore.dialogue_complete`: `explore.move`, `explore.look`,
  `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`,
  `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`,
  `explore.possess_release`, and `explore.deliver`; and every navigation entry carries exactly
  `surface` (`"guild"` or `"shop"`), `label`, `navigation` (true), `enabled`, and nullable
  `disabled_reason`, with no `action_id` and no `params`

#### Scenario: The panel's interact group is a label, not an action code
- **WHEN** the exploration panel renders its interact group
- **THEN** the vocabulary contains no `explore.interact` entry, because the group is a label over
  per-target affordances, not an action

#### Scenario: Engagement is monsters-only
- **WHEN** present NPCs, companions, and monsters are enumerated
- **THEN** no NPC or companion `explore.engage` entry exists; one engage entry is emitted once per
  present `Monster`

#### Scenario: A navigation entry is a dock surface-opener
- **WHEN** a guild or shop navigation entry is emitted
- **THEN** it is a dock surface-opener with no dispatcher action code and SHALL never be dispatched
  as a `ui_action`

#### Scenario: Move and look entries track presence
- **WHEN** exits and objects are present in the room
- **THEN** `explore.move` is emitted once per present, traversable Exit with a bounded localized
  label, and `explore.look` is emitted per present non-exit object with `{"target_id": int}`

#### Scenario: Talk entries track hosts, keywords, and NPCs
- **WHEN** a present dialogue host with a resolved `ScriptedDialogue` component and a present
  `LLMNPC` are enumerated
- **THEN** `explore.talk_scripted` is emitted once per disclosed permitted authored topic (hidden topics absent; locked topics expose refusal descriptors only) and
  `explore.talk_freeform` once per present `LLMNPC`

#### Scenario: Party entries follow the existing binding rules
- **WHEN** party and companion bindings are enumerated
- **THEN** `explore.party_invite` follows the existing party-bound and full-party rules and
  `explore.party_leave` follows the companion-bound rule

#### Scenario: Surface navigation names only the exact local host
- **WHEN** guild and shop hosts are considered
- **THEN** guild/shop navigation entries are emitted only for the exact local host, with guild navigation omitted while possessed, and the idle baseline follows the idle-baseline requirement below

#### Scenario: Possess entries mirror the deterministic entry gates
- **WHEN** a bound companion is present
- **THEN** `explore.possess` is emitted once per present bound companion with `params
  {"npc_id": int}`: `enabled` true when `world/rules/possession.py`'s deterministic entry gates
  pass for that companion, otherwise a disabled entry carrying the gate's stable reason code and
  fixed message

#### Scenario: Disabled states are stable and localized
- **WHEN** any entry is emitted in a disabled state
- **THEN** it carries a stable disabled code and a safe Traditional Chinese message

#### Scenario: The vocabulary module is side-effect free
- **WHEN** the vocabulary module emits any entry
- **THEN** nothing in the module mutates traits, knowledge, dialogue, quests, inventory, combat
  sessions, party, or world time

#### Scenario: The possessed actor's authored talk entries are enabled when lawful
- **WHEN** the puppeted actor IS a possessed NPC and talk-entry hosts are present
- **THEN** authored talk entries are enabled when the full actor/owner/host context is lawful, while freeform entries keep the stable possession-refusal code and safe Traditional Chinese message

#### Scenario: Schedule-blocked hosts stay in the vocabulary
- **WHEN** a dialogue host sits inside its schedule gate's blocked window
- **THEN** it SHALL NOT be omitted from the vocabulary; the vocabulary preserves the v1 panel's
  emission semantics

#### Scenario: An unresolvable dialogue table yields no talk entries
- **WHEN** a dialogue host's authored dialogue table cannot be resolved
- **THEN** the vocabulary has no talk entries for it; no validator-normalized params exist for a
  keywordless host, and the version-1 panel's disabled `dialogue_unavailable` affordance is a panel
  serialization degradation, not a vocabulary entry

#### Scenario: The panel serializes host talk entries as one 交談 affordance
- **WHEN** the `exploration` panel serializes a conversable host's talk entries
- **THEN** it renders its server-qualified topic `explore.talk_scripted` descriptors and its `explore.talk_freeform`
  entry as one 交談 `explore.talk_open` affordance derived from the same host, presence, and
  possession gates, while the `context_actions` form keeps consuming the per-keyword and free-form entries unchanged

#### Scenario: Completion is not a topic suggestion
- **WHEN** action registries and exploration targets are projected
- **THEN** explore.dialogue_complete is registered only for exact context-bound acknowledgement payloads and is never emitted as an interact-target action

#### Scenario: The possessed actor's talk entries stay visible disabled
- **WHEN** the possessed actor is offered native freeform talk outside the authorized authored conversation surface
- **THEN** that freeform entry keeps its existing stable visible-disabled possession refusal; lawful authored talk follows the separate enabled-context case

## REMOVED Requirements

### Requirement: Suggestion eligibility derives executable cards
**Reason**: `suggestible_candidates` and `SUGGESTIBLE_ACTION_IDS` existed only to choose AI suggestion cards; both are deleted and the vocabulary itself is unchanged.
**Migration**: None.

### Requirement: The deterministic degradation fallback derives rule cards
**Reason**: `default_cards()` existed only to render a degraded suggestion set; it is deleted with the suggestion surface.
**Migration**: None.
