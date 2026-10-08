# affinity-system Specification

## Purpose

Define the hidden NPC-to-player affinity foundation: per-NPC per-player records, the seven-stage
Traditional Chinese ladder, the sole-writer API with a source-capped daily budget, deterministic
gains at the existing talk/trade/guild success paths, stage-only presentation, and the party
auto-leave recheck seam consumed by later party changes.

## Requirements

### Requirement: Every NPC holds a hidden numeric affinity toward each player
Each NPC SHALL hold one per-player affinity record as serialized data on the NPC's
`relations_data` attribute through the `RelationHandler` mounted on `LivingEntity.relations`.
A record SHALL contain `value` (initial 0), `cap` (initial 99, mutable only through
`raise_affinity_cap`), the daily-gain counter, and the world-day tick at which that counter
started. The numeric value SHALL be hidden from the player; only stage names are rendered (see
the stage-ladder requirement).

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

#### Scenario: Deserialization tolerates missing fields and rejects type violations by resetting
- **WHEN** a stored record is deserialized with fields missing, or with a type-violating value
- **THEN** missing fields fall back to defaults, and a type-violating value resets the record to a fresh default (logging the event) rather than raising, so a corrupted record can never crash a look or a conversation

#### Scenario: The read APIs return defaults without persisting
- **WHEN** `affinity_for` or `stage_for` is called for a player that has never interacted with the NPC
- **THEN** the default record is returned without creating or persisting anything, and the `has_record` check distinguishes a stored record from a default

### Requirement: The stage ladder maps hidden values to seven Traditional Chinese stage names
`rulebook/affinity.yaml` SHALL define exactly seven stages with floors 0 (初識), 10 (熟識),
30 (親睦), 50 (信賴), 70 (羈絆), 90 (至愛), and 100 (絕對羈絆), each with a stable ID, a floor, a
display name, and an authored look-flavor template. The stage for a value SHALL be the last stage
whose floor is at or below the value; values at or above 100 SHALL map to the topmost stage (絕對羈絆).

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

#### Scenario: A deviant ladder fails closed at load before any write
- **WHEN** the ladder deviates from the canonical floor sequence — a wrong stage count, non-increasing floors, or a floor outside the canonical set 0/10/30/50/70/90/100
- **THEN** loading rejects it with a named validation error before any write

#### Scenario: The same YAML carries the tuning values
- **WHEN** `rulebook/affinity.yaml` is read for its non-ladder settings
- **THEN** it carries the offline party-invite threshold (70), the daily interaction cap (5), and the quest-completion gain (2)

#### Scenario: Player-facing glyphs are Traditional Chinese
- **WHEN** any player-facing affinity glyph is rendered
- **THEN** it uses Traditional Chinese forms (信賴, 絕對)

### Requirement: apply_affinity_change is the sole affinity writer with a source-capped daily budget
`world/rules/affinity.py` SHALL be the only module that writes affinity values, and
`apply_affinity_change(npc, player, source, delta)` SHALL be its only *interaction* writer. The
source SHALL be a member of the closed set (`talk`, `trade`, `guild`, `ai_dialogue`,
`quest_completion`, `friendly_fire`, `sexual_forced`). The applied delta SHALL be
`min(requested, remaining_budget, cap - value)`. The same module SHALL expose exactly one *seed*
writer, `seed_affinity(npc, player, value)`.

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
- **WHEN** a negative delta (including a `friendly_fire` or `sexual_forced` penalty) applies after
  the budget was exhausted
- **THEN** the value decreases, the daily counter stays exhausted, and the auto-leave hook runs

#### Scenario: A friendly_fire source is accepted without budget interaction
- **WHEN** a call supplies the `friendly_fire` source with a negative delta
- **THEN** the penalty applies downward without consuming or resetting the daily budget, and the
  outcome reports the applied amount

#### Scenario: A sexual_forced source is accepted without budget interaction
- **WHEN** a call supplies the `sexual_forced` source with a negative delta
- **THEN** the penalty applies downward without consuming or resetting the daily budget, and the
  outcome reports the applied amount

#### Scenario: An unknown source is rejected without writing
- **WHEN** a call supplies a source outside the closed set
- **THEN** the outcome is rejected, no value or counter changes, and no record is created

#### Scenario: A non-NPC owner is rejected without writing
- **WHEN** a call supplies a player or monster as the affinity owner
- **THEN** the outcome is rejected and no state changes

#### Scenario: A seed establishes a starting relationship
- **WHEN** `seed_affinity` is called for a pair with no existing record and a value inside `1..NATURAL_CAP`
- **THEN** the record is created at that value with `cap` equal to `NATURAL_CAP`, a zero daily counter stamped with the current world day, and no auto-leave recheck runs

#### Scenario: A seed never overwrites an existing relationship
- **WHEN** `seed_affinity` is called for a pair that already holds a record
- **THEN** it raises without writing, so an interaction history can never be replaced by a seed

#### Scenario: A seed rejects an out-of-range value
- **WHEN** `seed_affinity` is called with a value below 1 or above `NATURAL_CAP`
- **THEN** it raises without writing

#### Scenario: A seed consumes no daily budget
- **WHEN** a relationship is seeded and a capped interaction gain is attempted on the same world day
- **THEN** the full daily budget is still available to that interaction

#### Scenario: A seed rejects a non-NPC owner or a non-integer value
- **WHEN** `seed_affinity` is called with a player or monster as the affinity owner, or with a boolean or non-integer value
- **THEN** it raises without writing

#### Scenario: The writer returns a structured outcome
- **WHEN** an interaction write completes through the sole-writer API
- **THEN** it returns a structured outcome (applied, delta used, budget capped) so callers can render feedback

#### Scenario: The daily counter resets lazily from the stored world-day tick
- **WHEN** a capped positive delta is budgeted and the record's stored tick differs from the current world day
- **THEN** the daily-gain counter is lazily reset before the budget is drawn

#### Scenario: The shared daily budget covers the four capped interaction sources
- **WHEN** positive deltas arrive from the capped sources
- **THEN** they draw from the remaining daily budget — a `cap` of 5 shared across `talk`, `trade`, `guild`, and `ai_dialogue` — while `quest_completion` deltas bypass the cap

#### Scenario: A positive delta clamps to the record cap
- **WHEN** a positive delta would push the value above the record's `cap`
- **THEN** the value clamps to `cap`

#### Scenario: A negative delta floors at zero
- **WHEN** a negative delta would push the value below zero
- **THEN** it applies unclamped downward only to the floor of 0, and always runs the party auto-leave recheck hook

#### Scenario: Every seed refusal raises a stable AffinitySeedError
- **WHEN** `seed_affinity` refuses a call for any reason
- **THEN** it raises `AffinitySeedError` with a stable reason, writing nothing, so a seed can never be used to launder an interaction gain past the daily budget

#### Scenario: A failed seed write restores the in-process record surface
- **WHEN** a seed write fails inside its transaction
- **THEN** the host's in-process `relations_data` surface is restored

#### Scenario: A committed seed emits one boundary info event
- **WHEN** a seed transaction commits durably
- **THEN** exactly one `affinity_seed` boundary info event is emitted at the outermost durable commit
- **AND** the seed consumed no daily budget, resolved no source, and ran no auto-leave recheck, because a seed establishes a starting relationship that no interaction produced

### Requirement: Deterministic gains apply at talk, trade, and guild success paths
A known-keyword talk answer SHALL grant +1 affinity (`talk` source) with the host NPC, a
successful buy or sell SHALL grant +1 (`trade` source) with the local Merchant host, and
successful guild registration, board acceptance, and examination start SHALL each grant +1
(`guild` source) with the respective host. Every gain SHALL be applied through the sole-writer
API inside the host operation's all-or-nothing commit, so a failing or rejected host operation
grants nothing.

#### Scenario: Keyword talk grants affinity and unknown keywords grant nothing
- **WHEN** the player talks to a scripted-dialogue host with a known keyword and then with an
  unknown keyword
- **THEN** the known-keyword answer raises the host's value by 1 and the unknown keyword changes
  nothing

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

#### Scenario: The talk writer commits keyword resolution and gain atomically
- **WHEN** the deterministic talk writer processes a known keyword
- **THEN** it resolves the keyword and applies the affinity gain in one transaction with cache restoration on failure

#### Scenario: Unknown and no-keyword talk paths grant nothing
- **WHEN** the player talks with an unknown keyword, or with no keyword at all
- **THEN** no affinity is granted on either path

#### Scenario: Service hosts are NPC instances that always carry their gain
- **WHEN** an operation's service host is inspected for affinity capacity
- **THEN** hosts SHALL be NPC instances: a host that cannot hold affinity is rejected before any write, so a successful operation always carries its gain

### Requirement: The party auto-leave recheck hook runs after negative affinity deltas
The sole-writer API SHALL invoke the party auto-leave recheck after every negative delta. The hook
SHALL be the wired rule from `party-core`: when the NPC is a bound companion and its affinity
toward the player drops below the invite threshold (70), it SHALL call
`world/rules/party.py::leave_party(npc, player, reason="affinity_below_threshold")` as part of the
affinity write's transaction.

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

#### Scenario: The writer returns the notification line but never sends it
- **WHEN** an auto-leave fires during a negative-delta write
- **THEN** the write API returns the auto-leave notification line, which the caller SHALL send to the player only after its own transaction commits — the writer never sends it

#### Scenario: A drop that stays at or above the threshold keeps the party
- **WHEN** a bound companion's affinity drops by a negative delta but stays at or above 70
- **THEN** the party is not ended

#### Scenario: The hook is deterministic
- **WHEN** the same negative delta and companion state are replayed
- **THEN** the hook produces the same recheck outcome, and it is side-effect free for non-companions

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
