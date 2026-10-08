## Purpose

The canonical, shared, read-only affordance vocabulary for exploration-mode surfaces — the
discriminated `AffordanceView` contract (action vs navigation), the eight emitted action codes
plus the guild/shop surfaces, validator-normalized params, the freeform binding-only exception,
the idle baseline, the suggestion-eligibility layer, and the deterministic `default_cards()`
degradation derivation. This capability owns the vocabulary; `webclient-context-actions` and
(later) the suggestions feature consume it.

## Requirements

### Requirement: The canonical affordance vocabulary is shared and read-only
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
- **WHEN** a guild or shop host is present
- **THEN** the vocabulary contains a navigation entry with `surface` `"guild"`/`"shop"`,
  `navigation` true, and no `action_id` and no `params`, and no `ui_action` registry lookup
  exists for it

#### Scenario: Possess entries mirror the deterministic gates
- **WHEN** a bound companion stands beside the player while a combat session is active
- **THEN** the vocabulary carries that companion's `explore.possess` entry disabled with the
  combat gate's stable code, and the same entry is enabled once combat ends

#### Scenario: Release is offered exactly once, only while possessing
- **WHEN** the actor possesses a companion and the vocabulary is emitted
- **THEN** exactly one `explore.possess_release` entry is present, and no unpossessed-emission
  vocabulary contains it

#### Scenario: The possessed actor's refusal surface stays visible
- **WHEN** the puppeted actor is a possessed NPC and a monster and a shop host are present
- **THEN** the engage and shop entries render disabled with stable possession-refusal codes and
  fixed messages rather than being omitted

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
  `explore.talk_open` entry, `explore.talk_open` is a member of `ACTION_CODE_ALLOWLIST`, and it is
  absent from `SUGGESTIBLE_ACTION_IDS`

#### Scenario: The vocabulary exposes exactly two view shapes
- **WHEN** any vocabulary is serialized
- **THEN** every action entry carries exactly `action_id`, `label`, `params`, `freeform`,
  `navigation` (false), `enabled`, and nullable `disabled_reason`, with `action_id` one member of
  `ACTION_CODE_ALLOWLIST`, which contains exactly `explore.move`, `explore.look`,
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
- **THEN** `explore.talk_scripted` is emitted once per authored keyword of the dialogue host and
  `explore.talk_freeform` once per present `LLMNPC`

#### Scenario: Party entries follow the existing binding rules
- **WHEN** party and companion bindings are enumerated
- **THEN** `explore.party_invite` follows the existing party-bound and full-party rules and
  `explore.party_leave` follows the companion-bound rule

#### Scenario: Surface navigation names only the exact local host
- **WHEN** guild and shop hosts are considered
- **THEN** guild/shop navigation entries are emitted only for the exact local host, and the idle
  baseline follows the idle-baseline requirement below

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

#### Scenario: The possessed actor's talk entries stay visible disabled
- **WHEN** the puppeted actor IS a possessed NPC and talk-entry hosts are present
- **THEN** the talk entries are emitted disabled with stable possession-refusal codes and safe
  Traditional Chinese messages — v1 possession refusals are visible disabled states, not hidden
  entries

#### Scenario: Schedule-blocked hosts stay in the vocabulary
- **WHEN** a dialogue host sits inside its schedule gate's blocked window
- **THEN** it SHALL NOT be omitted from the vocabulary — the vocabulary preserves the v1 panel's
  emission semantics, and schedule-gate exclusion applies only to suggestion eligibility (the
  suggestion-eligibility requirement below)

#### Scenario: An unresolvable dialogue table yields no talk entries
- **WHEN** a dialogue host's authored dialogue table cannot be resolved
- **THEN** the vocabulary has no talk entries for it — no validator-normalized params exist for a
  keywordless host, and the version-1 panel's disabled `dialogue_unavailable` affordance is a panel
  serialization degradation, not a vocabulary entry

#### Scenario: The panel serializes host talk entries as one 交談 affordance
- **WHEN** the `exploration` panel serializes a conversable host's talk entries
- **THEN** it renders its per-keyword `explore.talk_scripted` entries and its `explore.talk_freeform`
  entry as one 交談 `explore.talk_open` affordance derived from the same host, presence, and
  possession gates, while the `context_actions` form, suggestion eligibility, and the deterministic
  fallback keep consuming the per-keyword and free-form entries unchanged
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
  `{"target_id"}` or `{"room": true}`, `explore.talk_scripted` `{"npc_id", "keyword_id"}`,
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

### Requirement: The idle baseline guarantees at least one executable entry
In exploration mode with a puppeted player inside a location, the vocabulary SHALL always emit an
`explore.look` action entry with `params {"room": true}`. The vocabulary SHALL additionally emit
an `explore.wait` action entry with `params {"daypart": "noon"}` only when the wait adapter's
`unsafe_rejection(actor)` is absent.

#### Scenario: An empty room still yields a nonempty executable baseline
- **WHEN** a room has no exits, no NPCs, no monsters, and no objects
- **THEN** the vocabulary emits the `explore.look` room entry (and, in a safe room, the
  `explore.wait` entry), and `default_cards()` derives a nonempty suggestion set from them

#### Scenario: An unsafe room never offers wait
- **WHEN** a living Monster is present but no combat session is active
- **THEN** the vocabulary contains no `explore.wait` entry and the room-look entry remains
  eligible

#### Scenario: Baseline entries stay out of the v1 panel payload
- **WHEN** the version-1 `exploration` panel payload is serialized
- **THEN** these idle-baseline entries are members of the affordance vocabulary only and SHALL NOT
  appear in it — look is a section there and wait has no panel affordance

#### Scenario: Baseline entries reach the context form and fallback
- **WHEN** the `context_actions` exploration form and `default_cards()` are rendered
- **THEN** the idle-baseline entries SHALL appear in both

### Requirement: Suggestion eligibility derives executable cards
`suggestible_candidates(affordances)` SHALL return exactly the action entries that are
executable *suggestions*: `enabled` true, `action_id` in `SUGGESTIBLE_ACTION_IDS`, not a
navigation entry, not a party action, not blocked by the talk schedule gate, and not an
unsafe-room wait. This layer is the single source of "is this card runnable right now" for the
deterministic fallback and, later, for the AI proposal ladder; the vocabulary itself SHALL
remain unchanged by this filtering.

#### Scenario: A schedule-blocked host is suggestible-excluded but vocabulary-present
- **WHEN** a present dialogue host is inside its schedule gate's blocked window
- **THEN** the vocabulary still contains its talk entries (v1 semantics), while
  `suggestible_candidates()` excludes them

#### Scenario: Party and navigation actions are never suggestions
- **WHEN** the vocabulary contains party entries and navigation entries
- **THEN** `suggestible_candidates()` contains none of them

#### Scenario: The suggestible code set is closed
- **WHEN** suggestibility is judged by action code
- **THEN** `SUGGESTIBLE_ACTION_IDS` is exactly `explore.move`, `explore.look`,
  `explore.talk_scripted`, `explore.talk_freeform`, `explore.engage`, `explore.wait`

#### Scenario: The talk schedule gate excludes blocked hosts
- **WHEN** the talk schedule gate (`interaction_reason(npc, "talk")`) is evaluated
- **THEN** a blocked host's talk entries are excluded, and an unsafe-room wait is excluded too
  (wait entries only exist when safe, per the idle-baseline requirement)

#### Scenario: Without the live actor, talk entries are excluded
- **WHEN** `suggestible_candidates()` is called without the actor
- **THEN** it SHALL exclude every talk entry rather than claim executability for an unverifiable
  card — the schedule and safety gates require the live actor, and the caller that needs talk
  suggestions passes the actor

### Requirement: The deterministic degradation fallback derives rule cards
`default_cards(affordances, *, objective_npc_ids=frozenset())` SHALL derive the deterministic
fallback suggestion list from `suggestible_candidates(affordances)`: it SHALL rank
objective-relevant entries first, SHALL then prefer talk and engage entries over the idle
baseline, SHALL preserve vocabulary order within a rank, and SHALL return only executable
suggestion cards, so the result is always a strict subset of the current affordance union.

#### Scenario: Objective-relevant actions rank first
- **WHEN** `objective_npc_ids` names a present NPC that supports `explore.talk_scripted`
- **THEN** that scripted-talk entry precedes all move, baseline, and non-objective talk entries in
  the derivation, and every navigation, party, and disabled entry is absent

#### Scenario: The subset contract holds on every fixture
- **WHEN** `default_cards()` is evaluated across the per-scenario fixtures (empty room, exits,
  schedule-blocked NPC, monster present, quest objective, multi-LLM-NPC)
- **THEN** the result is at least 1 and at most 5 cards, each card exactly matches one current
  affordance union entry (id, params, label), and order complies with the ranking rule

#### Scenario: The objective rank keys on params-referenced NPC ids
- **WHEN** the objective ranking is applied
- **THEN** an entry whose params reference a present NPC id in `objective_npc_ids` precedes all
  others

#### Scenario: Returned cards are vocabulary-identical suggestion cards
- **WHEN** `default_cards()` returns any card
- **THEN** it is an executable suggestion card with the same `action_id`, same
  validator-normalized `params`, and same label as the vocabulary entry it came from

#### Scenario: The card count bounds are fixed
- **WHEN** `default_cards()` returns for v1 exploration
- **THEN** it contains at most 5 cards and at least 1 card — the room-look baseline is always
  suggestible

#### Scenario: The derivation is pure
- **WHEN** `default_cards()` is called
- **THEN** the function never mutates state and only reads what the caller passes


### Requirement: Navigation entries render off-anchor service hosts honestly
A `guild` or `shop` navigation entry for a co-located host whose corresponding service component
is verdicted `off_anchor` or `malformed_binding` by `world/rules/service_gate.py` SHALL be emitted
`enabled: false` with the gate's fixed registry message as its `disabled_reason.message` — the
entry keeps the unchanged navigation shape (no `action_id`, no `params`).

#### Scenario: The traveling merchant shows disabled beside the player
- **WHEN** the place-bound merchant stands with the party in the town square and the snapshot
  presents exploration affordances
- **THEN** the shop navigation entry appears disabled carrying the gate's fixed message, and the
  Vue and text presenters render the same disabled entry from the shared emitter

#### Scenario: The darkened anchor room shows nothing
- **WHEN** the merchant has left the general store with the party and the player looks at the
  empty store through another character
- **THEN** the store's affordances carry no shop navigation entry at all

#### Scenario: At-anchor emission is untouched
- **WHEN** the merchant is at his anchor room beside the player
- **THEN** the shop navigation entry is enabled exactly as before this requirement

#### Scenario: A remote host changes nothing
- **WHEN** the gate verdicts a co-located host `remote`
- **THEN** emission is unchanged — absence is still the norm

#### Scenario: An allowed host is unchanged
- **WHEN** the gate verdicts the host `allowed`
- **THEN** the navigation entry behaves exactly as before this requirement

#### Scenario: The anchor room without a host emits nothing
- **WHEN** a room contains the anchor but no host
- **THEN** it SHALL emit no navigation entry for that service (pinned test; no ghost storefront)
