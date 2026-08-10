# affinity-system Specification

## Purpose

Define the hidden NPC-to-player affinity foundation: per-NPC per-player records, the seven-stage
Traditional Chinese ladder, the sole-writer API with a source-capped daily budget, deterministic
gains at the existing talk/trade/guild success paths, stage-only presentation, and the party
auto-leave recheck seam consumed by later party changes.

## Requirements

### Requirement: Every NPC holds a hidden numeric affinity toward each player
Each NPC SHALL hold one affinity record per player it has interacted with, stored as serialized
data on the NPC's `relations_data` attribute through the `RelationHandler` mounted on
`LivingEntity.relations`. A record SHALL contain `value` (initial 0), `cap` (initial 99, mutable
only through `raise_affinity_cap`), the daily-gain counter, and the world-day tick at which that
counter started. Deserialization SHALL tolerate missing fields with defaults and SHALL reject
type-violating values by resetting the record to a fresh default (logging the event) rather than
raising, so a corrupted record can never crash a look or a conversation. Reading affinity SHALL NOT
create or persist a record: read APIs (`affinity_for`, `stage_for`) return defaults for players
without a record, and a `has_record` check SHALL distinguish a stored record from a default. The
numeric value SHALL be hidden from the player; only stage names are rendered (see the stage-ladder
requirement).

#### Scenario: A fresh NPC starts at zero affinity
- **WHEN** a player reads the affinity record of an NPC with no prior interaction
- **THEN** the reported value is 0, the cap is 99, and no record is persisted on the NPC

#### Scenario: Reading never materializes a record
- **WHEN** a player looks at a recordless NPC and then the NPC's stored data is inspected
- **THEN** `has_record` is false and `relations_data` holds no entry for that player

#### Scenario: A corrupted record resets instead of crashing
- **WHEN** an NPC's `relations_data` attribute holds a record whose `value` is a string
- **THEN** reading the record yields the fresh default record (value 0, cap 99) and logs the
  recovery instead of raising

#### Scenario: Records are keyed per player
- **WHEN** two different players interact with the same NPC
- **THEN** each player's record reads and writes independently

#### Scenario: The cap is mutable only through the sole cap writer
- **WHEN** the code paths that mutate a record's `cap` are inspected
- **THEN** every mutation goes through `raise_affinity_cap`, and a raised cap (e.g. 150) persists
  across serialization round trips without changing the value or the daily-gain fields

### Requirement: The stage ladder maps hidden values to seven Traditional Chinese stage names
`rulebook/affinity.yaml` SHALL define exactly seven stages with floors 0 (初識), 10 (熟識),
30 (親睦), 50 (信賴), 70 (羈絆), 90 (至愛), and 100 (絕對羈絆), each with a stable ID, a floor, a
display name, and an authored look-flavor template. The stage for a value SHALL be the last stage
whose floor is at or below the value; values at or above 100 SHALL map to the topmost stage (絕對羈絆).
Loading SHALL reject any deviation from the canonical floor sequence — a wrong stage count,
non-increasing floors, or a floor outside the canonical set 0/10/30/50/70/90/100 — with a named
validation error before any write. The same YAML SHALL carry the offline party-invite threshold
(70), the daily interaction cap (5), and the quest-completion gain (2). Player-facing glyphs SHALL
be Traditional Chinese forms (信賴, 絕對).

#### Scenario: Stage boundaries map values to names
- **WHEN** values 0, 10, 30, 50, 70, 90, 99, and 100 are resolved against the ladder
- **THEN** they map to 初識, 熟識, 親睦, 信賴, 羈絆, 至愛, 至愛, and 絕對羈絆 respectively

#### Scenario: A deviant floor sequence is rejected at load
- **WHEN** a stage definition uses a floor outside the canonical set, a duplicated floor, or a
  stage count other than seven
- **THEN** loading the rulebook fails closed with a named validation error

#### Scenario: A future value above the natural cap still renders the topmost stage
- **WHEN** a record's `cap` has been raised beyond 99 and its value is 130
- **THEN** the displayed stage is 絕對羈絆 and no numeric value or cap is rendered anywhere

### Requirement: apply_affinity_change is the sole affinity writer with a source-capped daily budget
`world/rules/affinity.py` SHALL expose `apply_affinity_change(npc, player, source, delta)` as the
only function that writes affinity values. The source SHALL be a member of the closed set
(`talk`, `trade`, `guild`, `ai_dialogue`, `quest_completion`, `friendly_fire`); an unknown source
SHALL be rejected without writing. The writer SHALL reject a non-NPC owner without writing. Before
budgeting a capped positive delta it SHALL lazily reset the daily-gain counter when the record's
stored tick differs from the current world day; negative deltas (including `friendly_fire`) SHALL
never reset the counter and never restore spent budget. Positive deltas from the capped sources
SHALL draw from the remaining daily budget (`cap` 5 shared across `talk`, `trade`, `guild`,
`ai_dialogue`); `quest_completion` deltas SHALL bypass the cap. The applied delta SHALL be
`min(requested, remaining_budget, cap - value)`, the daily counter SHALL accrue only the actually
applied increase, and a delta that applies zero SHALL consume no budget. Positive deltas SHALL
clamp to the record's `cap`; negative deltas SHALL apply unclamped downward (floor 0) and always
run the party auto-leave recheck hook. The function SHALL return a structured outcome (applied,
delta used, budget capped) so callers can render feedback.

#### Scenario: Capped sources exhaust the daily budget
- **WHEN** capped-source gains total 5 in one world day and a sixth capped gain is attempted
- **THEN** the sixth gain is rejected with a capped outcome, no budget is consumed, and the value
  stays unchanged

#### Scenario: A partial delta applies only the remaining budget
- **WHEN** a requested capped delta of 4 arrives with 2 budget remaining
- **THEN** exactly 2 is applied, the daily counter accrues 2, and the outcome reports the applied
  amount

#### Scenario: A delta at the natural cap consumes no budget
- **WHEN** a capped delta is requested while the value already equals the record's cap
- **THEN** zero is applied, no budget is consumed, and the outcome reports zero applied

#### Scenario: The budget resets on a new world day
- **WHEN** the daily budget is exhausted and the world clock advances to the next day
- **THEN** a new capped gain applies and increments the value

#### Scenario: Quest-completion gains bypass the daily cap
- **WHEN** the daily budget is exhausted and a `quest_completion` gain of 2 is attempted
- **THEN** the gain applies and the value increases

#### Scenario: Negative deltas never reset or restore the budget
- **WHEN** a negative delta (including a `friendly_fire` penalty) applies after the budget was
  exhausted
- **THEN** the value decreases, the daily counter stays exhausted, and the auto-leave hook runs

#### Scenario: A friendly_fire source is accepted without budget interaction
- **WHEN** a call supplies the `friendly_fire` source with a negative delta
- **THEN** the penalty applies downward without consuming or resetting the daily budget, and the
  outcome reports the applied amount

#### Scenario: An unknown source is rejected without writing
- **WHEN** a call supplies a source outside the closed set
- **THEN** the outcome is rejected, no value or counter changes, and no record is created

#### Scenario: A non-NPC owner is rejected without writing
- **WHEN** a call supplies a player or monster as the affinity owner
- **THEN** the outcome is rejected and no state changes

### Requirement: Deterministic gains apply at talk, trade, and guild success paths
A known-keyword talk answer SHALL grant +1 affinity (`talk` source) with the host NPC through a
deterministic talk writer that resolves the keyword, records any onboarding `guide_progress`
update, and applies the affinity gain in one transaction with cache restoration on failure; unknown
keywords and no-keyword paths SHALL grant nothing. A successful buy or sell SHALL grant +1
(`trade` source) with the local Merchant host. Successful guild registration, board acceptance,
and examination start SHALL each grant +1 (`guild` source) with the respective host. Every gain
SHALL be applied through the sole-writer API inside the host operation's all-or-nothing commit, so
a failing or rejected host operation grants nothing. Service hosts SHALL be NPC instances: a
host that cannot hold affinity is rejected before any write, so a successful operation always
carries its gain. When a capped source is blocked by the daily
budget, the call site SHALL present a fixed non-numeric Traditional Chinese hint and SHALL NOT
expose the cap or any number.

#### Scenario: Keyword talk grants affinity and unknown keywords grant nothing
- **WHEN** the player talks to a scripted-dialogue host with a known keyword and then with an
  unknown keyword
- **THEN** the known-keyword answer raises the host's value by 1 and the unknown keyword changes
  nothing

#### Scenario: Guard keyword tracking and affinity commit together
- **WHEN** the player talks to the South Gate guard with a known guard keyword
- **THEN** the guard answers, `guide_progress` records the keyword, and the guard's affinity value
  rises by 1 in one commit; if any write fails, both surfaces are restored

#### Scenario: A failed operation grants no affinity
- **WHEN** a trade, registration, acceptance, or examination is rejected before committing
- **THEN** the involved NPC's affinity record is unchanged

#### Scenario: A non-NPC service host is rejected before any write
- **WHEN** an operation targets a service host that is not an NPC (for example an object
  carrying a Merchant component)
- **THEN** the operation is rejected before any write and no affinity is granted

#### Scenario: A budget-capped gain gives non-numeric feedback
- **WHEN** a capped source would gain affinity but the daily budget is exhausted
- **THEN** the player receives a fixed Traditional Chinese hint that does not contain the cap,
  the budget, or any number, and the NPC's value is unchanged

### Requirement: The party auto-leave recheck hook runs after negative affinity deltas
The sole-writer API SHALL invoke the party auto-leave recheck after every negative delta. The hook
SHALL be the wired rule from `party-core`: when the NPC is a bound companion and its affinity
toward the player drops below the invite threshold (70), it SHALL call
`world/rules/party.py::leave_party(npc, player, reason="affinity_below_threshold")` as part of the
affinity write's transaction — a failed leave SHALL roll back the entire negative-delta operation
— and the write API SHALL return the auto-leave notification line, which the caller SHALL send to
the player only after its own transaction commits (the writer never sends it); a drop that stays
at or above the threshold SHALL NOT end the party. The hook SHALL be deterministic and SHALL be
side-effect free for non-companions.

#### Scenario: The hook is invoked on negative deltas
- **WHEN** a negative delta is applied through the sole-writer API
- **THEN** the auto-leave recheck hook runs once with the affected NPC and player

#### Scenario: A below-threshold drop ends a companion party
- **WHEN** a bound companion's affinity drops from 70 to 69 through a negative delta
- **THEN** the binding is removed with the auto-leave reason, the write API returns the
  notification line, and the caller notifies the player only after the write commits

#### Scenario: A failed auto-leave rolls back the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold
- **THEN** the affinity value and both party attributes return to their pre-delta values and no
  notification is emitted

#### Scenario: A non-companion negative delta changes nothing
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** the hook runs, no party call occurs, and no notification is emitted

### Requirement: Affinity presentation is stage-only and never exposes the numeric value
NPC appearance SHALL include one affinity stage line rendered from the record's stage for the
looking player (for example 「她看著你的眼神裡帶著信賴。」), and SHALL render no line for entities
without a record (checked via `has_record`, which never persists). No player-facing text SHALL
expose the numeric value, the cap, the daily budget, or the threshold. The same line SHALL appear
on the text look command, the `at_look` hook, and the webclient explore-look action.

#### Scenario: Look shows the stage line without a number
- **WHEN** a player looks at an NPC with a 信賴-stage record
- **THEN** the appearance includes the stage flavor line for 信賴 and contains no numeric affinity
  value, cap, or threshold

#### Scenario: Entities without a record render no stage line
- **WHEN** a player looks at a monster or an NPC with no affinity record
- **THEN** the appearance contains no affinity line and no record is persisted by the look
