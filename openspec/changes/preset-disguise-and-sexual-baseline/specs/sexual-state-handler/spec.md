# sexual-state-handler delta

## MODIFIED Requirements

### Requirement: SexualState is constructed from entity.db.sexual when a raw baseline is present
When `entity.db.sexual` is a populated dict, `SexualState`'s construction
SHALL derive every field's initial value from that dict, defaulting any optional field the dict omits
(`wetness`, `shame`, `exposure`, `climax_phase`) to its vocabulary's first (lowest) level. Two
production paths SHALL produce that dict: the character import loader, and preset activation in
`world/rules/character_creation.py` when the selected preset declares a `sexual_baseline`. A preset
declaring no baseline SHALL leave the attribute absent, so the existing default-construction rules
apply unchanged.

#### Scenario: A fully-specified baseline is used verbatim
- **WHEN** `entity.db.sexual` is `{"arousal": "微興奮", "virgin": true, "sensitivity": {}}`
- **THEN** the constructed `entity.sexual.arousal.level` equals `"微興奮"` and `entity.sexual.virgin`
  is `True`

#### Scenario: An omitted optional field defaults to its vocabulary's lowest level
- **WHEN** `entity.db.sexual` omits `wetness` entirely
- **THEN** the constructed `entity.sexual.wetness.level` equals `"乾燥"` (`WETNESS_LEVELS[0]`)

#### Scenario: A preset-declared baseline reaches the handler
- **WHEN** a character is activated from a preset declaring a `sexual_baseline` and its `entity.sexual` is first constructed
- **THEN** every field derives from the preset's declared record rather than from the generic default baseline
