# Spec Delta

## ADDED Requirements

### Requirement: Recovery food is an out-of-combat consumable
Food with an authored recovery profile SHALL use the ordinary inventory item action. A committed use SHALL apply the authored HP, MP, and/or SP recovery to the acting character under the ordinary gauge caps and consume one serving. Combat SHALL refuse the use without applying recovery or consuming a serving.

#### Scenario: Eat a serving with two recovery effects
- **WHEN** a character missing HP and SP uses a serving that restores both outside combat and the use commits
- **THEN** each gauge gains its authored amount up to its cap and the inventory loses exactly one serving

#### Scenario: Attempt to eat during combat
- **WHEN** a combat participant attempts to use recovery food
- **THEN** the use is refused without consuming the serving or applying its effects
