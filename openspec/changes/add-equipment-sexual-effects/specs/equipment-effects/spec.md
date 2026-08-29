## ADDED Requirements

### Requirement: Effective exposure is a pure clamped read-time overlay

The equipment-effect capability SHALL expose one accessor returning the
entity's effective exposure: the stored `EXPOSURE_LEVELS` ordinal shifted by
the summed `exposure_bias` of worn equipment, clamped to the vocabulary
bounds. It SHALL read the stored level through one neutral shared reader
(that imports no rules modules), SHALL write nothing, SHALL materialize no
handlers, and malformed equipment storage SHALL contribute zero bias. The
capability SHALL also expose one pure summed `pleasure_gain` accessor over
worn equipment with the same purity contract and a malformed-yields-zero
rule.

#### Scenario: Vestments lift a nun's exposure two bands

- **WHEN** an actor with stored exposure 中等 wears 圣女聖袍 (bias +2)
- **THEN** effective exposure is 極高 and the stored trait is untouched

#### Scenario: Bias clamps at both vocabulary ends

- **WHEN** effective exposure is computed for stored 極高 with bias +2, and
  for stored 極低 with a negative-sum hypothetical
- **THEN** the results clamp to 極高 and 極低 respectively without error

#### Scenario: Malformed storage contributes no bias

- **WHEN** the accessor runs against malformed equipment storage
- **THEN** it returns exactly the stored exposure level
