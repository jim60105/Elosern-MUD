## ADDED Requirements

### Requirement: Spell cost labels include a sixth tier with deterministic column precedence
Elemental spell cost classification SHALL include 神格 with single/direct costs 180 through 220 and area/strong costs 200 through 260, inclusive. It SHALL search all ascending tiers in the target-shape column before the opposite column. Labels SHALL NOT grant ownership, impose a race restriction, or introduce a numeric cast gate. Costs outside every band SHALL fail closed.

#### Scenario: Overlap honors shape
- **WHEN** synthetic SINGLE and AREA spells each cost 180 MP
- **THEN** SINGLE classifies as 神格 and AREA as 主宰

#### Scenario: Sixth band accepts boundaries
- **WHEN** synthetic AREA spells cost 200, 240 or 260 MP
- **THEN** each classifies as 神格 without dependence on caster race or stats

#### Scenario: Out of all bands stays invalid
- **WHEN** a synthetic elemental spell has a positive cost outside both columns of all tiers
- **THEN** classification rejects it instead of inventing a tier or silently omitting the label
