# Spec Delta

## MODIFIED Requirements

### Requirement: Defeat recovery advances the clock to the 5% wake target
After the core's defeat phases, the aftermath SHALL compute the minimum
non-negative integer seconds `t` such that the stored gauge-regen model
(`world/rules/clock.py`: HP advances as `floor(current + carried +
scaled_rate × elapsed)`) first reaches or exceeds the wake target
`ceil(max_hp × declared_wake_fraction)`; it SHALL advance the world clock once by exactly
`t` with source `defeat_aftermath`, then clamp the player's HP to exactly
the target.

#### Scenario: Defeat wakes at exactly the declared fraction after the computed advance
- **WHEN** a defeat settles with the player at HP 1, regen rate and remainder fixed by fixture, and the rulebook scale in force
- **THEN** the clock advances by the computed minimum `t` with source `defeat_aftermath` and the player's HP equals exactly `ceil(max_hp × declared_wake_fraction)`

#### Scenario: Overshoot inside the final interval is clamped down
- **WHEN** a coarse regen rate would land the final tick's floor above the target
- **THEN** settlement ends with HP exactly at the target (the clamp write), never above it

#### Scenario: Already-above-target settles inertly
- **WHEN** the solve begins with HP at or above the wake target
- **THEN** the clock does not advance, HP is unchanged, and no recovery event is emitted

#### Scenario: The scaled regen model behind the solve
- **WHEN** the solve evaluates the stored gauge-regen model
- **THEN** `carried` is the float remainder the model carries, and `scaled_rate` is the player's HP regen rate multiplied by the rulebook `recovery` section's defeat scale, active while `defeat_weak` is mounted
- **AND** when the player's HP is already at or above the target at solve time, `t` is `0`

#### Scenario: The wake state never sits above the target
- **WHEN** a defeated player wakes
- **THEN** the wake state never sits above the wake target

#### Scenario: Synthetic recovery oracle
- **WHEN** a fixed synthetic recovery row sets wake fraction 0.05 and max HP 100
- **THEN** recovery solves for HP 5 using an independently known clock/regen fixture and proves rollback without pinning the production fraction


### Requirement: The recovery rulebook section is validated by its own loader
The `rulebook/defeat_aftermath.yaml` `recovery` section (defeat regen
scale, `max_recovery_seconds`, validated authored wake fraction as data) SHALL be
validated by a section validator registered through the core's per-section
loader; a malformed `recovery` section SHALL fail load, and the core's
existing sections SHALL be unaffected by its presence or absence.

#### Scenario: Malformed recovery section fails closed at load
- **WHEN** the `recovery` section carries a non-positive scale or missing key
- **THEN** rulebook load fails with a validation error and the server does not boot with a half-valid defeat registry

#### Scenario: Synthetic recovery oracle
- **WHEN** a fixed synthetic recovery row sets wake fraction 0.05 and max HP 100
- **THEN** recovery solves for HP 5 using an independently known clock/regen fixture and proves rollback without pinning the production fraction


### Requirement: A retained quest-bound winner forces the move-and-rest route
When the defeating monster is quest-bound and therefore retained in the
room, the settlement SHALL complete normally, and `skip_safety` SHALL
continue to refuse rest/skip in that room; the smoke path SHALL prove the
player can move to an adjacent room (movement has no HP gate) and rest
there to full.

#### Scenario: Defeat against a retained winner, move, rest to full
- **WHEN** a player is defeated by a retained quest-bound winner, moves one room away, and issues a rest/skip
- **THEN** the settlement woke the player at the declared wake target, the in-room rest is refused while the winner lives, and the adjacent-room rest succeeds and regenerates normally

#### Scenario: Synthetic recovery oracle
- **WHEN** a fixed synthetic recovery row sets wake fraction 0.05 and max HP 100
- **THEN** recovery solves for HP 5 using an independently known clock/regen fixture and proves rollback without pinning the production fraction

