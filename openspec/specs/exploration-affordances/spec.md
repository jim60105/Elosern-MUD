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
affordance rules for a puppeted player in exploration mode, consumed by both the `exploration`
panel presenter and the `context_actions` exploration presenter. Every emitted entry SHALL be an
`AffordanceView` that is exactly one of two discriminated shapes:
- an **action entry** SHALL carry exactly `action_id`, `label`, `params`, `freeform`, `navigation`
  (false), `enabled`, and nullable `disabled_reason`; `action_id` SHALL be one member of
  `ACTION_CODE_ALLOWLIST`, which SHALL contain exactly `explore.move`, `explore.look`,
  `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`,
  `explore.engage`, `explore.wait`, `explore.possess`, and `explore.possess_release` — there SHALL
  be no `explore.interact` entry (the exploration panel's interact group is a label over
  per-target affordances, not an action); there
  SHALL be no NPC or companion `explore.engage` (engagement is monsters-only);
- a **navigation entry** SHALL carry exactly `surface` (`"guild"` or `"shop"`), `label`,
  `navigation` (true), `enabled`, and nullable `disabled_reason`, and SHALL carry no
  `action_id` and no `params` — a navigation entry is a dock surface-opener with no dispatcher
  action code and SHALL never be dispatched as a `ui_action`.

`explore.move` SHALL be emitted once per present, traversable Exit with a bounded localized label;
`explore.look` SHALL be emitted per present non-exit object with `{"target_id": int}`;
`explore.talk_scripted` SHALL be emitted once per authored keyword of a present dialogue host
(resolved `ScriptedDialogue` component), `explore.talk_freeform` SHALL be
emitted once per present `LLMNPC`, `explore.party_invite` SHALL follow the existing party-bound
and full-party rules and `explore.party_leave` the companion-bound rule, `explore.engage` SHALL be
emitted once per present `Monster` (a living monster yields `enabled` true; a dead monster yields
a disabled entry with a stable `target_dead` reason — matching the v1 panel), guild/shop
navigation entries SHALL be emitted only for the exact local host, and the idle baseline SHALL
follow the idle-baseline requirement below. `explore.possess` SHALL be emitted once per present
bound companion with `params {"npc_id": int}`: `enabled` true when
`world/rules/possession.py`'s deterministic entry gates pass for that companion, otherwise a
disabled entry carrying the gate's stable reason code and fixed message. `explore.possess_release`
SHALL be emitted exactly once, only while the puppeted actor is a possessed NPC. While the
puppeted actor IS a possessed NPC, the vocabulary SHALL keep its refusal surface honest: talk
entries, `explore.engage`, and shop navigation entries SHALL be emitted disabled with stable
possession-refusal codes and safe Traditional Chinese messages — v1 possession refusals are
visible disabled states, not hidden entries. A schedule-blocked dialogue host SHALL NOT be omitted
from the vocabulary — the vocabulary preserves the v1 panel's emission semantics; schedule-gate
exclusion applies only to suggestion eligibility (suggestion-eligibility requirement below).
A dialogue host whose authored dialogue table cannot be resolved SHALL have no talk entries in
the vocabulary — no validator-normalized params exist for a keywordless host; the version-1
panel's disabled `dialogue_unavailable` affordance is a panel serialization degradation, not a
vocabulary entry. Every entry with a disabled state SHALL carry a stable disabled code and safe
Traditional Chinese message. Nothing in this module SHALL mutate traits, knowledge, dialogue,
quests, inventory, combat sessions, party, or world time.

#### Scenario: The exploration panel and the context form share one vocabulary
- **WHEN** the same room is presented to the same puppeted actor through both the `exploration`
  panel and the `context_actions` exploration form
- **THEN** both surfaces enumerate the same eligible targets and actions with identical ids,
  labels, gates, and disabled states, and both serializations are unchanged before and after a
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

### Requirement: Affordance params are validator-normalized
Every action entry's `params` SHALL be the normalized output of that action's registered
validator in `web/webclient/actions/exploration_actions.py` applied to a candid payload the
builder constructs (exact shapes: `explore.move` `{"exit_ref", "current_node"}`, `explore.look`
`{"target_id"}` or `{"room": true}`, `explore.talk_scripted` `{"npc_id", "keyword_id"}`,
`explore.party_invite` `{"npc_id", "message"}` (message empty by construction),
`explore.party_leave` `{"npc_id"}`, `explore.engage` `{"monster_id"}`, `explore.wait`
`{"daypart": "noon"}`, `explore.possess` `{"npc_id"}`, and `explore.possess_release`
`{"npc_id"}`) — so the dispatched payload is byte-for-byte the payload the dispatcher
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

### Requirement: The idle baseline guarantees at least one executable entry
In exploration mode with a puppeted player inside a location, the vocabulary SHALL always emit an
`explore.look` action entry with `params {"room": true}`. The vocabulary SHALL additionally emit
an `explore.wait` action entry with `params {"daypart": "noon"}` only when the wait adapter's
`unsafe_rejection(actor)` is absent (a room with a living monster SHALL NOT offer wait). These
idle-baseline entries are members of the affordance vocabulary only — they SHALL NOT appear in
the version-1 `exploration` panel payload (where look is a section and wait has no panel
affordance); they SHALL appear in the `context_actions` exploration form and in `default_cards()`.

#### Scenario: An empty room still yields a nonempty executable baseline
- **WHEN** a room has no exits, no NPCs, no monsters, and no objects
- **THEN** the vocabulary emits the `explore.look` room entry (and, in a safe room, the
  `explore.wait` entry), and `default_cards()` derives a nonempty suggestion set from them

#### Scenario: An unsafe room never offers wait
- **WHEN** a living Monster is present but no combat session is active
- **THEN** the vocabulary contains no `explore.wait` entry and the room-look entry remains
  eligible

### Requirement: Suggestion eligibility derives executable cards
`suggestible_candidates(affordances)` SHALL return exactly the action entries that are
executable *suggestions*: `enabled` true, `action_id` in `SUGGESTIBLE_ACTION_IDS`
(`explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`,
`explore.engage`, `explore.wait`), not a navigation entry, not a party action, not blocked by the
talk schedule gate (`interaction_reason(npc, "talk")` — a blocked host's talk entries are
excluded), and not an unsafe-room wait (wait entries only exist when safe, per the idle-baseline
requirement). The schedule and safety gates require the live actor: a call without the actor
SHALL exclude every talk entry rather than claim executability for an unverifiable card (the
caller that needs talk suggestions passes the actor). This layer is the single source of "is this
card runnable right now" for the deterministic fallback and, later, for the AI proposal ladder;
the vocabulary itself SHALL remain unchanged by this filtering.

#### Scenario: A schedule-blocked host is suggestible-excluded but vocabulary-present
- **WHEN** a present dialogue host is inside its schedule gate's blocked window
- **THEN** the vocabulary still contains its talk entries (v1 semantics), while
  `suggestible_candidates()` excludes them

#### Scenario: Party and navigation actions are never suggestions
- **WHEN** the vocabulary contains party entries and navigation entries
- **THEN** `suggestible_candidates()` contains none of them

### Requirement: The deterministic degradation fallback derives rule cards
`default_cards(affordances, *, objective_npc_ids=frozenset())` SHALL derive the deterministic
fallback suggestion list from `suggestible_candidates(affordances)`: it SHALL rank
objective-relevant entries first (an entry whose params reference a present NPC id in
`objective_npc_ids` precedes all others), SHALL then prefer talk and engage entries over the idle
baseline, SHALL preserve vocabulary order within a rank, SHALL contain at most 5 cards, SHALL
contain at least 1 card in v1 exploration (the room-look baseline is always suggestible), and
SHALL return only cards that are executable suggestion cards — same `action_id`, same
validator-normalized `params`, same label as the vocabulary — so the result is always a strict
subset of the current affordance union. The function SHALL be pure: it never mutates state and
only reads what the caller passes.

#### Scenario: Objective-relevant actions rank first
- **WHEN** `objective_npc_ids` names a present NPC that supports `explore.talk_scripted`
- **THEN** that scripted-talk entry precedes all move, baseline, and non-objective talk entries in
  the derivation, and every navigation, party, and disabled entry is absent

#### Scenario: The subset contract holds on every fixture
- **WHEN** `default_cards()` is evaluated across the per-scenario fixtures (empty room, exits,
  schedule-blocked NPC, monster present, quest objective, multi-LLM-NPC)
- **THEN** the result is at least 1 and at most 5 cards, each card exactly matches one current
  affordance union entry (id, params, label), and order complies with the ranking rule


### Requirement: Navigation entries render off-anchor service hosts honestly
A `guild` or `shop` navigation entry for a co-located host whose corresponding service component
is verdicted `off_anchor` or `malformed_binding` by `world/rules/service_gate.py` SHALL be emitted
`enabled: false` with the gate's fixed registry message as its `disabled_reason.message` — the
entry keeps the unchanged navigation shape (no `action_id`, no `params`). A `remote` host changes
nothing (absence is still the norm), and an `allowed` host behaves exactly as before. The
anchor-room side of the contract is absence: a room containing the anchor but no host SHALL emit
no navigation entry for that service (pinned test; no ghost storefront).

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
