# city-sleep-policy Specification

## Purpose
Give city locations consistent voluntary sleep rules while preserving forced sleep and free safe camping outside cities.

## Requirements

### Requirement: City locations govern voluntary sleep
City shops, homes belonging to others, and other non-lodging interiors SHALL refuse voluntary sleep. City streets SHALL allow voluntary naps with a general patrol warning that discloses no patrol time. A city SHALL NOT offer a free protected overnight sleep location. Solo, party, camp and web requests SHALL NOT bypass the same policy. Awake rest, waiting, involuntary sleep, and ordinary safe camping outside cities SHALL retain their existing rules.

#### Scenario: Store and shelter location checks
- **WHEN** players attempt solo or party sleep or camp in a city shop, and attempt awake waiting there or safe camping outside the city
- **THEN** no voluntary sleep starts in the shop, awake waiting is unaffected, and the safe outdoor camp retains ordinary free recovery

### Requirement: A city patrol ends voluntary street naps
The game clock SHALL apply applicable city patrols deterministically. A patrol reaching an active voluntary street nap SHALL credit only elapsed recovery, end the nap, and wake the affected bodies with no continuation. That party SHALL be refused another nap at the same location until the next game day. Recovery claims SHALL reflect committed time. No money is lost and forced sleepers retain their existing threshold.

#### Scenario: Interrupted street nap
- **WHEN** a party's voluntary street nap crosses an applicable patrol while a separate forced sleeper is present
- **THEN** the nap ends at the patrol, the voluntary sleepers retain the settled recovery and cannot resume the nap, and the forced sleeper is not awakened by the patrol

#### Scenario: Refusal persists across reload
- **WHEN** the party reloads after a patrol interruption and retries the same street on the same game day
- **THEN** entry is refused before advancing time or changing sleep state and becomes available on the next day if otherwise eligible
