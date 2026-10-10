# Spec Delta

## MODIFIED Requirements

### Requirement: Each named public blessing ceremony reads the holder's excitement tier exactly once
The vessel SHALL retain exactly its two ceremonial modifier roles, a blessing arousal scale gated on vessel ownership and a separate positive defense grace gated on vessel ownership, active light_blessing and arousal at least 中等. Magnitudes and authored durations SHALL be mutable rulebook data. Cast-time recovery grace SHALL combine the maximum of the priestly and vessel scale, with one arousal read, and snapshot that result on the mounted recovery buff. The blessing SHALL NOT gain a recovery profile; the vessel SHALL add no other combat adjustments.

#### Scenario: Shared synthetic snapshot mechanism
- **WHEN** a fixed synthetic fixture gives priestly and vessel scales 0.1 and arousal ordinal 2
- **THEN** each alone and both together mount grace 1.2, never double-counted 1.4; changing arousal after mounting leaves the snapshot unchanged

#### Scenario: Distinct defense recipient and gate
- **WHEN** a real holder and untouched non-holder resolve the named blessing with identical state above and below the arousal gate
- **THEN** the independent vessel defense row appears only on the qualified holder and no extra recovery profile is mounted, without literal +6/+18/60-second expectations

### Requirement: Saintess trickle pins the holder's idle arousal inside the idle band
For an entity owning `saintess_vessel`, the world-clock settlement SHALL guarantee that after any settlement step the entity's pleasure is never below the 微興奮 authored floor while the holder sits below the 中等/高度 boundary, and all trickle writes go through the sanctioned `world/rules/` pleasure writers only, never a typeclass, AI, or presentation module. The holder's arousal level therefore never leaves 微興奮～中等, and a non-holder SHALL decay and settle byte-for-byte exactly as before this change.

#### Scenario: A completely idle holder at zero is pinned up in one advance
- **WHEN** a vessel holder with pleasure 0 and no buffs or other pending settlement work is settled by one world-clock advance
- **THEN** her pleasure reads exactly the authored 微興奮 floor after the advance (the pin runs even though the quantum decay loop has no pending work to do)

#### Scenario: The band oscillation stays inside the interval from the 微興奮 floor through the 中等 ceiling and visibly moves
- **WHEN** a vessel holder with pleasure 30 is settled by many successive advances
- **THEN** every reading stays within the interval from the 微興奮 floor through the 中等 ceiling, successive readings differ by at most 1 per advance, and at least one reading differs from 30

#### Scenario: Decay cannot push a holder out of the band
- **WHEN** a vessel holder inside the band is advanced longer than the pleasure decay interval
- **THEN** her pleasure never falls below the authored 微興奮 floor and her arousal level never reads 平靜

#### Scenario: A holder at or above 高度 is left to ordinary decay
- **WHEN** a vessel holder with pleasure 70 (高度) is settled after more than one decay interval
- **THEN** the trickle adds nothing, ordinary decay applies, and the pin/oscillation resume only once the gauge re-enters the interval from the 微興奮 floor through the 中等 ceiling

#### Scenario: A retried failed advance recomputes the identical step
- **WHEN** a world-clock advance for a mid-band holder is forced to fail after the trickle step and is retried with the same inputs
- **THEN** both attempts compute the same fluctuation direction and the restored holder's pleasure equals the single-apply value

#### Scenario: The idle trickle never opens a climax
- **WHEN** a holder whose climax phase rests at 接近 (left there by an earlier 極限 spike) is settled by repeated advances inside the interval from the 微興奮 floor through the 中等 ceiling
- **THEN** the phase never reads 進行中 and no extension is staged

#### Scenario: Non-holders are byte-identical
- **WHEN** a non-holder with pleasure 20 is settled over the same advances
- **THEN** she receives no fluctuation, no pin, and her decay follows the unchanged 平靜-floor behavior

#### Scenario: The holder's decay floor is the 微興奮 floor
- **WHEN** the pleasure decay step runs for a vessel holder
- **THEN** `decay_tick` targets `max(15, band_floor − 1)` and a holder at or below the authored 微興奮 floor with decay due is a no-op

#### Scenario: The pin runs once per advance over settled non-combat scopes
- **WHEN** one world-clock `advance()` with `seconds > 0` settles non-combat-sourced scopes containing entities below the authored 微興奮 floor
- **THEN** each such entity is raised to exactly 15 via `apply_pleasure_gain(..., stimulus=False)`, once per `advance()` and NOT per settlement quantum

#### Scenario: The band step is a deterministic stateless hash draw
- **WHEN** a vessel holder inside the interval from the 微興奮 floor through the 中等 ceiling is settled by one advance
- **THEN** she receives exactly one ±1 step whose direction is a stateless hash of the FULL resulting world tick and the entity identity ;  no RNG is consumed, and raw tick parity is refuted as the draw source because every shipped non-combat advance duration is even and the draw would freeze per entity
- **AND** the result is clamped so the gauge never leaves the interval from the 微興奮 floor through the 中等 ceiling, and a clamped-to-zero delta issues no writer call

#### Scenario: The trickle leaves an entity at or above 60 untouched
- **WHEN** a vessel holder's gauge reads 60 or above at settlement
- **THEN** the trickle touches nothing, ordinary decay owns the descent, and the pin and band step re-arm only when the gauge re-enters the band

#### Scenario: Trickle writes carry the writer's explicit non-stimulus policy
- **WHEN** a trickle write lands on a holder
- **THEN** the sanctioned writer's explicit non-stimulus policy applies: the gauge write and the wetness-on-band-up cascade apply, while the climax-phase edges (接近→進行中, 極限→接近) and extension staging NEVER fire ;  the idle fluctuation must not autonomously open a climax below the 85 gate for a holder parked at 接近

#### Scenario: A holder resting at the floor stays pinned with at most ±1 movement
- **WHEN** a vessel holder rests at the 微興奮 floor across advances
- **THEN** she stays never-below-15 with at most ±1 movement per advance
