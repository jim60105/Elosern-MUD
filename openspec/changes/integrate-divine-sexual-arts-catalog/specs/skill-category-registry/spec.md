## MODIFIED Requirements

### Requirement: Classifying a skill changes no other field
Assigning `category`/`group` to any `SKILL_REGISTRY` entry SHALL NOT change that entry's `kind`,
`cost`, `effects`, `element`, `target_spec`, or `faction_constraint` from their values before this
requirement's classification was introduced. The `effects` pin for `divine_sexual_arts` tracks the
one authorised post-classification rewrite made by `integrate-divine-sexual-arts-catalog` (the
`sexual_event:` → `sexual_event_target:` prefix migration of the same declared event); no other
field of that entry changed.

#### Scenario: divine_sexual_arts keeps its mechanics after reclassification
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"]` is inspected after classification
- **THEN** `requires_divine_arts` is `True`, `effects` equals `["sexual_event_target:stimulus_applied"]`,
  and `kind`, `cost`, `target_spec` are unchanged from their pre-classification values, while
  `category` is `SEXUAL_ACT` and `group` is `"神之秘法"`

#### Scenario: An elemental spell's element field is unaffected by its group assignment
- **WHEN** any `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** its `element` field's key equals its `group` value, and its `effects` are unchanged from
  their pre-classification values
