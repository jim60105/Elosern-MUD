# Spec Delta

## MODIFIED Requirements

### Requirement: Equipment adjustments render as deterministic prose
The capability SHALL provide one server-side formatter converting a registered item's rulebook entry into one deterministic 正體中文 summary: segments joined by 「｜」 in field-vocabulary declaration order, signed integers, percent fields as `±N%`, gauge fields as `<gauge>上限 ±N`, immunity keys rendered by their registered display names, and zero-valued fields omitted. Every number SHALL come from the rulebook; the formatter SHALL NOT recompute effective values.

#### Scenario: Heavy armor describes its trade-off verbatim
- **WHEN** the formatter renders a synthetic armor entry (atk −2, defense +8, agility −10%, hp cap +15)
- **THEN** the output is exactly 「攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15」

#### Scenario: Immunity-only item
- **WHEN** the formatter renders 無懼胸針's entry (immune `fear` only)
- **THEN** the output contains only the immunity segment with the registered display name and no numeric segments

### Requirement: Effective exposure is a pure clamped read-time overlay

The equipment-effect capability SHALL expose one accessor returning the
entity's effective exposure: the stored `EXPOSURE_LEVELS` ordinal shifted by
the summed `exposure_bias` of worn equipment, clamped to the vocabulary
bounds.

#### Scenario: Vestments lift a nun's exposure two bands

- **WHEN** an actor with stored exposure 中等 wears a synthetic equipment declaration with bias +2
- **THEN** effective exposure is 極高 and the stored trait is untouched

#### Scenario: Bias clamps at both vocabulary ends

- **WHEN** effective exposure is computed for stored 極高 with bias +2, and
  for stored 極低 with a negative-sum hypothetical
- **THEN** the results clamp to 極高 and 極低 respectively without error

#### Scenario: Malformed storage contributes no bias

- **WHEN** the accessor runs against malformed equipment storage
- **THEN** it returns exactly the stored exposure level

#### Scenario: The exposure accessor keeps the purity contract

- **WHEN** the effective-exposure accessor reads the stored level
- **THEN** it reads through one neutral shared reader that imports no rules modules, writes nothing, and materializes no handlers

#### Scenario: A summed pleasure_gain accessor shares the contract

- **WHEN** the capability exposes its summed `pleasure_gain` accessor over worn equipment
- **THEN** it follows the same purity contract and a malformed-yields-zero rule
