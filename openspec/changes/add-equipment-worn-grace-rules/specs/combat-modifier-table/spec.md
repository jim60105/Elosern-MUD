## ADDED Requirements

### Requirement: Equipment-worn conditions match a shared worn-item fact

The rulebook condition vocabulary SHALL include `equipment_worn:
<item_key>` matching iff the entity currently wears that item key. The
worn-item-keys fact SHALL come from one pure stored-equipment read
(malformed storage → empty set, no writes, no handler materialization) and
SHALL be present in the handler context, the no-create context, and the
shared matcher's partial-context defaults, so live resolution, preview,
resist scoring, and presentation all match identically. A context lacking
the fact SHALL fail the condition (fail-closed). `equipment_worn` SHALL
AND-compose with all existing conditions.

#### Scenario: Sister's grace fires while the habit is worn

- **WHEN** an actor wearing 修女聖袍 with arousal 中等 is evaluated for
  combat modifiers
- **THEN** the merged bundle includes `sister_vestment_grace`'s defense +4

#### Scenario: Same rule silent without the item or the arousal

- **WHEN** the arousal is 平靜, or the habit is not worn
- **THEN** no grace adjustment is present

#### Scenario: Preview agrees with resolution

- **WHEN** a grace-wearing actor's modifiers are evaluated through the
  no-create path and rendered through a partial presentation context
- **THEN** both include the same grace adjustment as live resolution

#### Scenario: Malformed equipment confers no grace

- **WHEN** worn-equipment storage is malformed during evaluation
- **THEN** the worn-item fact is empty and no `equipment_worn` rule matches

#### Scenario: Multi-accessory devotion stack merges as declared

- **WHEN** an actor simultaneously wears 聖女聖袍, 光輝聖徽, and 朝聖者銅符
  (within the shipped accessory slot budget) with arousal 高度
- **THEN** the merged bundle carries the combined defense +8 and the
  emblem's heal_gain +10%, and the display layer lists all three matched
  grace rules

#### Scenario: Grace rules carry display labels

- **WHEN** the shipped display-coverage test runs against the rulebook
- **THEN** every authored grace rule has its Traditional-Chinese label and
  severity entry in the status display rulebook
