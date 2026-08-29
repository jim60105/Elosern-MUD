## ADDED Requirements

### Requirement: Equipment immunity predicate is pure and fail-closed

The equipment-effect capability SHALL expose one predicate returning the
union of `immune` keys over the entity's currently worn equipment. It SHALL
read stored state without materializing handlers, SHALL write nothing, and
malformed equipment storage SHALL yield no immunities at all (fail-closed:
broken storage never grants protection).

#### Scenario: Worn pendant grants poison immunity

- **WHEN** an actor wearing 淨化吊墜 is queried for immune buff keys
- **THEN** the result contains `poisoned` and nothing was written

#### Scenario: Malformed storage grants nothing

- **WHEN** the predicate runs against malformed equipment storage
- **THEN** it returns an empty set

### Requirement: Equipment adjustments render as deterministic prose

The capability SHALL provide one server-side formatter converting a
registered item's rulebook entry into one deterministic 正體中文 summary:
segments joined by 「｜」 in field-vocabulary declaration order, signed
integers, percent fields as `±N%`, gauge fields as `<gauge>上限 ±N`,
immunity keys rendered by their registered display names, and zero-valued
fields omitted. Every number SHALL come from the rulebook; the formatter
SHALL NOT recompute effective values.

#### Scenario: Heavy armor describes its trade-off verbatim

- **WHEN** the formatter renders 騎士全套板甲's entry (atk −2, defense +8,
  agility −10%, hp cap +15)
- **THEN** the output is exactly
  「攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15」

#### Scenario: Immunity-only item

- **WHEN** the formatter renders 無懼胸針's entry (immune `fear` only)
- **THEN** the output contains only the immunity segment with the registered
  display name and no numeric segments
