## Purpose

The canonical, shared, read-only affordance vocabulary for exploration-mode surfaces — the
discriminated `AffordanceView` contract (action vs navigation), the eight emitted action codes
plus the guild/shop surfaces, validator-normalized params, the freeform binding-only exception,
the idle baseline, the suggestion-eligibility layer, and the deterministic `default_cards()`
degradation derivation. This capability owns the vocabulary; `webclient-context-actions` and
(later) the suggestions feature consume it.

## ADDED Requirements

### Requirement: The canonical affordance vocabulary is shared and read-only
A shared module (`web/webclient/presentation/affordances.py`) SHALL own the canonical
affordance rules for a puppeted player in exploration mode, consumed by both the `exploration`
panel presenter and the `context_actions` exploration presenter. Every emitted entry SHALL be an
`AffordanceView` that is exactly one of two discriminated shapes:
- an **action entry** SHALL carry exactly `action_id`, `label`, `params`, `freeform`, `navigation`
  (false), `enabled`, and nullable `disabled_reason`; `action_id` SHALL be one member of
  `ACTION_CODE_ALLOWLIST`, which SHALL contain exactly `explore.move`, `explore.look`,
  `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`,
  `explore.engage`, and `explore.wait` — there SHALL be no `explore.interact` entry (the
  exploration panel's interact group is a label over per-target affordances, not an action); there
  SHALL be no NPC or companion `explore.engage` (engagement is monsters-only);
- a **navigation entry** SHALL carry exactly `surface` (`"guild"` or `"shop"`), `label`,
  `navigation` (true), `enabled`, and nullable `disabled_reason`, and SHALL carry no
  `action_id` and no `params` — a navigation entry is a dock surface-opener with no dispatcher
  action code and SHALL never be dispatched as a `ui_action`.

`explore.move` SHALL be emitted once per present, traversable Exit with a bounded localized label;
`explore.look` SHALL be emitted per present non-exit object with `{"target_id": int}`;
`explore.talk_scripted` SHALL be emitted once per authored keyword of a present dialogue host
(resolved `OnboardingGuide` or `ScriptedDialogue` component), `explore.talk_freeform` SHALL be
emitted once per present `LLMNPC`, `explore.party_invite` SHALL follow the existing party-bound
and full-party rules and `explore.party_leave` the companion-bound rule, `explore.engage` SHALL be
emitted once per present `Monster` (a living monster yields `enabled` true; a dead monster yields
a disabled entry with a stable `target_dead` reason — matching the v1 panel), guild/shop
navigation entries SHALL be emitted only for the exact local host, and the idle baseline SHALL
follow the idle-baseline requirement below. A schedule-blocked dialogue host SHALL NOT be omitted
from the vocabulary — the vocabulary preserves the v1 panel's emission semantics; schedule-gate
exclusion applies only to suggestion eligibility (suggestion-eligibility requirement below).
Every entry with a disabled state SHALL carry a stable disabled code and safe Traditional Chinese
message. Nothing in this module SHALL mutate traits, knowledge, dialogue, quests, inventory,
combat sessions, party, or world time.

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
omitted. A move entry's `current_node` SHALL be produced by the shared pure node-ID encoder
(`web/webclient/actions/node_ids.py::node_id_for_location`) that the move adapter's
`stale_location` check uses, so the value is byte-identical across GridRoom, TerrainRoom, and
ordinary-room encodings.

#### Scenario: Every emitted entry executes against its real adapter
- **WHEN** a unit or integration test takes the vocabulary emitted for a fixture room and
  dispatches each suggestible action entry through the production dispatcher
- **THEN** no `malformed_payload` rejection occurs, and the move entry passes the adapter's
  `stale_location` comparison unchanged

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
requirement). This layer is the single source of "is this card runnable right now" for the
deterministic fallback and, later, for the AI proposal ladder; the vocabulary itself SHALL remain
unchanged by this filtering.

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