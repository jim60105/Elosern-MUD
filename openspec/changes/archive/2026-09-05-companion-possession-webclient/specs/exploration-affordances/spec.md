# Delta spec: exploration-affordances (companion-possession-webclient)

The allowlist is an exact enumeration, so the vocabulary and params requirements are MODIFIED
(full reproductions with the two possession codes woven in). Suggestion eligibility needs no
delta: `SUGGESTIBLE_ACTION_IDS` is itself an exact enumeration that the possession codes do not
join, so party-style exclusion is automatic.

## MODIFIED Requirements

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
  per-target affordances, not an action); there SHALL be no NPC or companion `explore.engage`
  (engagement is monsters-only);
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
