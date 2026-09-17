## ADDED Requirements

### Requirement: Usable intimacy devices raise pleasure through the existing shared writer
The catalog SHALL register the codex's usable 性玩具 roster — 催情浴鹽, 史萊姆潤滑凝膠, 熱吻藥水, 微電跳蛋糖, 纏枝魔藤, 女神之吻聖霧, 情欲香爐 — as usable items in the intimacy-device category on the intimacy-device price band. Each SHALL declare exactly one effect: a positive adjustment to the pleasure gauge scoped to the acting entity. The settlement of that adjustment SHALL route through the intimacy system's single shared pleasure writer, so a device's stimulation reaches arousal, wetness, and climax state by the identical path a skill's stimulation does. No device SHALL introduce a status key, a new verb, or a second effect entry.

#### Scenario: Every usable device declares one self-scoped pleasure gain
- **WHEN** the seven usable intimacy profiles are loaded
- **THEN** each carries exactly one effect entry, that entry is a positive pleasure adjustment scoped to the acting entity, and no entry names a status

#### Scenario: A device's stimulation drives the same cascade as a skill's
- **WHEN** a usable intimacy device is used by an entity whose pleasure gauge is below its ceiling
- **THEN** the pleasure gauge rises through the shared writer and the arousal-coupled state changes follow, with the applied delta reported as what actually moved

#### Scenario: A device at a full gauge is refused rather than consumed
- **WHEN** a usable intimacy device is used by an entity whose pleasure gauge is already at its ceiling
- **THEN** the use is rejected with the full-gauge reason and the item is not consumed

### Requirement: Intimacy magnitudes are drawn from the existing stimulus band
The three magnitudes a usable intimacy device may declare — gentle, moderate, and intense — SHALL be taken from the intimacy system's existing stimulus magnitude band rather than chosen independently, so an item's stimulation is never stronger or weaker than the acts the same system already models. The codex's stated tier for each device SHALL determine which of the three it uses.

#### Scenario: Every declared magnitude lies in the stimulus band
- **WHEN** each usable intimacy profile's pleasure amount is compared against the intimacy system's stimulus magnitude band
- **THEN** every amount lies within that band's bounds

#### Scenario: Codex tier and declared magnitude agree
- **WHEN** each device's codex tier is compared against its declared amount
- **THEN** gentle, moderate, and intense devices carry the band's low, middle, and high values respectively, with no two tiers sharing a value

### Requirement: Intimacy devices are barred from combat and may be reusable
Every usable intimacy device SHALL be barred from use during combat, because the codex frames them as leisure and ritual goods rather than battlefield consumables. A device the codex describes as reusable SHALL declare that a use does not consume it; such a device SHALL still incur the ordinary out-of-combat time cost of an item use, which is the only thing bounding how often it can be used.

#### Scenario: A device cannot be used in a combat turn
- **WHEN** a usable intimacy device is submitted as a combat action
- **THEN** the submission is rejected for the combat restriction and no gauge moves

#### Scenario: A reusable device survives its own use
- **WHEN** a device declared as non-consuming is used successfully out of combat
- **THEN** its effect settles, the item remains in inventory at the same count, and the world clock advances by the standard item-use duration

#### Scenario: A consuming device is spent
- **WHEN** a device declared as consuming is used successfully
- **THEN** exactly one copy is removed from inventory
