# defeat-aftermath-recovery delta

## ADDED Requirements

### Requirement: Defeat recovery advances the clock to the 5% wake target
After the core's defeat phases, the aftermath SHALL compute the minimum
non-negative integer seconds `t` such that the stored gauge-regen model
(`world/rules/clock.py`: HP advances as `floor(current + carried +
scaled_rate × elapsed)` with a carried float remainder, where `scaled_rate`
is the player's HP regen rate multiplied by the rulebook `recovery`
section's defeat scale, active while `defeat_weak` is mounted) first
reaches or exceeds the wake target `ceil(max_hp × 0.05)`; it SHALL advance
the world clock once by exactly `t` with source `defeat_aftermath`, then
clamp the player's HP to exactly the target. The wake state SHALL never sit
above the target. When the player's HP is already at or above the target at
solve time, `t` is `0`: no advance, no clamp, no event.

#### Scenario: Defeat wakes at exactly 5% after the computed advance
- **WHEN** a defeat settles with the player at HP 1, regen rate and remainder fixed by fixture, and the rulebook scale in force
- **THEN** the clock advances by the computed minimum `t` with source `defeat_aftermath` and the player's HP equals exactly `ceil(max_hp × 0.05)`

#### Scenario: Overshoot inside the final interval is clamped down
- **WHEN** a coarse regen rate would land the final tick's floor above the target
- **THEN** settlement ends with HP exactly at the target (the clamp write), never above it

#### Scenario: Already-above-target settles inertly
- **WHEN** the solve begins with HP at or above the wake target
- **THEN** the clock does not advance, HP is unchanged, and no recovery event is emitted

### Requirement: Unreachable recovery is capped and reported, never truncated silently
The `recovery` rulebook section SHALL declare `max_recovery_seconds`. If
the solve yields `t` above the cap (a zero/tiny scaled rate or a
pathologically low rate), the aftermath SHALL advance by the cap instead,
settle the player at the state the stored scaled model produces at the cap
(current and carried remainder — a declared aftermath write, never
clamped upward toward the target), and emit one `log_error` facade event
carrying `{char, tick, target, capped}` context.

#### Scenario: Degenerate rate hits the cap with an error event
- **WHEN** the rulebook scale combined with the fixture rate makes the target unreachable within `max_recovery_seconds` (e.g. a zero HP regen rate)
- **THEN** the clock advances by exactly the cap, HP rests below the target at the capped value, and one `log_error` event is recorded

### Requirement: The recovery rulebook section is validated by its own loader
The `rulebook/defeat_aftermath.yaml` `recovery` section (defeat regen
scale, `max_recovery_seconds`, wake fraction 0.05 as data) SHALL be
validated by a section validator registered through the core's per-section
loader; a malformed `recovery` section SHALL fail load, and the core's
existing sections SHALL be unaffected by its presence or absence.

#### Scenario: Malformed recovery section fails closed at load
- **WHEN** the `recovery` section carries a non-positive scale or missing key
- **THEN** rulebook load fails with a validation error and the server does not boot with a half-valid defeat registry

### Requirement: Clock side effects during the recovery window are the only quest/world mutations
Advancing through the recovery window may legitimately mutate world state
through ordinary clock causality — a crossed quest deadline failing a quest,
a crossed daily boundary applying gauge decay or reset, a crossed restock
boundary restocking a merchant, a buff expiring. The recovery battery
manifest SHALL enumerate these as the only expected in-window mutations for
every record family outside the aftermath's declared writes; any other
change fails the zero-uncaused-write contract.

#### Scenario: A recovery window crossing a quest deadline fails exactly that quest
- **WHEN** the computed `t` crosses one quest's deadline and a merchant's restock boundary
- **THEN** that quest is failed and the merchant restocked by ordinary clock logic, no other quest or record changed, and the manifest accounts for both mutations

### Requirement: The recovery phase commits with the settlement
The advance, the HP clamp, and the `recovery_advance` EventLog entry SHALL
run inside the same `settle_session` transaction as the rest of the
aftermath. A fault injected after the clamp before commit leaves no clock
movement, no HP change, and no recovery entry; the recovery fallback's
re-run reproduces the identical `t` (the solve is pure over stored state).

#### Scenario: Rollback removes the advance and the clamp together
- **WHEN** a fault is injected after the clamp write and before commit
- **THEN** the world tick, the player's HP, and the EventLog all match the pre-settlement state, and the retried settlement wakes the player at the same target

### Requirement: A retained quest-bound winner forces the move-and-rest route
When the defeating monster is quest-bound and therefore retained in the
room, the settlement SHALL complete normally, and `skip_safety` SHALL
continue to refuse rest/skip in that room; the smoke path SHALL prove the
player can move to an adjacent room (movement has no HP gate) and rest
there to full.

#### Scenario: Defeat against a retained winner, move, rest to full
- **WHEN** a player is defeated by a retained quest-bound winner, moves one room away, and issues a rest/skip
- **THEN** the settlement woke the player at the 5% target, the in-room rest is refused while the winner lives, and the adjacent-room rest succeeds and regenerates normally
