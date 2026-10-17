# Spec Delta

## ADDED Requirements

### Requirement: Field cast and item use advances settle the present party
Every successful out-of-combat field cast or item use SHALL settle its command-time advance over the present party scope of its acting character, so gauge regeneration and buff expiry reach every co-located member once.

#### Scenario: A field heal settles the whole present party
- **WHEN** the commander casts a field heal out of combat with companions 艾拉 and 卡恩 present
- **THEN** the one command-time advance settles the commander, 艾拉 and 卡恩

#### Scenario: A rejected field action settles nobody
- **WHEN** an out-of-combat item use is rejected in preflight
- **THEN** no member's gauges, buffs or booking change and the tick is unchanged
