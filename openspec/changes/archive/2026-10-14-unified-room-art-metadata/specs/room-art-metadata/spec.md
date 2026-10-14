# Spec Delta

## Purpose

Define authored per-place official artwork metadata and stable logical scene identity across permanent, instance and pooled wilderness room construction.

## ADDED Requirements

### Requirement: Room official references are explicit authored keys
Supported authored rooms and explicitly declared instances SHALL carry optional registered room_art_key metadata synchronized by the map owner. Keys SHALL NOT be inferred from names, ObjectDB ids, threat tiers or nearby rooms. Dynamic rooms without declarations SHALL use their archetype chain without new generation.

#### Scenario: Permanent interior metadata converges
- **WHEN** startup runs twice for an authored permanent interior
- **THEN** its valid scene archetype and declared optional artwork key converge without duplicate rooms or inferred keys

#### Scenario: Instance accepts an explicit key
- **WHEN** a supported instance declaration supplies a registered key
- **THEN** construction preserves that key; undeclared instances have none

### Requirement: Pooled wilderness describes the active logical place
Every wilderness preparation SHALL derive scene metadata and identity from its current wilderness and coordinates, and clear any preceding place's artwork key when absent. Scene identity SHALL distinguish logical places even when they share a pooled room object or archetype.

#### Scenario: Same object moves to another coordinate
- **WHEN** one pooled object is prepared for declared place A then undeclared place B
- **THEN** B has its own coordinate identity, valid archetype and no A artwork key

#### Scenario: Region keys do not masquerade as archetypes
- **WHEN** a wilderness region is prepared
- **THEN** its authored art mapping supplies a registered scene archetype while its region identity/terrain behavior remains unchanged

