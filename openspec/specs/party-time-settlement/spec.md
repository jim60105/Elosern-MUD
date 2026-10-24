# party-time-settlement Specification

## Purpose
Define which commander-initiated world-clock advances settle the present party, so resting and travelling regenerate, expire and settle companions together with the commander.

## Requirements

### Requirement: Skip advances settle the present party
Every SKIP-source advance started by a rest, sleep, wait, or graphical wait SHALL settle the present party scope: the commander and every effective companion located in the commander's room, whether or not the player is possessing a companion.

#### Scenario: Resting regenerates a co-located companion
- **WHEN** the commander rests one hour with companion 艾拉 at MP 10 of 120 in the same room
- **THEN** 艾拉's MP regenerates by her own one-hour regeneration in the same advance as the commander

#### Scenario: A companion in another room is not settled
- **WHEN** the commander rests one hour while companion 卡恩 waits in another room with an active buff
- **THEN** 卡恩's gauges and buff state are unchanged by that advance

### Requirement: Movement advances settle the travelling party
A movement advance SHALL settle the travelling party: the traverser and every party member the follow step moves with it (effective companions and, for a possessed traverser, the commander's body, co-located in the source room before the step).

#### Scenario: Followers regenerate with the step
- **WHEN** the commander steps through an exit with 艾拉 in the source room
- **THEN** the one movement advance settles both the commander and 艾拉

#### Scenario: Possessed movement settles the whole travelling party
- **WHEN** the player, possessing 艾拉, steps through an exit while the player's body and 卡恩 share her source room
- **THEN** the one movement advance settles 艾拉, the player's body and 卡恩

### Requirement: Other advances keep their scope
Church rites, GM console advances, defeat aftermath and combat settlement SHALL keep their existing non-mental entity scopes. Every accepted player-driven noncombat advance SHALL additionally settle mental time over the present co-located party, without widening unrelated HP/MP/SP, rite, quest or practice effects. Combat SHALL retain terminal participant scope; GM-only advances SHALL retain their declared scope.

#### Scenario: A church rite settles only its participant
- **WHEN** the commander performs a church rite with companions present
- **THEN** the rite's existing resource effects settle only the commander, while its actual elapsed mental time settles the present party

### Requirement: A failed party advance restores every settled member
When a party-scoped advance fails after any settlement write, the system SHALL restore every settled member's gauges, buffs and practice booking together with the tick.

#### Scenario: Injected failure restores the companion
- **WHEN** a rest advance raises after settling the commander and 艾拉
- **THEN** both members' gauges and buffs equal their pre-advance values and the tick is unchanged

### Requirement: Field cast and item use advances settle the present party
Every successful out-of-combat field cast or item use SHALL settle its command-time advance over the present party scope of its acting character, so gauge regeneration and buff expiry reach every co-located member once.

#### Scenario: A field heal settles the whole present party
- **WHEN** the commander casts a field heal out of combat with companions 艾拉 and 卡恩 present
- **THEN** the one command-time advance settles the commander, 艾拉 and 卡恩

#### Scenario: A rejected field action settles nobody
- **WHEN** an out-of-combat item use is rejected in preflight
- **THEN** no member's gauges, buffs or booking change and the tick is unchanged

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

### Requirement: The text client books member practice
`修煉 <技能> [= <成員>]` SHALL book the named present member's practice (default: the caller) with the same preflight, rejections and messages as `explore.practice`, advancing no time, and SHALL be documented in both player command documents.

#### Scenario: Text booking matches the action
- **WHEN** the player types `修煉 healing_light = 艾拉`
- **THEN** 艾拉's booking equals the one `explore.practice` would record, and no time passes

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

### Requirement: Every settled sleeper completes its own accepted wake plan
Every applicable deterministic party advance SHALL reconcile each living sleeper's own declared wake target, independent of the controlled body. Voluntary recovery SHALL include HP/MP/SP and mental targets; duration SHALL wait until its deadline. Wake SHALL change that body's posture/projection once without changing possession or reviving defeat/death. Live-combat natural wake SHALL retain terminal-only policy.

#### Scenario: Owner wakes while companion waits
- **WHEN** an awake possessed companion waits across its sleeping owner's recovery boundary
- **THEN** the owner becomes awake and its receipt completes once while session control remains on the companion

#### Scenario: Owner wakes while another companion sleeps
- **WHEN** continuation of a controlled companion's sleep reaches the owner's earlier voluntary target
- **THEN** owner posture reconciles awake despite the owner not being the explicitly continued member

#### Scenario: Reserve saturates before duration
- **WHEN** a duration sleeper reaches full reserve before its deadline during another body's local action
- **THEN** it remains asleep until the deadline while reserve clamps, and a later applicable advance wakes it

#### Scenario: Independent practice and resources
- **WHEN** a booked sleeping member reaches its target partway through an applicable interval and another member remains awake
- **THEN** sleeping time earns no practice and preserves the booking; any eligible later awake interval uses ordinary practice/resource rules without granting sleep recovery twice

### Requirement: Sleep receipts join complete party advance compensation
Sleep targets, per-body progress, wake state and completion notifications SHALL commit with the owning clock advance. Failure SHALL restore every touched persisted and cached resource, reserve, posture, projection, booking, receipt and clock surface. Technical failures SHALL report no completed wake; replay SHALL reuse the committed result.

#### Scenario: Late failure
- **WHEN** a fault occurs after clock/resource settlement and one body's wake write
- **THEN** all touched bodies and receipt/projection caches restore with the original tick and no wake-success notification
