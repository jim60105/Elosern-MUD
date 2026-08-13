# combat-modifier-table Specification

## Purpose
TBD - created by archiving change buffs-rulebook. Update Purpose after archive.
## Requirements
### Requirement: combat_modifiers.yaml is one table evaluated by one condition engine, with no
special-case branch between buff-origin and sexual-origin rows
`world/rules/rulebook/combat_modifiers.yaml` SHALL contain both buff-presence rules (poison, paralysis,
fear) and sexual-field-threshold rules (arousal, climax phase), and `world/rules/combat_modifiers.py`
SHALL evaluate every rule in the table through the identical `evaluate_condition()` function from
`world/rules/rulebook/schema.py`. No function in `combat_modifiers.py` SHALL contain a conditional
branch that distinguishes a sexual-origin condition from a buff-origin condition.

#### Scenario: The seed table contains both condition origins
- **WHEN** `world/rules/rulebook/combat_modifiers.yaml` is loaded
- **THEN** it contains at least one rule whose `when` uses `buff_active` (e.g. `poison_agility_penalty`,
  `paralysis_locks_actions`, `fear_agility_and_accuracy_penalty`) and at least one rule whose `when`
  uses `field`/`gte`/`equals` against a sexual-state field (e.g.
  `high_arousal_agility_accuracy_penalty`, `climax_in_progress_locks_actions`)

#### Scenario: No source-level branching distinguishes rule origin
- **WHEN** `world/rules/combat_modifiers.py`'s source is inspected
- **THEN** it contains no conditional (e.g. `if rule.id.startswith(...)`, `if "arousal" in rule.when`)
  that special-cases a sexual-origin rule differently from a buff-origin rule when evaluating them

### Requirement: evaluate_combat_modifiers() is a pure query that never writes to entity state
`world/rules/combat_modifiers.py` SHALL provide `evaluate_combat_modifiers(entity)`, returning a merged
adjustment bundle (a `dict` of field name to adjustment) computed by evaluating every rule in
`combat_modifiers.yaml` against a context built from the entity's current state. This function SHALL
NOT assign to `entity.traits`, `entity.buffs`, `entity.db.*`, or any other entity attribute.

#### Scenario: Multiple matching rules merge into one bundle
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity with both `poisoned` and `fear`
  active as buffs
- **THEN** the returned bundle includes both rules' adjustments (an `agility` entry reflecting
  `poison_agility_penalty` and `fear_agility_and_accuracy_penalty` together, and an `accuracy` entry
  from `fear_agility_and_accuracy_penalty`)

#### Scenario: No entity state changes as a result of calling the query
- **WHEN** `evaluate_combat_modifiers(entity)` is called any number of times in sequence on the same
  entity with unchanged buff/sexual state
- **THEN** `entity.traits.<key>.value` for every trait key is unchanged after each call, and
  `entity.buffs`'s active buff set is unchanged after each call

#### Scenario: An entity with no matching rules returns an empty bundle
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity with no active buffs and no
  sexual state present
- **THEN** it returns an empty `dict`, not an error

### Requirement: Sexual-field rules degrade to inert until entity.sexual is real, then self-arm
`world/rules/combat_modifiers.py`'s context-building step SHALL tolerate `entity.sexual` being `None`
(change 3's current placeholder value) by omitting sexual-field context keys entirely, causing every
sexual-field rule in `combat_modifiers.yaml` to evaluate as not-satisfied rather than raising. Once
`entity.sexual` is a real object exposing `arousal`/`climax_phase` (change 7's future contribution),
the same rules SHALL evaluate against its real values with no code change to `combat_modifiers.py`.

#### Scenario: Sexual-field rules never match while entity.sexual is the change-3 placeholder
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.sexual` is `None`
- **THEN** the returned bundle contains no adjustment attributable to `high_arousal_agility_accuracy_
  penalty` or `climax_in_progress_locks_actions`, and no exception is raised

#### Scenario: Sexual-field rules fire once entity.sexual is a real object (self-arming)
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.sexual` exposes
  `arousal` at or above the `高度` threshold
- **THEN** the returned bundle includes `high_arousal_agility_accuracy_penalty`'s adjustment
  (`agility: "-20%"`, `accuracy: -15`)

### Requirement: Every rule ID in combat_modifiers.yaml has exactly one corresponding unit test
For every `Rule.id` present in `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/tests/
test_combat_modifiers.py` SHALL define exactly one test function named `test_rule_<id>`. A regression
test SHALL mechanically verify this correspondence rather than relying on reviewer discipline.

#### Scenario: Every seed rule has a matching test function
- **WHEN** the mechanical correspondence check inspects `combat_modifiers.yaml`'s rule IDs against
  `test_combat_modifiers.py`'s test function names
- **THEN** it finds exactly one `test_rule_<id>` function for each of `poison_agility_penalty`,
  `paralysis_locks_actions`, `fear_agility_and_accuracy_penalty`,
  `high_arousal_agility_accuracy_penalty`, and `climax_in_progress_locks_actions`

#### Scenario: Adding a rule without a matching test fails the correspondence check
- **WHEN** a new rule is added to `combat_modifiers.yaml` with no corresponding `test_rule_<id>`
  function added to `test_combat_modifiers.py`
- **THEN** the mechanical correspondence check fails, naming the rule ID missing a test

### Requirement: skill_owned is a first-class condition alongside buff_active and field thresholds
`world/rules/rulebook/schema.py`'s `evaluate_condition()` SHALL support `{"skill_owned":
"<skill_key>"}`, true when `<skill_key>` appears in `entity.skills.owned_keys()`. This condition SHALL
be evaluated by the same `evaluate_condition()` function as `buff_active` and sexual-field-threshold
conditions, with no special-casing by condition type in `combat_modifiers.py`.

#### Scenario: An owned skill's rule matches
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity whose `entity.skills.owned_keys()`
  includes `"defense_instinct"`
- **THEN** the returned bundle includes the `defense_instinct` row's adjustment

#### Scenario: An unowned skill's rule does not match
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that does not own
  `"defense_instinct"`
- **THEN** the returned bundle does not include that row's adjustment

#### Scenario: skill_owned rows merge with buff-origin and sexual-origin rows identically
- **WHEN** an entity simultaneously owns `defense_instinct`, has the `poisoned` buff active, and has
  high arousal
- **THEN** the returned bundle includes all three rows' adjustments merged together, with no row
  excluded or handled differently because of its condition type

### Requirement: The eight previously-dead passive_buff/combat_prediction skills each grant a real adjustment
`combat_modifiers.yaml` SHALL contain one `skill_owned` row for each of `defense_instinct`,
`blade_art_mastery`, `extreme_endurance`, `magic_circle_comprehension`, `precise_mana_control`,
`retainer_martial_training`, `guardian_instinct`, and `reincarnation_boon_yuka`, each producing a
nonzero adjustment consistent with the skill's Traditional-Chinese flavor description. Each row's
adjustment SHALL surface through the same surfaces as every other combat-modifier row: the merged
bundle returned by `evaluate_combat_modifiers()` and the player-visible WebClient status conditions
(`build_status_read_model()`'s matched-modifier presentation). Row keys that live combat resolution
reads today (`agility`, `accuracy`, `actions_per_turn`) take effect in combat math; the remaining
vocabulary keys (`defense`, `atk_phys`, `sp_cost`, `mp_cost`) are documented bundle/status vocabulary
whose consumption by the deterministic combat/resource math is owned by later changes.

#### Scenario: Every one of the eight skills has a corresponding rule row
- **WHEN** `combat_modifiers.yaml` is loaded
- **THEN** it contains a `skill_owned` rule referencing each of the eight listed skill keys, and none
  of the eight produces an empty/no-op adjustment

#### Scenario: An owned skill's adjustment is player-visible in the status panel
- **WHEN** an entity that owns `defense_instinct` is presented through `build_status_read_model()`
- **THEN** the read model's conditions include the `defense_instinct_defense_bonus` condition carrying
  the row's adjustment as its modifiers

#### Scenario: The no-create preview path evaluates skill_owned rows identically
- **WHEN** an entity that owns `defense_instinct` is evaluated through
  `evaluate_combat_modifiers_no_create()`
- **THEN** the returned bundle includes the same `defense_instinct` row adjustment as
  `evaluate_combat_modifiers()`, and the read creates no persistent attribute or handler state

### Requirement: dual_wield_style grants a combat adjustment while owned
`combat_modifiers.yaml` SHALL contain a `skill_owned` row for `dual_wield_style` producing a nonzero
to-hit and/or damage adjustment, conditioned on actual dual-wielding if the equipment data model
exposes that fact as a queryable condition, or on bare ownership otherwise.

#### Scenario: Owning and dual-wielding grants the adjustment
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that owns `dual_wield_style` and
  (if the equipment check is implemented) has two weapons equipped
- **THEN** the returned bundle includes `dual_wield_style`'s adjustment

#### Scenario: Not owning the skill never grants the adjustment
- **WHEN** `evaluate_combat_modifiers(entity)` is called on an entity that does not own
  `dual_wield_style`
- **THEN** the returned bundle does not include this adjustment, regardless of equipped weapons
