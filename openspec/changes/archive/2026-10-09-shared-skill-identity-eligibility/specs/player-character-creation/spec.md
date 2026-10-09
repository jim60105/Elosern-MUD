# Spec Delta

## MODIFIED Requirements

### Requirement: Preset activation grants the preset's declared skill kit
Preset mode SHALL additionally grant the selected preset's declared skill kit: every active key
SHALL be persisted into the character's `skills.active` and every passive key into
`skills.passive`, in the preset's declared order, inside the same all-or-nothing activation
transaction that writes identity, traits, and the remaining initial mechanical state.

#### Scenario: A preset activation persists the preset's skill kit
- **WHEN** a pending player activates a shipped preset that declares `active_skills` and
  `passive_skills`
- **THEN** the activated character's `db.skills` holds the declared active keys in declared order
  followed by any closure-added active keys, and the declared passive keys in declared order
  followed by any closure-added passive keys, written atomically with the activation, and the
  preset's `creation_draft`, if any, is cleared in the same transaction

#### Scenario: A deep preset kit arrives gate-usable
- **WHEN** a preset declares a skill whose prerequisite edge is unsatisfied by any declared key
- **THEN** the activated character owns the closed chain, the prerequisite's seeded proficiency is
  exactly the required value and never above, and `can_use_skill` passes for the declared skill

#### Scenario: A declared proficiency beats the auto-seed
- **WHEN** a preset declares a `skill_proficiency` entry below the value the seed would write for
  the same key
- **THEN** the activated character's stored proficiency is the declared value and the seed does not
  overwrite it

#### Scenario: Custom activation starts with innate skills only
- **WHEN** a pending player completes the custom creation flow
- **THEN** the activated character's `db.skills` is `{"active": [], "passive": []}`, so its only
  skills are the universal innate set, and its `skill_proficiency` is empty

#### Scenario: A preset kit with a registry-invalid skill is rejected at load
- **WHEN** a preset declares a skill key absent from `SKILL_REGISTRY`, an active key whose registry
  `SkillKind` is `PASSIVE` (or vice versa), or any skill whose shared eligibility rejects the preset's actor kind or race/subrace identity
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

#### Scenario: An invalid declared proficiency is rejected at load
- **WHEN** a preset declares a `skill_proficiency` key absent from `SKILL_REGISTRY`, a negative or
  non-numeric value, or the same key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid entry can never reach a
  player's activation

#### Scenario: Closure extension runs through the lineage ownership closure
- **WHEN** activation extends each declared skill list with the transitive prerequisite closure of the declared keys
- **THEN** it uses `world/rules/progression.py::lineage_ownership_closure`, appending closure-added keys after the declared ones so the declared order is preserved

#### Scenario: Proficiency is seeded over the closed set
- **WHEN** activation seeds `skill_proficiency` over the closed skill set
- **THEN** it does so through `world/rules/progression.py::seed_lineage_proficiency`, so a preset kit arrives gate-usable rather than owning a tip skill whose `can_use_skill` predicate fails

#### Scenario: A preset may declare explicit proficiency pairs
- **WHEN** a preset declares its own `skill_proficiency` as a tuple of `(skill_key, xp)` pairs
- **THEN** a declared entry SHALL always win over a seeded value, even when it leaves an edge unmet; the same precedence an explicit import record entry has

#### Scenario: Custom mode grants only the universal innate skills
- **WHEN** a custom activation completes
- **THEN** the character SHALL have no skills beyond the universal innate set (`basic_attack`, `flee`)

#### Scenario: Kit validation is load-time only
- **WHEN** a preset kit is validated
- **THEN** it SHALL reference only keys that exist in `SKILL_REGISTRY` with the matching `SkillKind` (active keys `SkillKind.ACTIVE`, passive keys `SkillKind.PASSIVE`), a preset SHALL NOT declare a skill ineligible for its actor kind or race/subrace identity, and every declared `skill_proficiency` key SHALL resolve in `SKILL_REGISTRY` with a non-negative numeric value and no repeated key; an invalid kit or entry SHALL fail at registry load, never at player activation

#### Scenario: No player-facing surface exposes the skill kit
- **WHEN** the Telnet preset preview or the WebClient preset card renders a preset
- **THEN** neither surface exposes the kit, and the card contract and the `creation.preset` action payload are unchanged
