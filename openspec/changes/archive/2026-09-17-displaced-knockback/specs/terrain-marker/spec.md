## MODIFIED Requirements

### Requirement: A ground marker extinguishes when its holder leaves the battlefield
A live ground-marker instance SHALL end — through the existing buff-removal path, with zero further ticks or credit legs — when its holder flees the combat session, is knocked out, or the combat session ends, without waiting for its authored duration. This battlefield-exit extinguishment SHALL apply ONLY to rows declaring the marker clause — now covering both closed marker values, `ground` and `positional`, through the same removal path and the same persisted transitions: an ordinary buff's cross-combat persistence, refresh-stacking and expiry semantics SHALL be unchanged, and a marker still held by a still-active combatant SHALL persist across rounds exactly like any other timed buff. Marker expiry, dispel and cleanse SHALL remove the instance through the shipped paths unchanged, and removal SHALL never damage or revive any entity. Ground-row extinguishment behavior SHALL stay bit-identical to its shipped behavior.

#### Scenario: Fleeing steps off the hazard
- **WHEN** a synthetic marker holder flees mid-session and the clock advances past a would-be tick interval
- **THEN** the marker instance is gone at flee time, no further tick loss occurs, the standing-on-it fact is false, and the entity's non-marker buffs persist across the session boundary unchanged

#### Scenario: A knockout removes the footing marker
- **WHEN** a synthetic marker holder is knocked out by a nonlethal round and the session continues for further rounds
- **THEN** the marker instance no longer ticks and the standing-on-it fact is false for the knocked out holder

#### Scenario: Session end sweeps markers only
- **WHEN** a combat session ends with one living participant holding a synthetic ground marker and one holding an ordinary timed buff with equal remaining duration
- **THEN** the marker instance is removed at session end, the ordinary buff is untouched and still expiring on its own clock, and neither entity's HP changes from the sweep

#### Scenario: An active holder keeps the marker across rounds
- **WHEN** a synthetic marker holder stays in the fight for several rounds before expiry
- **THEN** the marker keeps ticking and matching every round until its own duration elapses

#### Scenario: The same transitions sweep positional rows
- **WHEN** a synthetic positional-marker holder flees, is knocked out, or ends the session while a ground-marker holder and an ordinary-buff holder remain under observation
- **THEN** the positional instance is removed at the transition through the same path with zero side effects, ground extinguishment behavior is unchanged, and the ordinary buff persists on its own clock
