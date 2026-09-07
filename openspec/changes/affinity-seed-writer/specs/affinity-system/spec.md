# affinity-system delta

## MODIFIED Requirements

### Requirement: apply_affinity_change is the sole affinity writer with a source-capped daily budget
`world/rules/affinity.py` SHALL be the only module that writes affinity values, and
`apply_affinity_change(npc, player, source, delta)` SHALL be its only *interaction* writer. The source SHALL be a member of the closed set
(`talk`, `trade`, `guild`, `ai_dialogue`, `quest_completion`, `friendly_fire`, `sexual_forced`); an
unknown source SHALL be rejected without writing. The writer SHALL reject a non-NPC owner without
writing. Before budgeting a capped positive delta it SHALL lazily reset the daily-gain counter when
the record's stored tick differs from the current world day; negative deltas (including
`friendly_fire` and `sexual_forced`) SHALL never reset the counter and never restore spent budget. Positive deltas from the capped sources
SHALL draw from the remaining daily budget (`cap` 5 shared across `talk`, `trade`, `guild`,
`ai_dialogue`); `quest_completion` deltas SHALL bypass the cap. The applied delta SHALL be
`min(requested, remaining_budget, cap - value)`, the daily counter SHALL accrue only the actually
applied increase, and a delta that applies zero SHALL consume no budget. Positive deltas SHALL
clamp to the record's `cap`; negative deltas SHALL apply unclamped downward (floor 0) and always
run the party auto-leave recheck hook. The function SHALL return a structured outcome (applied,
delta used, budget capped) so callers can render feedback.

The same module SHALL additionally expose exactly one *seed* writer,
`seed_affinity(npc, player, value)`, for establishing a starting relationship that no interaction
produced. It SHALL create a fresh record whose value is `value`, whose `cap` is `NATURAL_CAP`, and
whose daily counter is zero stamped with the current world day. It SHALL reject a value outside
`1..NATURAL_CAP` and SHALL refuse to overwrite an existing record for the pair, so it can never be
used to launder an interaction gain past the daily budget. It SHALL NOT consume daily budget,
resolve a source, or run the auto-leave recheck, because a seed is not an interaction. No module
outside `world/rules/affinity.py` SHALL write an affinity record.

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
