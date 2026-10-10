# Spec Delta

## MODIFIED Requirements

### Requirement: Each named public blessing ceremony reads the holder's excitement tier exactly once
The vessel SHALL retain exactly its two ceremonial modifier roles, a blessing arousal scale gated on vessel ownership and a separate positive defense grace gated on vessel ownership, active light_blessing and arousal at least 中等. Cast-time recovery grace SHALL combine the maximum of the priestly and vessel scale, with one arousal read, and snapshot that result on the mounted recovery buff. The blessing SHALL NOT gain a recovery profile; the vessel SHALL add no other combat adjustments.

#### Scenario: Shared synthetic snapshot mechanism
- **WHEN** a fixed synthetic fixture gives priestly and vessel scales 0.1 and arousal ordinal 2
- **THEN** each alone and both together mount grace 1.2, never double-counted 1.4; changing arousal after mounting leaves the snapshot unchanged

#### Scenario: Distinct defense recipient and gate
- **WHEN** a real holder and untouched non-holder resolve the named blessing with identical state above and below the arousal gate
- **THEN** the independent vessel defense row appears only on the qualified holder and no extra recovery profile is mounted, without literal +6/+18/60-second expectations

#### Scenario: The vessel alone reads the tier on a ward cast
- **WHEN** a fixed synthetic vessel scale 0.1 applies to a ward cast at ordinal 2
- **THEN** mounted grace is independently 1.2 from one arousal read

#### Scenario: Holding both clergy passives does not double the read
- **WHEN** fixed synthetic priestly and vessel scales are both 0.1 at ordinal 2
- **THEN** mounted grace is 1.2, never 1.4, and arousal is read once

#### Scenario: priestly_grace alone is unchanged
- **WHEN** a fixed synthetic priestly-only scale 0.1 applies at ordinal 3
- **THEN** mounted grace is 1.3 through the existing recovery path

#### Scenario: The goddess blessing ceremony reads the tier through its own grace row
- **WHEN** a real vessel holder above the 中等 gate has light_blessing active
- **THEN** current authored blessing defense and independent vessel defense both appear as separate status-sourced rows; below the gate only the base blessing remains

#### Scenario: A non-holder casts either ceremony plainly
- **WHEN** a caster owning neither clergy passive casts ward or goddess blessing
- **THEN** ward grace is the neutral 1.0 and blessing grants only its currently authored base row

#### Scenario: The scale key is deliberately distinct from priestly_grace's key
- **WHEN** vessel and priestly scale keys are compared
- **THEN** keys stay distinct because equal-key numeric contributions add at merge

#### Scenario: The +6 grace row follows the established 恩典 pattern
- **WHEN** the vessel defense row is authored
- **THEN** its magnitude is a positive flat authored defense value under the established holder/buff/arousal 恩典 predicate, not a fixed +6 approval

#### Scenario: The ward grace stays 0.1-scaled under every clergy holding
- **WHEN** the fixed synthetic 0.1 rows apply separately or together to a ward cast
- **THEN** grace is 1 plus 0.1 times ordinal, never 0.2 times ordinal; production casts consume the maximum current declared scale

#### Scenario: The authored goddess_blessing numbers stay byte-identical
- **WHEN** this test-design migration is applied
- **THEN** it changes no production goddess_blessing data; future valid authored coefficient/defense/duration edits require no old-value expectation table

#### Scenario: The second ceremonial read stacks independently and adds no recovery profile
- **WHEN** the vessel row applies with live light_blessing
- **THEN** its declared defense remains an independent status-sourced contribution and light_blessing gains no recovery profile

### Requirement: Saintess trickle pins the holder's idle arousal inside the idle band
For an entity owning `saintess_vessel`, the world-clock settlement SHALL guarantee that after any settlement step the entity's pleasure is never below the 微興奮 authored floor while the holder sits below the 中等/高度 boundary, and all trickle writes go through the sanctioned `world/rules/` pleasure writers only, never a typeclass, AI, or presentation module. The holder's arousal level therefore never leaves 微興奮～中等, and a non-holder SHALL decay and settle byte-for-byte exactly as before this change.

#### Scenario: A completely idle holder at zero is pinned up in one advance
- **WHEN** a vessel holder with pleasure 0 and no buffs or other pending settlement work is settled by one world-clock advance
- **THEN** her pleasure reads exactly the authored 微興奮 floor after the advance (the pin runs even though the quantum decay loop has no pending work to do)

#### Scenario: The band oscillation stays inside [15, 59] and visibly moves
- **WHEN** a vessel holder starts strictly inside the authored idle band and is settled by many successive advances
- **THEN** every reading stays within the interval from the 微興奮 floor through the 中等 ceiling, successive readings differ by at most 1 per advance, and at least one reading differs from the starting value

#### Scenario: Decay cannot push a holder out of the band
- **WHEN** a vessel holder inside the band is advanced longer than the pleasure decay interval
- **THEN** her pleasure never falls below the authored 微興奮 floor and her arousal level never reads 平靜

#### Scenario: A holder at or above 高度 is left to ordinary decay
- **WHEN** a vessel holder within the authored 高度 band is settled after more than one decay interval
- **THEN** the trickle adds nothing, ordinary decay applies, and the pin/oscillation resume only once the gauge re-enters the interval from the 微興奮 floor through the 中等 ceiling

#### Scenario: A retried failed advance recomputes the identical step
- **WHEN** a world-clock advance for a mid-band holder is forced to fail after the trickle step and is retried with the same inputs
- **THEN** both attempts compute the same fluctuation direction and the restored holder's pleasure equals the single-apply value

#### Scenario: The idle trickle never opens a climax
- **WHEN** a holder whose climax phase rests at 接近 (left there by an earlier 極限 spike) is settled by repeated advances inside the interval from the 微興奮 floor through the 中等 ceiling
- **THEN** the phase never reads 進行中 and no extension is staged

#### Scenario: Non-holders are byte-identical
- **WHEN** a non-holder starts within the authored 微興奮 band and is settled over the same advances
- **THEN** she receives no fluctuation, no pin, and her decay follows the unchanged 平靜-floor behavior

#### Scenario: The holder's decay floor is the 微興奮 floor
- **WHEN** the pleasure decay step runs for a vessel holder
- **THEN** `decay_tick` targets `max(authored_micro_floor, band_floor - 1)` and a holder at or below the authored 微興奮 floor with decay due is a no-op

#### Scenario: The pin runs once per advance over settled non-combat scopes
- **WHEN** one world-clock `advance()` with `seconds > 0` settles non-combat-sourced scopes containing entities below the authored 微興奮 floor
- **THEN** each such holder is raised to exactly the authored 微興奮 floor via `apply_pleasure_gain(..., stimulus=False)`, once per `advance()` and NOT per settlement quantum

#### Scenario: The band step is a deterministic stateless hash draw
- **WHEN** a vessel holder inside the interval from the 微興奮 floor through the 中等 ceiling is settled by one advance
- **THEN** she receives exactly one ±1 step whose direction is a stateless hash of the FULL resulting world tick and the entity identity; no RNG is consumed, and fixed even-duration fixtures refute raw tick parity as a draw source that would freeze per entity, without pinning production advance durations
- **AND** the result is clamped so the gauge never leaves the interval from the 微興奮 floor through the 中等 ceiling, and a clamped-to-zero delta issues no writer call

#### Scenario: The trickle leaves an entity at or above 60 untouched
- **WHEN** a vessel holder's gauge reads the authored 高度 floor or above at settlement
- **THEN** the trickle touches nothing, ordinary decay owns the descent, and the pin and band step re-arm only when the gauge re-enters the band

#### Scenario: Trickle writes carry the writer's explicit non-stimulus policy
- **WHEN** a trickle write lands on a holder
- **THEN** the sanctioned writer's explicit non-stimulus policy applies: the gauge write and the wetness-on-band-up cascade apply, while the climax-phase edges (接近→進行中, 極限→接近) and extension staging NEVER fire; the idle fluctuation must not autonomously open a climax below the authored 極限 floor for a holder parked at 接近

#### Scenario: A holder resting at the floor stays pinned with at most ±1 movement
- **WHEN** a vessel holder rests at the 微興奮 floor across advances
- **THEN** she never falls below the authored 微興奮 floor and moves by at most ±1 per advance
