## ADDED Requirements

### Requirement: Wearable intimacy devices express sustained stimulation as a worn adjustment and a stated cost
The catalog SHALL register the codex's wearable 性玩具 roster — 花蒂銀夾, 暖蜜魔導珠, 恆溫魔法卵, 尖銳觸感之飾, 恆振晶 — as accessory-slot equipment in the intimacy-device category on the intimacy-device price band. Sustained stimulation SHALL be modelled as a positive worn pleasure adjustment and SHALL NOT require any new status definition, verb, or rulebook field. Where the codex assigns a device a drawback, it SHALL be authored as a negative combat or stamina column expressing the cost of distraction; a device SHALL NOT carry a drawback the codex does not state.

#### Scenario: Every wearable device is accessory-slot equipment in its own category
- **WHEN** the five wearable intimacy keys are inspected
- **THEN** each declares the accessory slot, the intimacy-device kind and icon key, the intimacy-device price band, and a complete modifier binding

#### Scenario: Stimulation needs no new status vocabulary
- **WHEN** the five rulebook entries are inspected
- **THEN** each expresses its effect through existing adjustment fields alone, with no attached buff, immunity, or status key introduced by this roster

#### Scenario: Drawbacks match the codex
- **WHEN** each device's negative columns are compared against its codex row
- **THEN** the negative defence and stamina-cost values agree, and no device carries a negative column the codex omits

### Requirement: The intimacy-device category is registered without a storefront
The wearable intimacy roster SHALL be registry-only. The codex routes these goods through the 聖所 device shop and the elven village shop, and until those storefronts exist no shop SHALL offer them. They SHALL remain equippable, inspectable, and grantable by any non-shop path.

#### Scenario: No shop stocks a wearable intimacy device
- **WHEN** every shop's offered keys are inspected
- **THEN** none of the five wearable intimacy keys appears

#### Scenario: A wearable device equips and applies when granted
- **WHEN** a wearable intimacy device is placed in an entity's inventory by a non-shop path and equipped
- **THEN** it occupies an accessory slot and its pleasure adjustment reaches the shared accessor
