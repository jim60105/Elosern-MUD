# Spec Delta

## MODIFIED Requirements

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
- **WHEN** the ladder deviates from the canonical floor sequence ;  a wrong stage count, non-increasing floors, or a floor outside the canonical set 0/10/30/50/70/90/100
- **THEN** loading rejects it with a named validation error before any write

#### Scenario: The same YAML carries the tuning values
- **WHEN** `rulebook/affinity.yaml` is read for its non-ladder settings
- **THEN** it carries the offline party-invite threshold (70, preserving the canonical 羈絆 entitlement), the authored positive daily interaction cap, and the authored positive quest-completion gain

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
- **WHEN** a fixed synthetic rulebook cap of 5 has been exhausted in one world day and a sixth capped gain is attempted
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
- **THEN** they draw from the remaining daily budget ;  the authored daily cap shared across `talk`, `trade`, `guild`, and `ai_dialogue` ;  while `quest_completion` deltas bypass the cap

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

#### Scenario: Production daily cap remains author-adjustable
- **WHEN** a valid daily budget or quest gain is edited
- **THEN** schema and integration checks consume the new declaration unchanged; fixed synthetic budgeting/rollback tests remain independent

