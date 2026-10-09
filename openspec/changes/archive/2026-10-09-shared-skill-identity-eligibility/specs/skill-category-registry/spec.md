# Spec Delta

## MODIFIED Requirements

### Requirement: Classifying a skill changes no other field
Assigning `category`/`group` to any `SKILL_REGISTRY` entry SHALL NOT change that entry's `kind`,
`cost`, `effects`, `element`, `target_spec`, or `faction_constraint` from their values before this
requirement's classification was introduced. The Phase B re-homing of the five acquired-passive keys
and `flee` SHALL likewise change only `category`/`group`. The `holy_rite` re-classification of the
fifteen church-block ACTIVE rows SHALL likewise change only `category`.

#### Scenario: divine_sexual_arts keeps its mechanics after reclassification
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"]` is inspected after classification
- **THEN** required race capabilities contain `can_use_divine_arts`, `effects` equals `["sexual_event_target:stimulus_applied"]`,
  and `kind`, `cost`, `target_spec` are unchanged from their pre-classification values, while
  `category` is `SEXUAL_ACT` and `group` is `"神之秘法"`

#### Scenario: A re-homed acquired passive keeps its mechanics
- **WHEN** `SKILL_REGISTRY["flight"]` and `SKILL_REGISTRY["reincarnation_boon_yuka"]` are inspected after Phase B re-homing
- **THEN** `flight` keeps `kind=PASSIVE`, `cost={"mp": 22}`, `effects=["movement:flight"]` and its wind `element`; `reincarnation_boon_yuka` keeps `kind=PASSIVE` and `effects=["combat_prediction:武感"]`; only `category`/`group` differ from their pre-Phase-B values

#### Scenario: An elemental spell's element field is unaffected by its group assignment
- **WHEN** any `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** its `element` field's key equals its `group` value, and its `effects` are unchanged from their pre-classification values

#### Scenario: A moved church rite keeps every other field
- **WHEN** `SKILL_REGISTRY["rite_lamb_mark"]`, `SKILL_REGISTRY["rite_martyrdom_vow"]`, and
  `SKILL_REGISTRY["rite_morning_devotion"]` are inspected after the holy_rite re-classification
- **THEN** the first two keep `effects=["self_buff_apply:lamb_seal"]` and
  `effects=["session_stamp:martyr_key"]` respectively, all three keep their `kind`, `cost`,
  `element`, and `target_spec`, and each now carries `category` `HOLY_RITE` with `group` `None`

#### Scenario: The divine_sexual_arts effects pin tracks one authorised rewrite
- **WHEN** `divine_sexual_arts`' `effects` pin is compared to its pre-classification value
- **THEN** the difference is the one authorised post-classification rewrite made by
  `integrate-divine-sexual-arts-catalog` (the `sexual_event:` → `sexual_event_target:` prefix
  migration of the same declared event); no other field of that entry changed

#### Scenario: Series D rows keep their group through re-classification
- **WHEN** the fifteen church-block ACTIVE rows are re-classified to `holy_rite`
- **THEN** the four Series D rows keep their `group="聖禮"` untouched

#### Scenario: Church rows stay on the same rails
- **WHEN** the holy_rite re-classification lands
- **THEN** in particular `rite_morning_devotion` keeps `kind=ACTIVE` and every row keeps its exact
  `effects` value (the same two referenced rows, every other row the same declaration it carried),
  because cast mechanics are a separate change's work

