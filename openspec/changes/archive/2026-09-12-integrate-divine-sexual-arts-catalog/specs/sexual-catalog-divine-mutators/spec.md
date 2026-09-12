## MODIFIED Requirements

### Requirement: Four hand-built acts extend DIVINE_ACTS, gated exclusively by requires_divine_arts, with no counter unlock
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL carry the four 後期 hand-built pairs
(感度創世 `divine_sensitivity_creation`, 恥辱剝奪 `divine_shame_deprivation`, 絕對從屬
`divine_absolute_submission`, 無垢回歸 `divine_purity_restoration`) — each a hand-built `(SkillDef,
SexualActDef)` pair declaring `requires_divine_arts=True`, `unlock={}`, `target_part=None`,
`resistible=True`, no counters, `actor_pleasure_ratio=0.0`, and exactly one new `divine_` effect
prefix — extending the tuple to the seven-entry line (the first three pairs unchanged in every
field). The tuple SHALL reach exactly eight entries only through the `integrate-divine-sexual-arts-
catalog` integration's eighth pair (`divine_sexual_arts`, `ownership_gated=True`), pinned by the
`sexual-act-registry` capability's eighth-row requirement: the four 後期 acts' fields and the first
seven pairs' ordering SHALL NOT change when the eighth pair lands.

#### Scenario: The four 後期 acts are registered in divine.py
- **WHEN** `DIVINE_ACTS` keys are collected at runtime
- **THEN** all four 後期 keys are present, and every `DIVINE_ACTS` key begins with `divine_`

#### Scenario: First-three-pair regression passes after the extension
- **WHEN** the 神之秘法 catalogue structural test asserts the first three pairs' full field values
- **THEN** it passes against the extended tuple — the extension changed no earlier pair

#### Scenario: Growth pin after the integration lands
- **WHEN** the extension's registration test asserts the tuple length
- **THEN** it asserts `len(DIVINE_ACTS) == 8` with the eighth pair keyed `divine_sexual_arts`
  appended, while the first seven pairs and their ordering are unchanged

#### Scenario: The four 後期 acts carry no counter gates
- **WHEN** each of the four acts' `SexualActDef.unlock` mapping is inspected
- **THEN** it is empty — counter thresholds do not apply to the 神之秘法 line
