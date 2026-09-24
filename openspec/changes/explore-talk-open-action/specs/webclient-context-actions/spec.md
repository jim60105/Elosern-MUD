## MODIFIED Requirements

### Requirement: The exploration context form enumerates the complete canonical affordance list
The exploration available form's `affordances` SHALL be a bounded list of exactly the
`AffordanceView` objects produced by the shared vocabulary (`exploration-affordances`) in
vocabulary order: at most `MAX_CONTEXT_AFFORDANCES` (320) entries — a bound derived from the
shared v1 caps (≤ 32 interact targets × ≤ 8 affordances per target, ≤ 16 scripted keywords per
host, ≤ 12 exits, ≤ 32 look objects, ≤ 2 baseline, ≤ 2 navigation), so a legal room can never
truncate the list (asserted by a maximal-fixture test). Each action entry SHALL carry `action_id`
in `ACTION_CODE_ALLOWLIST` (no fabricated or `explore.interact` code), a bounded safe `label`,
the validator-normalized `params` (or the freeform binding shape), exact `freeform` and
`navigation` booleans, exact `enabled`, and `disabled_reason` null or an exact object with stable
code and safe Traditional Chinese message. Each navigation entry SHALL carry `surface`
(`"guild"` or `"shop"`), a bounded safe `label`, `navigation` true, exact `enabled`,
`disabled_reason`, and no `action_id`/`params`, and SHALL never be dispatched as a `ui_action`.
The form SHALL fail closed over the OOB envelope byte limit exactly like the version-1
exploration panel: the entry-count bound is a ceiling, not a guarantee that any content fits, so
a form whose canonical serialization exceeds `MAX_CANONICAL_JSON_BYTES` SHALL be rejected by the
server validator rather than emitted. The client's global envelope gate (list-item ceiling) SHALL
clear the maximal affordance list so a large room's form is never rejected before panel
validation. The production client mirror's action-code enumerations (context-action codes,
exploration action ids) and its affordance `params` validation branches SHALL stay in lockstep
with the server vocabulary. `CONTEXT_ACTIONS_ACTION_CODES` is the full sequence of every code in
`ACTION_CODE_ALLOWLIST` (twelve codes, including `explore.talk_open`, which the vocabulary never
emits but which the shared params gate accepts with exactly `{npc_id}`). `EXPLORATION_ACTION_IDS`
is intentionally the `exploration` panel's target-scoped subset (affordances that require an NPC
target identity) — `explore.move`, `explore.look`, and `explore.wait` are absent because they are
never emitted as per-target affordances, and `explore.talk_scripted` and `explore.talk_freeform`
are absent because the panel folds a host's talk entries into one `explore.talk_open` affordance;
the list is exactly `explore.talk_open`, `explore.party_invite`, `explore.party_leave`,
`explore.engage`, `explore.possess`, `explore.possess_release`, and `explore.deliver`. Every code in each enumeration SHALL have a params branch accepting exactly the
server validator's accepted shape and rejecting everything else; the parity SHALL be pinned by
dependency-free Node test fixtures carrying the server's authoritative code lists and accept/reject
params vectors.

#### Scenario: The context form mirrors the vocabulary exactly
- **WHEN** the exploration form is rendered for a fixture room
- **THEN** its `affordances` equals the vocabulary's `AffordanceView` list for that room (same
  entries, order, ids, labels, params, flags, enabled states, and disabled reasons), and both the
  server validator and the client mirror accept it

#### Scenario: A maximal legal room serializes untruncated
- **WHEN** a fixture room reaches the shared caps (32 targets with full keyword lists, 12 exits,
  32 objects, baseline, navigation)
- **THEN** the exploration form contains every vocabulary entry, passes the server validator, and
  is accepted by the client mirror without truncation

#### Scenario: The client mirror accepts the possession codes
- **WHEN** a version-5 exploration fixture carries an `explore.possess` entry with canonical
  params and an `explore.possess_release` entry with canonical params (both codes carry exactly
  the server validator's accepted `npc_id` shape)
- **THEN** the client mirror's enumeration and params validation accept both, and reject mutated
  params (missing or extra keys, wrong kinds, out-of-range ids) exactly as the server validator
  does

#### Scenario: The client mirror accepts the conversation-opening code
- **WHEN** the client mirror's params gate validates `explore.talk_open` with `{npc_id: 7}`, and
  again with an added `keyword_id`, a missing `npc_id`, or a zero `npc_id`
- **THEN** the first is accepted and the others are rejected exactly as the server validator does,
  and `CONTEXT_ACTIONS_ACTION_CODES` equals the server's twelve-code allowlist
