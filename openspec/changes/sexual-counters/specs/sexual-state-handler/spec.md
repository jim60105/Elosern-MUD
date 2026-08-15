## ADDED Requirements

### Requirement: SexualState exposes eleven independent, unbounded, lifetime behaviour counters, each with exactly one sanctioned mutator
`SexualState` SHALL expose exactly the eleven counter fields below, each an unbounded (`min=0`, no
`max`) counter starting at `0` for every entity regardless of any imported baseline, each readable
through its own property, and each mutable **only** through its own named method, which SHALL
increment it by exactly `1`. No rule, effect handler, or other caller SHALL be able to increment,
decrement, or reset any of the eleven through any path other than its named mutator. None of the
eleven SHALL be reset by `reset_daily_counters()`.

| Field | Mutator |
|---|---|
| `masturbation_count` | `record_masturbation()` |
| `toy_use_count` | `record_toy_use()` |
| `exposure_act_count` | `record_exposure_act()` |
| `watched_count` | `record_watched()` |
| `duo_act_count` | `record_duo_act()` |
| `group_act_count` | `record_group_act()` |
| `hostile_act_count` | `record_hostile_act()` |
| `restraint_count` | `record_restraint()` |
| `interspecies_act_count` | `record_interspecies_act()` |
| `climax_count` | `record_climax_count()` |
| `climax_extension_count` | `record_climax_extension()` |

#### Scenario: Every counter starts at zero regardless of baseline
- **WHEN** `entity.sexual` is read for the first time on any entity, imported or not, `Monster` or
  not
- **THEN** all eleven counter properties above equal `0`

#### Scenario: A mutator increments only its own counter by exactly one
- **WHEN** `entity.sexual.record_masturbation()` is called once
- **THEN** `entity.sexual.masturbation_count` equals `1`, and every one of the other ten counters is
  unchanged

#### Scenario: Repeated calls accumulate linearly
- **WHEN** `entity.sexual.record_hostile_act()` is called five times in sequence
- **THEN** `entity.sexual.hostile_act_count` equals exactly `5`

#### Scenario: No counter is reset by reset_daily_counters
- **WHEN** `reset_daily_counters(entity)` is called on an entity whose `climax_count` is `3` and
  whose `restraint_count` is `7`
- **THEN** `entity.sexual.climax_count` remains `3` and `entity.sexual.restraint_count` remains `7`
  afterward — only `climax_today` (unchanged by this capability) is affected

#### Scenario: climax_count is independent of the existing daily climax_today counter
- **WHEN** `entity.sexual.record_climax()` (the existing, unmodified mutator) is called, without also
  calling `entity.sexual.record_climax_count()`
- **THEN** `entity.sexual.climax_today` increases as it already did before this capability, and
  `entity.sexual.climax_count` is unaffected — the two counters are mutated independently, and no
  call to either mutator has a side effect on the other's field

#### Scenario: No counter is reachable through SexualState's private TraitHandler
- **WHEN** any module outside `world/rules/sexual_state.py` is inspected
- **THEN** no line references `entity.sexual._traits` (or any other leading-underscore attribute of
  `SexualState`) to read or write any of the eleven counters — every access goes through the named
  property or mutator
