# terrain-marker Specification

## Purpose
Defines the element-agnostic ground-hazard marker primitive: a validated `marker: ground` clause on the buff-definition grammar making holder presence the canonical standing-on-it fact, with world-second duration/refresh lifecycle and automatic battlefield-exit (flee, knockout, session teardown) extinguishment scoped strictly to marker rows.

## Requirements

### Requirement: A ground-marker buff row makes holding it the canonical standing-on-it fact
A buff definition MAY declare the closed-vocabulary `marker: ground` clause at definition load. A row
that declares it SHALL be a ground-hazard marker whose canonical「站在其上」fact is exactly the
holder carrying a live (unexpired, non-paused) instance of that definition — there is no separate
position, tile, or room state, and no generic code SHALL read an element, skill or definition-key
identity to honor the clause. Marker rows compose with the shipped definition vocabulary without
restriction (a marker row may additionally carry `rate`, `bounds` or an empty `modifiers` mapping);
a row without the clause SHALL load, apply, tick and expire bit-identically to its pre-clause
behavior. The clause value SHALL be validated fail-closed at load — a value outside the closed
marker vocabulary, a non-string, or a boolean SHALL name the offending definition key and fail the
load.

#### Scenario: A synthetic marker hazard damages its holder while it lasts
- **WHEN** a synthetic marker row carrying a negative hp `rate` is applied by a living caster and the
  clock advances past several tick intervals and then past expiry
- **THEN** the holder loses exactly the authored per-interval amount each interval for exactly the
  authored duration, the standing-on-it fact is true for every interval and false after expiry, and
  no other entity changes

#### Scenario: A non-marker row is untouched by the clause machinery
- **WHEN** ordinary `bounds`-shaped and `rate`-shaped rows without the clause tick and expire
  alongside a synthetic marker row
- **THEN** each non-marker row's holder and every other entity change exactly as before the clause
  existed, and none of them satisfies any marker-fact query

#### Scenario: A malformed marker clause fails closed at load
- **WHEN** a synthetic buffs table declares `marker: fire`, `marker: true`, or `marker: 3`
- **THEN** the definition load fails naming the offending key, and no partially-loaded definition set
  is observable

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
