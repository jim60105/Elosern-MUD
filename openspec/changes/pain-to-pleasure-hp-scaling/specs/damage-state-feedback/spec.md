## MODIFIED Requirements

### Requirement: Damage feedback follows actual loss and newly accepted negative instances
A qualified passive SHALL react once to each positive actual HP loss and each newly accepted negative buff instance, using an authored gain proportional to the harm actually suffered, applied through the canonical state writer. For an HP-loss event the gain SHALL be derived from the ratio of that event's actual loss to the recipient's maximum HP, scaled by the table's authored coefficient and floored to a whole number. For a newly accepted negative buff instance, which carries no HP loss, the gain SHALL be the same derivation applied to an authored flat fraction of maximum HP. Spell, item, rulebook and periodic-damage sources SHALL share this behavior and SHALL be priced identically for an identical loss: the source's tier, school and spell-or-not nature SHALL NOT affect the gain. A recipient whose maximum HP is unreadable or not positive SHALL produce no gain rather than a guessed one. Misses, zero loss, healing, resource costs, immunity and instance refresh SHALL not trigger.

The retired source-tier gain mapping SHALL NOT be loadable: a `pleasure_gain` authored as a tier-keyed mapping SHALL fail closed at rule load naming the rule id. Source tier SHALL retain every other role it has, including capture at application for periodic effects and grant-time attribution for source-targeted actions.

#### Scenario: Different damage sources share the reaction
- **WHEN** a synthetic passive owner suffers direct spell, item and periodic damage of equal actual loss
- **THEN** each actual loss causes the configured gain exactly once, and all three gains are equal because the gain reads the loss rather than the source

#### Scenario: A larger loss is worth proportionally more
- **WHEN** a synthetic passive owner suffers one loss of a tenth of maximum HP and, separately, one loss of half of maximum HP
- **THEN** the second gain is five times the first

#### Scenario: A full journey costs half of maximum HP
- **WHEN** a synthetic passive owner at the post-climax baseline suffers cumulative losses totalling half of maximum HP
- **THEN** the accumulated gain reaches the threshold band that opens the climax gate

#### Scenario: A no-loss negative instance uses the flat fraction
- **WHEN** a synthetic passive owner newly accepts a negative buff instance that inflicts no HP loss
- **THEN** the gain equals the authored flat fraction of maximum HP, and is smaller than the gain from a loss of a tenth of maximum HP

#### Scenario: An unreadable maximum produces no gain
- **WHEN** a synthetic passive owner whose maximum HP is unreadable or not positive suffers an actual loss
- **THEN** no gain is applied and no state write occurs

#### Scenario: A tier-keyed gain mapping fails at load
- **WHEN** a rule authors `pleasure_gain` as a source-tier-keyed mapping
- **THEN** rule loading raises naming that rule id

#### Scenario: Immune and refresh outcomes do not count
- **WHEN** a negative buff is refused by immunity or only refreshes an existing instance
- **THEN** there is no new-instance feedback

#### Scenario: New debuff and its ticks are distinct
- **WHEN** a new damaging debuff is accepted and later ticks twice
- **THEN** the new-instance event and each positive-loss tick independently trigger once
