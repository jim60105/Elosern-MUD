# defeat-aftermath-core Specification

## Purpose

Define the deterministic, offline defeat settlement: the nonlethal HP floor,
violator departure with quest-retention precedence, the weak debuff, the
defeat EventLog kinds, and the guarded adult-scene hook point.

## Requirements

### Requirement: Hostile defeat floors player HP at 1 and marks the player knocked out
On a hostile-mode session settling `outcome == "defeat"`, the defeat
aftermath writer (`world/rules/defeat_aftermath.py`, deterministic core)
SHALL set the player's stored HP to `1` at the floor phase and record the
player in the session's knockout set before clearing session state. No
defeat settlement SHALL leave the player at stored HP 0. Guild-exam
(`exam_failed`) outcomes are exempt and keep their full-restoration
simulation semantics.

#### Scenario: Defeated player settles at the nonlethal floor
- **WHEN** a hostile session settles defeat with the player's HP driven to 0 mid-round
- **THEN** the floor phase stores HP `1` and the session is cleared; the recovery phase then wakes the player at exactly its 5% target before the settlement completes

#### Scenario: Exam defeat keeps full restoration
- **WHEN** a guild-exam session settles `exam_failed`
- **THEN** every exam participant's HP is restored to its pre-exam value and no aftermath phase runs

#### Scenario: The final wake state belongs to the recovery capability
- **WHEN** the aftermath's floor write completes
- **THEN** the final wake state is the recovery advance's target defined by the
  defeat-aftermath-recovery capability; the floor remains the declared interim write

### Requirement: Living winning violators depart the room, quest-bound monsters retained
At defeat settlement, every living foe-team monster carrying the wilderness
ownership marker `db.population_key` SHALL be logically departed inside the
settlement transaction: its marker is cleared and it is dropped from the
wilderness script's `itemcoordinates`.

#### Scenario: Population winner despawns at defeat settlement
- **WHEN** a player loses to a wilderness population monster carrying `population_key`
- **THEN** the monster is absent from `itemcoordinates` as part of the committed settlement and, after the post-commit departure callback completes, its object is deleted; the next coordinate activation reconciles a fresh monster as today

#### Scenario: Post-commit deletion failure reverts the departure
- **WHEN** the physical object deletion fails after the settlement committed
- **THEN** the marker and the `itemcoordinates` entry are restored, the monster remains a normal live population monster, and the failure is logged at error level

#### Scenario: Quest-bound winner is retained
- **WHEN** a player loses to a monster whose pk is listed in a persisted quest record's `objective_target_ids`
- **THEN** the monster remains in the room and the quest record is unchanged

#### Scenario: Quest binding outranks the population marker
- **WHEN** a monster carries both `population_key` and a `quest_log` `objective_target_ids` binding
- **THEN** it is retained, never despawned

#### Scenario: Physical deletion is deferred to after the outermost commit
- **WHEN** a logical departure is committed
- **THEN** the physical Evennia-object deletion is scheduled only after the outermost transaction
  commits (through `transaction.on_commit`), because a deleted idmapper instance cannot be
  restored on rollback

#### Scenario: A crash in the post-commit window is the accepted residual risk
- **WHEN** the process crashes in the post-commit window between commit and physical deletion
- **THEN** only that crash may leave a marker-less live monster — the parent design's accepted
  restart-refresh risk

#### Scenario: Foreign monsters are left untouched
- **WHEN** a living foe-team monster has no `db.population_key` marker and no quest binding
- **THEN** defeat settlement leaves it untouched

### Requirement: Defeat weak debuff is mounted at settle time
The aftermath SHALL grant the `defeat_weak` buff defined in
`world/rules/rulebook/buffs.yaml`: a marker buff whose declared modifiers
stay inside the shipped effect surface (`bounds` ceilings on existing stat
targets), with duration in advanced world seconds. It SHALL expire through
the ordinary decay stage without any special path.

#### Scenario: Weak debuff mounted at defeat and self-expiring
- **WHEN** a defeat settlement completes
- **THEN** the player carries `defeat_weak` with its rulebook bounds
  modifiers, and a further world-time advance beyond its duration removes it

### Requirement: Defeat aftermath emits EventLog entries and defeat lines
The aftermath SHALL record ordered EventLog entries with kinds
`defeat_settle`, `violator_depart`, and `weak_granted` — followed by the
recovery phase's `recovery_advance` entry when that phase advances the
clock (defeat-aftermath-recovery) — and SHALL render zh-tw defeat lines
through the existing `player_messages.py` idiom.

#### Scenario: Offline defeat produces the full event trail
- **WHEN** a defeat settles with every LLM profile disabled
- **THEN** the core aftermath EventLog kinds appear in order — followed by the recovery entry when the phase advances — the player receives the zh-tw defeat lines, and exactly one `defeat_aftermath` info event is logged

#### Scenario: New event kinds are open-vocabulary strings with offline template lines
- **WHEN** a new aftermath EventLog kind is introduced
- **THEN** it is an open-vocabulary `EventEntry.kind` string accompanied by its own offline
  template line authored in its change (no schema change; the webclient's current render path is
  untouched)

#### Scenario: One boundary info event carries the settlement context
- **WHEN** a defeat aftermath settles
- **THEN** it emits one `defeat_aftermath` boundary info event through the observability facade
  carrying `{char, room, tick, hp_after}` context, widened with `seconds` and `hp_wake` by the
  recovery phase

### Requirement: The DEFEAT_ADULT_SCENES setting exists and guards the violation hook
The server settings SHALL define `DEFEAT_ADULT_SCENES` (default `True`).
The core settlement SHALL consult it once, at aftermath-phase entry,
purely as a guard around the violation-sequence hook point: with the flag
off, the hook is never called and the settlement state is exactly the
core-only behavior described by this capability. The core itself SHALL
have no branch that changes behavior when the flag is on — the guarded
body is contributed by the adult-layer changes.

#### Scenario: Flag off settles exactly the core path
- **WHEN** a defeat settles with `DEFEAT_ADULT_SCENES` false
- **THEN** the violation hook is never invoked and the settled state equals this capability's requirements verbatim

### Requirement: Defeat settlement's only uncaused record writes are the declared ones
A defeat settlement SHALL leave, for the settling player and each allied
participant, byte-identical values for: affinity, wallet copper, inventory
contents, quest progress values, guild rank and merit, and
protected-entity bindings. The settlement's own writes are only the
declared ones: player HP floor, the knockout mark, the weak buff, the
violator departure, the recovery advance with its wake clamp (or its
capped scaled-model settle), and the aftermath's EventLog/observability
records.

#### Scenario: Defeat battery pins the zero-uncaused-write contract
- **WHEN** a defeat settles with an active quest, bound companions, guild rank, and nonzero copper, with the recovery window advanced no further than the settlement itself drives it
- **THEN** affinity, wallet, inventory, guild rank/merit, and protected bindings are unchanged; quest progress changes appear only if a clock boundary causally crossed; and no other record carries a write

#### Scenario: Clock-caused changes are the sole permitted exceptions
- **WHEN** the world clock advances during a defeat settlement
- **THEN** only changes causally produced by that advance are exempt from byte-identity: a
  crossed deadline failing a quest, a crossed daily boundary changing a gauge, a crossed restock
  boundary restocking a merchant, a buff decaying

### Requirement: The defeat aftermath joins the round's atomic persistence unit
The defeat aftermath SHALL run inside `settle_session`'s existing
`transaction.atomic()` block, before the session record is cleared.

#### Scenario: Commit failure rolls back the whole aftermath
- **WHEN** a fault is injected after the aftermath's last write and before commit
- **THEN** the logical departures (the monster keeps its marker and `itemcoordinates` entry), the weak buff, the HP floor, the EventLog entries, and the session clearing are all absent, and the next settlement attempt produces the full defeat outcome exactly once

#### Scenario: Marker and aftermath share one commit-or-rollback unit
- **WHEN** the round's persistence unit runs
- **THEN** the `settled_tick` marker, the clock, the logical departures (the marker and
  `itemcoordinates` removal), the buffs, and the aftermath commit or roll back together, so there
  is no observable state in which the marker is durable but the aftermath is incomplete

#### Scenario: Physical deletions ride on_commit
- **WHEN** an outer round transaction rolls back
- **THEN** the physical deletions — which ride `transaction.on_commit` — are discarded together
  with every other aftermath write

#### Scenario: A pre-commit crash replays the settlement identically
- **WHEN** the process crashes before commit
- **THEN** the session stays durable for the existing recovery fallback, which re-runs settlement
  — including the aftermath — once; aftermath dice (contributed by adult layers) derive purely
  from durable record state, so the replay produces the identical outcome
