## MODIFIED Requirements

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
