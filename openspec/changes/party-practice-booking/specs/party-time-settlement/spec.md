# Spec Delta

## ADDED Requirements

### Requirement: Each member owns one standing practice booking
Every party member SHALL own at most one standing practice booking that the commander can set for any present member outside combat; the booking SHALL persist until the next SKIP advance that settles that member, which SHALL settle it through the existing study-practice writer.

#### Scenario: Two members practise during one rest
- **WHEN** the commander books her own `slash` and 艾拉's `healing_light`, then rests three hours with 艾拉 present
- **THEN** both skills grow by three study hours each, each on its own member, and both bookings are consumed

#### Scenario: A member elsewhere keeps the booking
- **WHEN** 卡恩 has a standing booking and stays in another room while the commander rests
- **THEN** 卡恩's booking and proficiency are unchanged

#### Scenario: Movement does not consume a booking
- **WHEN** a member with a standing booking travels with the commander
- **THEN** the movement advance leaves the booking unconsumed

### Requirement: The text client books member practice
`修煉 <技能> [= <成員>]` SHALL book the named present member's practice (default: the caller) with the same preflight, rejections and messages as `explore.practice`, advancing no time, and SHALL be documented in both player command documents.

#### Scenario: Text booking matches the action
- **WHEN** the player types `修煉 healing_light = 艾拉`
- **THEN** 艾拉's booking equals the one `explore.practice` would record, and no time passes
