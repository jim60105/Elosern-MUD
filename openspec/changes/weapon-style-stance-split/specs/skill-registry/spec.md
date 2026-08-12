## ADDED Requirements

### Requirement: light_sword_style deals damage via the standard damage convention
`light_sword_style` SHALL declare `effects=["damage:light:physical"]` (changed from the previously
inert `weapon_style:light_sword`), resolved by the already-registered `damage` effect handler.

#### Scenario: Casting light_sword_style deals light-elemental physical damage
- **WHEN** a player casts `light_sword_style` at a valid `SINGLE` target
- **THEN** the cast resolves successfully (no `UNKNOWN_EFFECT_ID` rejection) and the target takes
  light-elemental physical damage
