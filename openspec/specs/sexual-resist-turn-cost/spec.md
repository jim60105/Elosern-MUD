# sexual-resist-turn-cost Specification

## Purpose

Define the deterministic turn-cost of a forced sexual act in combat: a validated
`sexual_forced_penalty` rulebook field, a coercion scan that penalizes exactly the forced
outcome (never compliance or successful resistance), the scan's placement inside the round's
shared outer transaction, and the widened relations snapshot that makes rollback reach every
roster NPC. The capability wires the affinity consequence of `sexual-resist-contest`'s verdict
into live combat rounds; the emitter of the resist-outcome log contract lands in later
proposals.

## Requirements

### Requirement: sexual_forced_penalty is a validated rulebook field, independent of friendly_fire_penalty_per_hit
`world/rules/rulebook/affinity.yaml` SHALL declare `sexual_forced_penalty`, a non-negative integer,
validated by `world/rules/affinity_config.py`'s loader with the same shape and fail-closed discipline
as the existing `friendly_fire_penalty_per_hit` field. `AffinityConfig`'s top-level field set SHALL
include `sexual_forced_penalty` alongside the existing fields.

#### Scenario: A missing sexual_forced_penalty fails closed
- **WHEN** `affinity.yaml` omits `sexual_forced_penalty`
- **THEN** loading the rulebook raises, naming the missing field

#### Scenario: A negative sexual_forced_penalty fails closed
- **WHEN** `affinity.yaml` declares `sexual_forced_penalty` as a negative integer
- **THEN** loading the rulebook raises

#### Scenario: sexual_forced_penalty and friendly_fire_penalty_per_hit are independently configurable
- **WHEN** `affinity.yaml` declares `sexual_forced_penalty` and `friendly_fire_penalty_per_hit` with
  different values
- **THEN** both load successfully and each is readable through `get_config()` independently

### Requirement: _scan_sexual_coercion penalizes exactly the forced outcome, never comply or successful resistance
`world/rules/combat_session.py` SHALL provide `_scan_sexual_coercion(actor, battlefield, logs) ->
tuple[str, ...]`, scanning the round's `list[EventLog]` for `EventEntry` records with
`kind == "sexual_resist"` and `event_log.actor` equal to the submitting player's key (mirroring
`_scan_friendly_fire`'s actor filter, so a future non-player emitter can never charge the player's
affinity for someone else's act). A `kind == "sexual_resist"` entry whose `data` is not a mapping
SHALL be ignored without penalizing and without raising. For every qualifying entry whose
`data["resisted"] is False` and `data["auto_comply"] is False` — a forced outcome — it SHALL apply
`-sexual_forced_penalty` through `world.rules.affinity.apply_affinity_change(target, actor,
AffinitySource.SEXUAL_FORCED, ...)`, resolving `target` from `battlefield.roster.get(entry.target)`.
An entry with `data["resisted"] is True` (successful resistance) or `data["auto_comply"] is True`
(compliance, rolled or automatic) SHALL apply no penalty. A `kind == "sexual_resist"` entry whose
resolved target is not an `NPC` SHALL apply no penalty (mirroring `apply_affinity_change`'s own
owner rejection, without needing to call it).

#### Scenario: A forced act applies exactly one penalty
- **WHEN** the round's logs contain one `kind == "sexual_resist"` entry with
  `data = {"resisted": False, "auto_comply": False, "roll": <int>}` targeting a companion `NPC`
- **THEN** `_scan_sexual_coercion` applies exactly one `-sexual_forced_penalty` delta through
  `apply_affinity_change` with `AffinitySource.SEXUAL_FORCED`

#### Scenario: A complied-with act applies no penalty
- **WHEN** the round's logs contain one `kind == "sexual_resist"` entry with
  `data = {"resisted": False, "auto_comply": False, "roll": <int>}` is absent and instead
  `data = {"resisted": False, "auto_comply": True, "roll": None}` is present
- **THEN** `_scan_sexual_coercion` applies no affinity penalty for that entry

#### Scenario: A successfully resisted act applies no penalty
- **WHEN** the round's logs contain one `kind == "sexual_resist"` entry with
  `data = {"resisted": True, "auto_comply": False, "roll": <int>}`
- **THEN** `_scan_sexual_coercion` applies no affinity penalty for that entry

#### Scenario: Multiple forced entries in one round each apply their own penalty
- **WHEN** the round's logs contain two `kind == "sexual_resist"` entries, both forced, targeting two
  different companion NPCs
- **THEN** `_scan_sexual_coercion` applies two separate `-sexual_forced_penalty` deltas, one per
  target

#### Scenario: A forced entry targeting a non-NPC applies no penalty
- **WHEN** a `kind == "sexual_resist"` entry's `target` resolves to a `Monster` or a
  `PlayerCharacter` rather than an `NPC`
- **THEN** `_scan_sexual_coercion` applies no penalty for that entry, and does not call
  `apply_affinity_change` for it

#### Scenario: A non-sexual-resist entry is ignored
- **WHEN** the round's logs contain `EventEntry` records of other kinds (for example `"damage"`)
  alongside or instead of any `"sexual_resist"` entry
- **THEN** `_scan_sexual_coercion` applies no penalty attributable to those entries

#### Scenario: A non-player-actor resist entry is ignored
- **WHEN** the round's logs contain a forced `kind == "sexual_resist"` entry whose
  `event_log.actor` is not the submitting player's key (for example a companion's or monster's own
  cast, a shape a future emitter could produce)
- **THEN** `_scan_sexual_coercion` applies no penalty for that entry and does not call
  `apply_affinity_change` for it

#### Scenario: A malformed non-mapping data payload is ignored without raising
- **WHEN** a `kind == "sexual_resist"` entry's `data` is not a mapping (for example a string or a
  list)
- **THEN** `_scan_sexual_coercion` applies no penalty for that entry, does not call
  `apply_affinity_change` for it, and does not raise

### Requirement: The coercion scan runs inside the round's shared outer transaction, symmetric with friendly fire
`submit_player_action` SHALL call `_scan_sexual_coercion(actor, battlefield, logs)` inside the same
shared outer transaction as the existing `_scan_friendly_fire` call, and SHALL combine both scans'
auto-leave notification lines into the outcome the caller sends after commit. A round whose outer
transaction rolls back SHALL leave no `sexual_forced` affinity write persisted or observable
in-process.

#### Scenario: A forced sexual-act penalty commits atomically with the round
- **WHEN** a round resolves successfully and includes a forced `kind == "sexual_resist"` entry
- **THEN** the resulting affinity penalty and the round's other durable effects commit together in
  the same transaction

#### Scenario: A rolled-back round leaves no coercion-penalty trace
- **WHEN** a round that would apply a `sexual_forced` penalty fails after `_scan_sexual_coercion` has
  run but before the outer transaction commits
- **THEN** the affected NPC's affinity value is unchanged both in the database and in-process after
  the rollback

#### Scenario: Friendly-fire and coercion penalties in the same round both apply
- **WHEN** a single round's logs contain both a qualifying `"damage"` entry against a companion and a
  forced `"sexual_resist"` entry against a (possibly different) companion
- **THEN** both `_scan_friendly_fire` and `_scan_sexual_coercion` apply their respective penalties
  within the same commit

### Requirement: The relations snapshot covers every roster NPC, not only party companions
Before a round runs, `world/rules/combat_session.py` SHALL snapshot `relations_data` for every
`NPC` present in `battlefield.roster`, not only those whose `pk` is a declared party companion. On a
rolled-back round, every snapshotted NPC's `relations_data` SHALL be restored, including a
non-companion NPC whose affinity was written only by `_scan_sexual_coercion`.

#### Scenario: A non-companion NPC's affinity write survives a successful round
- **WHEN** a round applies a `sexual_forced` penalty to an `NPC` present on the battlefield but not a
  declared party companion, and the round commits successfully
- **THEN** that NPC's affinity value reflects the applied penalty afterward

#### Scenario: A non-companion NPC's affinity write is rolled back correctly, even with no companions present
- **WHEN** a round applies a `sexual_forced` penalty to a non-companion `NPC` on a battlefield where
  the acting player has **zero declared party companions**, and the round's outer transaction
  subsequently fails
- **THEN** that NPC's `relations_data` is restored to its pre-round value both in the database and in
  the in-process idmapper cache, with no observable trace of the rolled-back write — the snapshot
  loop MUST run even when the actor has no companions, not only when a non-companion NPC happens to
  share a battlefield with at least one companion

#### Scenario: Companion snapshot coverage is unchanged
- **WHEN** a round involves only declared party-companion NPCs
- **THEN** the snapshot and restore behavior for those companions is unchanged from the existing
  friendly-fire mechanism's behavior
