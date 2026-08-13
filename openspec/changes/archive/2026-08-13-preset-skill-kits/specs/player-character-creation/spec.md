## ADDED Requirements

### Requirement: Preset activation grants the preset's declared skill kit
Preset mode SHALL additionally grant the selected preset's declared skill kit: every active key
SHALL be persisted into the character's `skills.active` and every passive key into
`skills.passive`, in the preset's declared order, inside the same all-or-nothing activation
transaction that writes identity, traits, and the remaining initial mechanical state. Custom mode
SHALL grant no skills beyond the universal innate set (`basic_attack`, `flee`). A preset kit SHALL
reference only keys that exist in `SKILL_REGISTRY` with the matching `SkillKind` (active keys
`SkillKind.ACTIVE`, passive keys `SkillKind.PASSIVE`), and a preset SHALL NOT declare a
`requires_divine_arts` skill unless its race `can_use_divine_arts` — an invalid kit SHALL fail at
registry load, never at player activation. No player-facing surface (the Telnet preset preview or
the WebClient preset card) SHALL expose the kit; the card contract and the `creation.preset` action
payload are unchanged.

#### Scenario: A preset activation persists the preset's skill kit
- **WHEN** a pending player activates a shipped preset that declares `active_skills` and
  `passive_skills`
- **THEN** the activated character's `db.skills` equals `{"active": [<declared active keys in
  order>], "passive": [<declared passive keys in order>]}` written atomically with the activation,
  and the preset's `creation_draft`, if any, is cleared in the same transaction

#### Scenario: Custom activation starts with innate skills only
- **WHEN** a pending player completes the custom creation flow
- **THEN** the activated character's `db.skills` is `{"active": [], "passive": []}`, so its only
  skills are the universal innate set

#### Scenario: A preset kit with a registry-invalid skill is rejected at load
- **WHEN** a preset declares a skill key absent from `SKILL_REGISTRY`, an active key whose registry
  `SkillKind` is `PASSIVE` (or vice versa), or a `requires_divine_arts` skill on a race without
  `can_use_divine_arts`
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation
