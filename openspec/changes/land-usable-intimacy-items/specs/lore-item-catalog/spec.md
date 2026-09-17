## ADDED Requirements

### Requirement: A usable item's pleasure gain routes through the shared intimacy writer
A usable item declaring a positive pleasure adjustment SHALL settle it through the intimacy system's single shared pleasure writer, so the item's stimulation reaches arousal, wetness, and climax state by the identical path a skill's stimulation does, and the reported amount SHALL be what the gauge actually moved rather than the declared amount. Raising pleasure SHALL require no status definition and no verb beyond the existing gauge adjustment.

#### Scenario: A pleasure gain needs no status vocabulary
- **WHEN** a usable item profile declares a single positive pleasure adjustment scoped to the acting entity
- **THEN** it loads and settles with no status key involved anywhere in the profile

#### Scenario: A device's stimulation drives the same cascade as a skill's
- **WHEN** a usable intimacy device is used by an entity whose pleasure gauge is below its ceiling
- **THEN** the pleasure gauge rises through the shared writer and the arousal-coupled state changes follow, with the applied delta reported as what actually moved

#### Scenario: A device at a full gauge is refused rather than consumed
- **WHEN** a usable intimacy device is used by an entity whose pleasure gauge is already at its ceiling
- **THEN** the use is rejected with the full-gauge reason and the item is not consumed

### Requirement: A non-consuming use settles without spending the item
A usable item may declare that a use does not consume it. Such an item SHALL settle its effects, remain in inventory at the same count, and still incur the ordinary out-of-combat time cost of an item use — that time cost, together with the gauge ceiling that refuses a use with nothing to accomplish, SHALL be the only thing bounding repeated use. A rollback partway through a non-consuming use SHALL restore every surface it touched and SHALL leave the inventory count unchanged.

#### Scenario: A reusable item survives its own use
- **WHEN** an item declared as non-consuming is used successfully out of combat
- **THEN** its effect settles, the item remains in inventory at the same count, and the world clock advances by the standard item-use duration

#### Scenario: A consuming item is spent
- **WHEN** an item declared as consuming is used successfully
- **THEN** exactly one copy is removed from inventory

#### Scenario: A rolled-back reusable use leaves nothing behind
- **WHEN** settlement of a non-consuming use fails partway
- **THEN** every touched gauge, status, and intimate surface is restored and the inventory count is unchanged

### Requirement: An item barred from combat is refused at submission
A usable item declaring that it may not be used in combat SHALL be refused when submitted as a combat action, and the refusal SHALL name the combat restriction rather than a generic failure. No gauge SHALL move and the item SHALL NOT be consumed.

#### Scenario: A combat-barred item cannot be used in a turn
- **WHEN** an item declaring no combat use is submitted as a combat action
- **THEN** the submission is rejected for the combat restriction, no gauge moves, and the item stays in inventory
