## ADDED Requirements

### Requirement: buffs.yaml entries declare a polarity, defaulting to buff
Each entry in `world/rules/rulebook/buffs.yaml` MAY declare `polarity: debuff`; when absent, polarity
SHALL default to `buff`. `poisoned`, `paralysis`, and `fear` SHALL declare `polarity: debuff`.

#### Scenario: The three existing hostile buffs are classified as debuffs
- **WHEN** `buffs.yaml` is loaded
- **THEN** `poisoned`, `paralysis`, and `fear` each resolve to `polarity == "debuff"`

#### Scenario: A buff with no polarity field defaults to buff
- **WHEN** `focus` (which declares no `polarity` field) is loaded
- **THEN** it resolves to `polarity == "buff"`

### Requirement: cleanse:status removes every active debuff-polarity buff from the target
`world/rules/buffs.py` SHALL register a `cleanse` effect handler via `register_effect_handler`,
resolving `cleanse:status` by calling `entity.buffs.remove()` for every currently-active buff on the
target whose `buffs.yaml` definition has `polarity == "debuff"`. Buffs with `polarity == "buff"` SHALL
NOT be removed.

#### Scenario: Cleansing removes an active debuff
- **WHEN** a `cleanse:status` effect resolves against a target with an active `poisoned` buff
- **THEN** the target no longer has `poisoned` active afterward

#### Scenario: Cleansing does not remove a beneficial buff
- **WHEN** a `cleanse:status` effect resolves against a target with an active `focus` buff and no
  active debuffs
- **THEN** `focus` remains active afterward
