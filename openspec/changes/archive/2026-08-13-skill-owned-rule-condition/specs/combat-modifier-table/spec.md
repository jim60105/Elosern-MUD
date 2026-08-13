## ADDED Requirements

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
