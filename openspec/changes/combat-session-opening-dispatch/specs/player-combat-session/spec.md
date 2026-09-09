## ADDED Requirements

### Requirement: One submission inside an active session is one ordinary round, by default and structurally
`world/rules/combat_session.py`'s shared submission body SHALL accept keyword-only
`opening: Literal["round", "overwhelm"] = "round"` and `first_actor: str | None = None`, and SHALL
run one `combat.run_round()` whenever `opening` is `"round"`. It SHALL NOT consult
`classify_overwhelm()` to choose between an ordinary round and compression; the choice SHALL be the
caller's, expressed through `opening`. `submit_player_action()` and `submit_player_item_use()` SHALL
NOT pass `opening` and SHALL NOT call `classify_overwhelm()` for dispatch, so every submission made
inside an already-active session resolves exactly one round regardless of the power verdict. The
session's `simulated` and companion `nonlethal_keys` policy, the item journal sink, and the
notification sink SHALL be forwarded identically for both `opening` values.

#### Scenario: An overwhelming verdict no longer compresses an in-session submission
- **WHEN** the player submits a preflight-valid skill in a session for which `classify_overwhelm()`
  returns the player's team
- **THEN** exactly one ordinary round resolves, `rounds_elapsed` increases by one, and
  `resolve_overwhelm()` is not called

#### Scenario: An item can never compress
- **WHEN** the player submits a preflight-valid item use in a session for which
  `classify_overwhelm()` returns the player's team
- **THEN** exactly one ordinary round resolves and `resolve_overwhelm()` is not called

#### Scenario: The public in-session entries never opt in
- **WHEN** `submit_player_action()`'s and `submit_player_item_use()`'s implementations are inspected
- **THEN** neither passes `opening` to the shared submission body and neither calls
  `classify_overwhelm()` to decide dispatch

#### Scenario: Round policy forwarding is identical for both openings
- **WHEN** the shared submission body runs with `opening="round"` and again with
  `opening="overwhelm"` for a session carrying `simulated` and non-empty `nonlethal_keys`
- **THEN** both forward the same `simulated`, `nonlethal_keys`, journal sink, and notification sink
  values into resolution

### Requirement: engage_group opens one session against several co-located hostile targets
`world/rules/combat_session.py` SHALL provide `engage_group(actor, targets)`, applying every
validation, companion collection, record construction, battlefield reconstruction, persistence, skip
safety registration, and dialogue-session clearing that single-target engagement performs, with
`enemy_ids` holding one dbref per supplied target in deterministic order. `engage(actor, target)`
SHALL retain its signature and semantics and SHALL delegate to `engage_group(actor, [target])`, so
its existing call sites are unchanged. `engage_group()` SHALL reject the whole request — persisting
no session — when the actor is not a `PlayerCharacter`, already has an active session, or when any
supplied target is not a living hostile `Monster` in the actor's room.

#### Scenario: A two-enemy session reconstructs, persists, resolves, and settles
- **WHEN** `engage_group()` is called with two living hostile monsters in the actor's room, and the
  player then submits one preflight-valid action
- **THEN** the persisted `enemy_ids` contains both dbrefs, the reconstructed battlefield places both
  on the opposing team, the round resolves, and terminal settlement behaves as it does for a
  single-enemy session

#### Scenario: engage is unchanged for its callers
- **WHEN** `engage(actor, target)` is called
- **THEN** it returns the same shape it returned before this change, persists an `enemy_ids` of
  exactly one dbref, and its call sites require no edit

#### Scenario: One invalid target rejects the whole group
- **WHEN** `engage_group()` is called with one valid monster and one target that is dead, in another
  room, or not a `Monster`
- **THEN** the request is rejected, no session is persisted, no battlefield is registered, and no
  world time changes

### Requirement: submit_opening_action is the sole compression dispatcher and always grants the player first strike
`world/rules/combat_session.py` SHALL provide `submit_opening_action(actor, skill_key, targets, scale)`
as the only production caller that may request compression. It SHALL select
`opening="overwhelm"` if and only if `classify_overwhelm(battlefield)` returns the actor's team
**and** `overwhelm.commanded_damage_reaches_enemy()` reports that the submitted skill damages a
member of the opposing team; in every other case it SHALL select `opening="round"`. It SHALL pass
`first_actor` equal to the actor's roster key for both selections, so the opening action resolves
before any other combatant acts. It SHALL accept skills only; no item request SHALL reach it.

`submit_opening_action()` SHALL accept only a concrete list of participant objects and SHALL reject
an approved AREA shorthand (`all-enemies`, `all-allies`, `all`) before initiative, even though
`submit_player_action()` accepts one. This is a correctness requirement, not a convenience:
`commanded_damage_reaches_enemy()` reads concrete roster keys, so a shorthand reaching it would fail
to intersect the enemy team and return `False`, silently selecting `opening="round"` and disabling
one-shot settlement with no diagnostic. Rejecting the shorthand makes that failure unreachable
instead of invisible. It SHALL likewise reject a target that is not a member of the reconstructed
battlefield's roster, matching `submit_player_action()`'s existing not-present rejection.

#### Scenario: An AREA shorthand is rejected before initiative
- **WHEN** `submit_opening_action()` is called with `"all-enemies"` instead of a concrete list
- **THEN** it rejects before initiative, no round runs, no resource is spent, and the rejection is a
  diagnostic rather than a silent fall back to `opening="round"`

#### Scenario: An off-roster target is rejected before initiative
- **WHEN** `submit_opening_action()` is called with a participant absent from the reconstructed
  battlefield's roster
- **THEN** it rejects before initiative, exactly as `submit_player_action()` does for the same input

#### Scenario: A damaging skill under a player-overwhelming verdict compresses
- **WHEN** `submit_opening_action()` runs for a skill carrying a `DamageEffect` aimed at an enemy in
  a session `classify_overwhelm()` decides for the player's team
- **THEN** it selects `opening="overwhelm"` and the encounter resolves through `resolve_overwhelm()`

#### Scenario: A non-damaging skill under the same verdict does not compress
- **WHEN** `submit_opening_action()` runs for a buff, heal, cleanse, debuff-only, or sexual skill in
  a session `classify_overwhelm()` decides for the player's team
- **THEN** it selects `opening="round"` and exactly one ordinary round resolves

#### Scenario: A damaging skill under a contested or foe-overwhelming verdict does not compress
- **WHEN** `submit_opening_action()` runs for a damaging skill in a session whose
  `classify_overwhelm()` returns `None` or the foe team
- **THEN** it selects `opening="round"`, exactly one ordinary round resolves, and the player retains
  full skill, item, and flee choice for the next round

#### Scenario: The player acts first in the opening round under both selections
- **WHEN** `submit_opening_action()` runs under a fixed seed for a battlefield in which ordinary
  initiative would not place the player first, once with a damaging skill and a player-overwhelming
  verdict and once with a non-damaging skill
- **THEN** in both cases the player's action resolves before any other combatant's in the opening
  round

## MODIFIED Requirements

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
At engagement the session SHALL record overwhelm classification but SHALL run no action before player input. Compression SHALL be reachable only through `submit_opening_action()`, and only when its two-part condition holds: `classify_overwhelm()` decides for the player's team **and** the submitted skill damages a member of the opposing team. A submission made inside an already-active session SHALL NEVER compress, whatever the verdict and whatever was submitted. When compression is dispatched, the selected request SHALL be used for the first simulated player turn; subsequent compressed player turns SHALL use deterministic `basic_attack` against the lowest-HP living enemy. Every turn SHALL remain a member of the closed deterministic request union and SHALL emit compressed EventLogs; no path SHALL directly assign HP, consume inventory outside the item resolver, or bypass quest planners. The dispatcher SHALL pass the selected action's actor key, `action_kind` (`skill`), and `action_key` to the resolver so the compressed log emits exactly one matching first-round `commanded_action` entry. This identity plumbing SHALL affect only log identity, never round sequence, combat math, or settlement. A foe-overwhelming verdict SHALL remain informational and play one ordinary round per submission, preserving full skill, flee, and item choice. Undecided encounters SHALL pause for player input between ordinary rounds.

#### Scenario: An opening damaging skill under a player-overwhelming verdict resolves compressed
- **WHEN** compression is dispatched through `submit_opening_action()` for a damaging skill and a player-direction verdict
- **THEN** only then does compression resolve through deterministic resolvers, emit ordinary defeat and quest effects, and settle its rounds

#### Scenario: An in-session submission never compresses
- **WHEN** the player submits a valid skill or a valid healing potion inside an already-active session whose verdict decides for the player's team
- **THEN** exactly one ordinary round resolves, `resolve_overwhelm()` is not called, and the player chooses again next round

#### Scenario: Engage alone never runs an overwhelming round
- **WHEN** an overwhelming target is engaged but the player has not submitted an action
- **THEN** neither team acts, no EventLog is emitted, and world time and round count remain unchanged

#### Scenario: Compressed log marks the selected action kind and key
- **WHEN** an overwhelming encounter compresses after a valid opening skill
- **THEN** compressed EventLogs contain exactly one first-round `commanded_action` matching the player's key, the `skill` action kind, and the action key without changing rounds, HP mutations, or settlement

#### Scenario: Foe-overwhelming encounter preserves item choice
- **WHEN** the foe team is overwhelming and the player submits a preflight-valid skill or item
- **THEN** exactly one ordinary round resolves, the player may choose a different skill, item, or flee next round, and compression is never invoked

#### Scenario: Non-overwhelming encounter waits for another command
- **WHEN** one round ends with both teams active and no player-direction overwhelm verdict
- **THEN** the session persists and no additional round runs before the player's next action

### Requirement: Overwhelm compression is player-direction only
`submit_opening_action()` SHALL invoke the overwhelm resolver only when `classify_overwhelm` returns the player's team and the submitted skill damages a member of the opposing team; any other verdict (contested or foe-overwhelming), and any non-damaging or non-enemy-directed skill, SHALL NOT trigger compression. No other production call site SHALL invoke the resolver.

#### Scenario: Foe-overwhelming verdict never dispatches the resolver
- **WHEN** the player submits a preflight-valid action in a session classified as foe-overwhelming
- **THEN** the session runs one ordinary round and never calls the overwhelm resolver, for that round or any later round while the verdict holds

#### Scenario: A player-direction verdict alone is not enough
- **WHEN** `submit_opening_action()` runs for a non-damaging skill in a session classified for the player's team
- **THEN** one ordinary round resolves and the overwhelm resolver is not called

#### Scenario: The resolver has exactly one production call site
- **WHEN** every production call site of `resolve_overwhelm()` is inspected
- **THEN** the only one is inside `submit_opening_action()`'s dispatch

### Requirement: A round and its settlement form one atomic persistence unit

The shared submission body SHALL persist the round's action effects (HP/resources/knockouts/quest effects), the updated session metadata (round count, fled/knockout sets), and any terminal settlement (exam outcome, clock advance, session clearing) as a single durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state. Upkeep-settled effects (damaging-tick HP, defeat entries, and quest effects staged by the upkeep settlement) SHALL commit inside the same unit: the body SHALL forward the session's `simulated` and companion `nonlethal_keys` policy into resolution for both the `opening="round"` and the `opening="overwhelm"` path, and an upkeep settlement failure SHALL roll back the whole round. On a hostile-defeat terminal outcome, the complete defeat aftermath (violator departure, weak buff grant, and the adult phases contributed by later changes) SHALL commit in that one transaction together with the `settled_tick` marker and the session-record clearing; the physical departure deletions ride `transaction.on_commit`, so an outer round transaction's rollback discards them too.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

### Requirement: Player combat submission accepts one explicit target value
`submit_player_action(actor, skill_key, targets_or_shorthand)` SHALL accept only a concrete list of live participant objects or one of `all-enemies`, `all-allies`, and `all`. It SHALL reject any other scalar, a duplicate explicit participant, or a participant outside the current reconstructed session before initiative. Player-facing NONE and SELF SHALL require an empty list; the facade SHALL bind that empty SELF input to the actor and leave NONE empty. SINGLE SHALL receive exactly one explicit participant, and AREA SHALL receive a nonempty explicit list or one approved shorthand. The facade SHALL retain battlefield reconstruction, shared preview, `ActionResolver.preflight()`, initiative, session persistence, terminal settlement, and recovery ownership. It SHALL NOT own compression dispatch, which belongs to `submit_opening_action()` alone. No single-object compatibility overload SHALL exist.

#### Scenario: Explicit AREA participants drive one round
- **WHEN** a player submits an AREA skill with two distinct current enemy objects
- **THEN** the facade builds one ActionRequest containing both canonical participants and drives exactly one ordinary round

#### Scenario: Approved shorthand reaches ordinary targeting
- **WHEN** a player submits an AREA skill with `all-enemies`
- **THEN** the facade preserves the shorthand for ActionResolver expansion and every resulting candidate passes ordinary target validation

#### Scenario: Old single-object input is not retained
- **WHEN** a production caller passes one participant object instead of a list
- **THEN** the facade rejects the malformed call before initiative rather than wrapping it through a compatibility branch
