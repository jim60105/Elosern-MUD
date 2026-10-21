# Spec Delta

## MODIFIED Requirements

### Requirement: Other advances keep their scope
Church rites, GM console advances, defeat aftermath and combat settlement SHALL keep their existing non-mental entity scopes. Every accepted player-driven noncombat advance SHALL additionally settle mental time over the present co-located party, without widening unrelated HP/MP/SP, rite, quest or practice effects. Combat SHALL retain terminal participant scope; GM-only advances SHALL retain their declared scope.

#### Scenario: A church rite settles only its participant
- **WHEN** the commander performs a church rite with companions present
- **THEN** the rite's existing resource effects settle only the commander, while its actual elapsed mental time settles the present party

### Requirement: Each member owns one standing practice booking
Every party member SHALL own at most one standing practice booking that the commander can set for any present member outside combat; the booking SHALL persist until the next positive-duration eligible awake SKIP interval that settles that member, which SHALL settle it through the existing study-practice writer.

#### Scenario: Two members practise during one rest
- **WHEN** the commander books her own `slash` and 艾拉's `healing_light`, then waits three awake hours with 艾拉 present
- **THEN** both skills grow by three study hours each, each on its own member, and both bookings are consumed

#### Scenario: A member elsewhere keeps the booking
- **WHEN** 卡恩 has a standing booking and stays in another room while the commander rests
- **THEN** 卡恩's booking and proficiency are unchanged

#### Scenario: Movement does not consume a booking
- **WHEN** a member with a standing booking travels with the commander
- **THEN** the movement advance leaves the booking unconsumed

## ADDED Requirements

### Requirement: Per-member mental time uses actual posture and activity
Every actual noncombat player-driven advance SHALL settle present co-located party mental time once using transient per-member activities. SKIP alone SHALL select nobody for sleep. Dead/deleted actors SHALL receive no physiological revival, and remote populations SHALL not be scanned.

#### Scenario: Mixed wait
- **WHEN** one member forced asleep at zero and an awake companion at 216000 units share a 600-second wait
- **THEN** the sleeper reaches 7200 (2%) and stays asleep; the companion reaches 213600 (59.3333%); neither posture is selected by the shared advance

#### Scenario: Sleeping practice booking
- **WHEN** a sleeping booked member and an awake booked member share an eligible two-hour skip
- **THEN** only the awake member earns practice and consumes its booking; the sleeping booking remains for a later eligible awake interval

### Requirement: No accepted time means no mental settlement
Status inspection, inventory inspection, menus, handoff selection/cancel, inactivity, disconnect and wall-clock time SHALL advance neither game time nor reserve. Waiting SHALL use ordinary awake cost with no special recovery or guard/ambush benefit.

#### Scenario: Free operations
- **WHEN** the player reads status, opens inventory, cancels handoff and disconnects
- **THEN** tick and all mental reserves remain identical

