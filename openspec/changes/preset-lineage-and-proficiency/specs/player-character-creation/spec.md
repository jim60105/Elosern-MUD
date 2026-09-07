# player-character-creation delta

## MODIFIED Requirements

### Requirement: Preset activation grants the preset's declared skill kit
Preset mode SHALL additionally grant the selected preset's declared skill kit: every active key
SHALL be persisted into the character's `skills.active` and every passive key into
`skills.passive`, in the preset's declared order, inside the same all-or-nothing activation
transaction that writes identity, traits, and the remaining initial mechanical state. Activation
SHALL extend each list with the transitive prerequisite closure of the declared keys
(`world/rules/progression.py::lineage_ownership_closure`), appending closure-added keys after the
declared ones so the declared order is preserved, and SHALL seed
`skill_proficiency` over the closed set through
`world/rules/progression.py::seed_lineage_proficiency`, so a preset kit arrives gate-usable rather
than owning a tip skill whose `can_use_skill` predicate fails. A preset MAY declare its own
`skill_proficiency` as a tuple of `(skill_key, xp)` pairs, and a declared entry SHALL always win
over a seeded value, even when it leaves an edge unmet — the same precedence an explicit import
record entry has. Custom mode
SHALL grant no skills beyond the universal innate set (`basic_attack`, `flee`). A preset kit SHALL
reference only keys that exist in `SKILL_REGISTRY` with the matching `SkillKind` (active keys
`SkillKind.ACTIVE`, passive keys `SkillKind.PASSIVE`), and a preset SHALL NOT declare a
`requires_divine_arts` skill unless its race `can_use_divine_arts` — an invalid kit SHALL fail at
registry load, never at player activation. Every declared `skill_proficiency` key SHALL likewise
resolve in `SKILL_REGISTRY` with a non-negative numeric value and no repeated key, validated at
registry load. No player-facing surface (the Telnet preset preview or
the WebClient preset card) SHALL expose the kit; the card contract and the `creation.preset` action
payload are unchanged.

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
  `SkillKind` is `PASSIVE` (or vice versa), or a `requires_divine_arts` skill on a race without
  `can_use_divine_arts`
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

#### Scenario: An invalid declared proficiency is rejected at load
- **WHEN** a preset declares a `skill_proficiency` key absent from `SKILL_REGISTRY`, a negative or
  non-numeric value, or the same key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid entry can never reach a
  player's activation
