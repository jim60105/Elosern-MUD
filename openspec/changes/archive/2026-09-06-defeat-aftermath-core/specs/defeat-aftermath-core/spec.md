# defeat-aftermath-core delta

## ADDED Requirements

### Requirement: Hostile defeat floors player HP at 1 and marks the player knocked out
On a hostile-mode session settling `outcome == "defeat"`, the defeat
aftermath writer (`world/rules/defeat_aftermath.py`, deterministic core)
SHALL set the player's stored HP to `1` and record the player in the
session's knockout set before clearing session state. No defeat settlement
SHALL leave the player at stored HP 0. Guild-exam (`exam_failed`) outcomes
are exempt and keep their full-restoration simulation semantics.

#### Scenario: Defeated player settles at the nonlethal floor
- **WHEN** a hostile session settles defeat with the player's HP driven to 0 mid-round
- **THEN** after settlement the player's stored HP equals `1` and the session is cleared

#### Scenario: Exam defeat keeps full restoration
- **WHEN** a guild-exam session settles `exam_failed`
- **THEN** every exam participant's HP is restored to its pre-exam value and no aftermath phase runs

### Requirement: Living winning violators depart the room, quest-bound monsters retained
At defeat settlement, every living foe-team monster carrying the wilderness
ownership marker `db.population_key` SHALL be logically departed inside the
settlement transaction: its marker is cleared and it is dropped from the
wilderness script's `itemcoordinates`. Its physical Evennia-object deletion
SHALL be scheduled only after the outermost transaction commits (through
`transaction.on_commit`), because a deleted idmapper instance cannot be
restored on rollback. If the post-commit deletion fails, the logical
departure SHALL be reverted deterministically so the monster remains a
normal, reconcilable population monster; only a process crash in the
post-commit window may leave a marker-less live monster (the parent
design's accepted restart-refresh risk). A living foe-team monster whose pk
appears in any of the settling player's persisted quest records
(`db.quest_log` entries' `objective_target_ids`) SHALL NOT be removed and
SHALL remain in the room — the quest-retention rule wins over the
population-despawn rule for a monster carrying both a `population_key` and
a quest binding. Foreign monsters (no marker, not quest-bound) SHALL be
left untouched.

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
`defeat_settle`, `violator_depart`, and `weak_granted`, and SHALL render
zh-tw defeat lines through the existing `player_messages.py` idiom. Each
new kind is an open-vocabulary `EventEntry.kind` string accompanied by its
own offline template line authored in this change (no schema change; the
webclient's current render path is untouched). It SHALL emit one
`defeat_aftermath` boundary info event through the observability facade
carrying `{char, room, tick, hp_after}` context.

#### Scenario: Offline defeat produces the full event trail
- **WHEN** a defeat settles with every LLM profile disabled
- **THEN** the three aftermath EventLog kinds appear in order, the player receives the zh-tw defeat lines, and exactly one `defeat_aftermath` info event is logged

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
protected-entity bindings — except changes causally produced by the world
clock advancing (a crossed deadline failing a quest, a crossed daily
boundary changing a gauge, a crossed restock boundary restocking a
merchant, a buff decaying). The settlement's own writes are only the
declared ones: player HP floor, the knockout mark, the weak buff, the
violator departure, and its own EventLog/observability records.

#### Scenario: Defeat battery pins the zero-uncaused-write contract
- **WHEN** a defeat settles with an active quest, bound companions, guild rank, and nonzero copper, with the recovery window advanced no further than the settlement itself drives it
- **THEN** affinity, wallet, inventory, guild rank/merit, and protected bindings are unchanged; quest progress changes appear only if a clock boundary causally crossed; and no other record carries a write

### Requirement: The defeat aftermath joins the round's atomic persistence unit
The defeat aftermath SHALL run inside `settle_session`'s existing
`transaction.atomic()` block, before the session record is cleared.
Because the `settled_tick` marker, the clock, the logical departures (the
marker and `itemcoordinates` removal), the buffs, and the aftermath commit
or roll back together, there is no observable state in which the marker is
durable but the aftermath is incomplete. The physical deletions ride
`transaction.on_commit`, so an outer round transaction's rollback discards
them together with every other aftermath write. A crash
before commit leaves the session durable for the existing recovery
fallback, which re-runs settlement — including the aftermath — once;
aftermath dice (contributed by adult layers) derive purely from durable
record state, so the replay produces the identical outcome.

#### Scenario: Commit failure rolls back the whole aftermath
- **WHEN** a fault is injected after the aftermath's last write and before commit
- **THEN** the logical departures (the monster keeps its marker and `itemcoordinates` entry), the weak buff, the HP floor, the EventLog entries, and the session clearing are all absent, and the next settlement attempt produces the full defeat outcome exactly once
