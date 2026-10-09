# Spec Delta

## MODIFIED Requirements

### Requirement: Four hand-built acts extend DIVINE_ACTS, gated exclusively by requires_divine_arts, with no counter unlock
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL carry the four 後期 hand-built pairs
(感度創世 `divine_sensitivity_creation`, 恥辱剝奪 `divine_shame_deprivation`, 絕對從屬
`divine_absolute_submission`, 無垢回歸 `divine_purity_restoration`), extending the tuple to the
seven-entry line with the first three pairs unchanged in every field.

#### Scenario: A non-divine race cannot cast any of the four acts regardless of counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `False` attempts to cast any of the four
  acts, regardless of that actor's lifetime counter values
- **THEN** `the shared identity-eligibility gate` rejects the cast with the named identity-eligibility rejection

#### Scenario: The four 後期 acts are registered in divine.py
- **WHEN** `DIVINE_ACTS` keys are collected at runtime
- **THEN** all four 後期 keys are present, and every `DIVINE_ACTS` key begins with `divine_`

#### Scenario: First-three-pair regression passes after the extension
- **WHEN** the 神之秘法 catalogue structural test asserts the first three pairs' full field values
- **THEN** it passes against the extended tuple; the extension changed no earlier pair

#### Scenario: Growth pin after the integration lands
- **WHEN** the extension's registration test asserts the tuple length
- **THEN** it asserts `len(DIVINE_ACTS) == 8` with the eighth pair keyed `divine_sexual_arts`
  appended, while the first seven pairs and their ordering are unchanged

#### Scenario: The four 後期 acts carry no counter gates
- **WHEN** each of the four acts' `SexualActDef.unlock` mapping is inspected
- **THEN** it is empty; counter thresholds do not apply to the 神之秘法 line

#### Scenario: Each 後期 pair declares the line's fixed field set
- **WHEN** each of the four 後期 pairs is inspected
- **THEN** each is a hand-built `(SkillDef, SexualActDef)` pair declaring the shared eligibility requirement for race capability `can_use_divine_arts`,
  `unlock={}`, `target_part=None`, `resistible=True`, no counters, `actor_pleasure_ratio=0.0`, and
  exactly one new `divine_` effect prefix

#### Scenario: The eighth entry arrives only via the integration pair
- **WHEN** `DIVINE_ACTS` reaches exactly eight entries
- **THEN** it is only through the `integrate-divine-sexual-arts-catalog` integration's eighth pair
  (`divine_sexual_arts`, `ownership_gated=True`), pinned by the `sexual-act-registry` capability's
  eighth-row requirement

#### Scenario: The eighth pair landing perturbs nothing earlier
- **WHEN** the eighth pair lands
- **THEN** the four 後期 acts' fields and the first seven pairs' ordering SHALL NOT change

### Requirement: The four new effect prefixes are line-agnostic dispatch-table entries
`action.py`'s `_EFFECT_HANDLERS` SHALL register `divine_saturate_sensitivity:`, `divine_clamp_shame:`,
`divine_mark_submission:`, and `divine_restore_purity:` as ordinary prefixes. No handler SHALL read
the calling skill's identity eligibility or otherwise branch on the calling `SkillDef`'s line.

#### Scenario: A hypothetical non-divine SkillDef naming one of the four prefixes is handled identically
- **WHEN** a hypothetical `SkillDef` outside the 神之秘法 line declares
  `effects=["divine_mark_submission:test"]` and is cast
- **THEN** the handler calls `mark_submission` on its resolved target exactly as it would for
  `絕對從屬`, without rejecting the cast for having no required divine race capability

