## ADDED Requirements

### Requirement: Gauge transfer is one typed effect family with a closed gauge set and validated magnitude modes
A skill SHALL express a gauge movement with one typed effect carrying a gauge from the closed set {`mp`, `hp`} (any other gauge, including `sp`, SHALL fail at parse until a consumer exists), one closed direction (`drain`/`restore`), and exactly one magnitude mode: an authored fixed amount, a finite fraction of the target's current value in that gauge in `(0,1]`, or the target's entire pool. Direction legality SHALL be per gauge: `mp` admits both directions; `hp` admits `drain` ONLY — an `hp` restore declaration SHALL be a construction error because HP restoration is the heal effect's exclusive verb. Malformed prefixes, unknown gauges, unknown directions, out-of-range fractions, non-positive fixed amounts and any potency coefficient attached to a transfer SHALL fail at registry construction. The transfer SHALL not be reinterpreted by any element-, skill- or handler-name branch.

#### Scenario: Each mode settles its authored magnitude
- **WHEN** synthetic mp drain skills with fixed, fraction and whole-pool modes hit a pool with a known current value
- **THEN** each moves exactly the authored amount (fraction rounding fixed by the contract) and an invalid authoring is rejected before any cast is possible

#### Scenario: Hp drain is legal and hp restore is rejected at construction
- **WHEN** a synthetic skill declares an hp drain in each magnitude mode and, separately, an `hp` restore of any mode
- **THEN** the drains parse and settle against the target's HP under the same magnitude rules, while every hp restore form raises before any cast is possible

#### Scenario: The closed gauge set admits no third axis
- **WHEN** `parse_effect` is called with an `sp` or otherwise unknown gauge segment
- **THEN** it raises `ValueError` (and therefore fails at registry load) — the family carries no dead gauge axis

#### Scenario: Alternate schools reuse the family
- **WHEN** a non-water synthetic skill declares the same prefixes and policies
- **THEN** it settles identically through the generic parse, policy and handler with no element-specific code

### Requirement: Drains pay through their gauge's canonical writer on both legs and share on the actual amount
A drain SHALL decrease the target through the canonical writer of its declared gauge — the mp gauge through the MP-depletion wave's canonical MP writer (dispatching the depletion outcome with the cast as attributed source whenever it zeroes the pool), the hp gauge through the existing attributed hp-loss write path the buff rate-tick consumes (dispatching the hp-loss outcome with source attribution and adding no new zero fact) — and SHALL return the configured caster recovery share of the ACTUAL amount drained, in the same gauge, through that gauge's writer on the caster. A share of a clamped or already-partial drain is computed on what was actually taken, never on the requested amount. An hp drain that reaches zero SHALL leave the terminal settlement to the combat/death pipeline's single settlement — exactly one death outcome per crossing, never a second kill path — honoring the same nonlethal knockout projection the combat stage already applies. Both legs SHALL settle inside the action's staged effects with snapshots so a commit failure restores target and caster together.

#### Scenario: Half-share on a clamped drain
- **WHEN** a synthetic mp drain of 5 with 50 % caster share hits a pool holding 3
- **THEN** the target lands at zero, the caster gains exactly 2 (share of the actual 3, not of the requested 5) and the depletion event names the cast once

#### Scenario: Fractional maw empties proportionally
- **WHEN** a synthetic fraction-of-current drain with 20 % target ratio and full caster return drains a known pool
- **THEN** the pool loses the contracted share and the caster gains the same actual amount, clamped at the caster's MP maximum

#### Scenario: Hp drain shares the actual HP taken
- **WHEN** a synthetic hp drain with a caster share hits a target whose remaining HP is below the requested amount
- **THEN** the caster gains the share of the HP actually removed and the hp-loss outcome carries the attributed source

#### Scenario: Hp drain-to-zero settles exactly one death
- **WHEN** a synthetic hp drain takes a living target from positive HP to zero
- **THEN** the combat/death pipeline performs its single terminal settlement for the crossing, the drain contributes no separate zero fact, and one kill attribution results — not two

#### Scenario: A failed commit restores both legs
- **WHEN** a staged drain-and-share cast fails at a later commit point
- **THEN** the target's gauge, the caster's gauge and any reaction-applied marker from the crossing are all restored

### Requirement: Restores clamp per target and add the caster's active marker-stack bonus
An mp restore SHALL move its authored fixed amount plus one bonus per ACTIVE instance of each explicitly declared marker key counted on the CASTER, through the canonical MP writer's increase leg, clamped at each recipient's MP maximum. Restore SHALL never dispatch a depletion event, SHALL count the caster's own instances (never the recipient's), and SHALL read counts from stored buff state without materializing handlers on preview paths. The per-stack bonus is mp-restore-only in practice because the hp gauge admits no restore direction.

#### Scenario: Per-stack bonus reads the caster
- **WHEN** a synthetic restore with a declared marker bonus runs from a caster holding one active instance of each of three declared marker keys while the recipient holds none
- **THEN** the recipient's pool gains base plus one bonus per present key and the same cast from a marker-free caster gains base only

#### Scenario: Overflow clamps without loss elsewhere
- **WHEN** an area restore pushes one ally over their maximum while another gains fully
- **THEN** the first lands exactly at maximum, the second gains the full amount, and no depletion event fires for anyone

### Requirement: Regen lock is a bounded marker consumed by the clock's closed-form regen
A marker buff SHALL be able to zero one gauge's passive regeneration for its bounded duration through one ordinary combat-modifier rule contributing a per-gauge regen-scale bundle value, consumed by the world clock's existing closed-form regen computation as a multiplier (absent means unchanged). A zero scale SHALL neither accrue regeneration nor consume the carried sub-unit remainder, SHALL end exactly at expiry, and SHALL leave authored direct stat grants (item effects) untouched. No scheduler, cooldown table or element-specific branch may participate.

#### Scenario: Locked gauge regenerates nothing while the lock lives
- **WHEN** a synthetic entity at a depleted MP pool advances the clock under an active regen-lock marker and after its expiry
- **THEN** MP stays exactly at the pre-lock value across the locked window, the carried remainder is preserved, and regen resumes normally afterward

#### Scenario: Authored grants bypass the lock
- **WHEN** the locked entity receives an item-style direct stat grant and an authored restore effect
- **THEN** both apply normally — only passive regeneration is frozen

#### Scenario: Regen stays closed-form
- **WHEN** the regen stage runs for locked and unlocked entities over one multi-second advance
- **THEN** the computation performs no per-second or per-quantum loop for either entity and unlocked arithmetic is bit-identical to the pre-change closed form

### Requirement: A component's audience gate selects its recipients by stored target state
An effect component SHALL be declarable with one immutable validated audience condition over a closed
gauge-state vocabulary (the recipient's MP maximum being zero, or being positive), evaluated per
resolved target from stored state at audience planning without handler materialization or random
rolls. The gate SHALL skip ONLY its own component for non-matching targets — every other component of
the same cast follows its own audience — and preflight and final resolution SHALL evaluate the
identical gate against current state. Malformed gate declarations SHALL fail at authoring. The gate
SHALL compose with the existing relation audiences (an ally-audience component may additionally
require a gauge-state fact).

#### Scenario: Max-zero rider delivers to one subset only
- **WHEN** one synthetic cast carries an ungated component to all selected targets and a gated rider
  requiring the zero-maximum fact, against one normal-pool and one zero-maximum target
- **THEN** the ungated component lands on both, the rider lands only on the zero-maximum target, and
  a single paid settlement and one practice pass cover the cast

#### Scenario: Stale preflight re-evaluates the identical gate
- **WHEN** preflight classifies the gated recipients and a target's stored gauge state changes before
  execution
- **THEN** final delivery follows the current stored state, never the preview classification

#### Scenario: Gate composition with relation audiences
- **WHEN** a synthetic ally-audience restore additionally declares a positive-maximum gate and the
  selection mixes allies with and without a positive MP maximum
- **THEN** only allies satisfying both the relation and the gate receive it

#### Scenario: Malformed gates fail at authoring
- **WHEN** authoring declares an unknown gate field, a gate without a component, or a contradictory
  combination of both gate facts on one component
- **THEN** skill construction raises before any cast is possible
