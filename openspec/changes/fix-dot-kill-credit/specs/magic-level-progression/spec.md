## MODIFIED Requirements

### Requirement: World-clock and combat integration use the progression seams exactly once
The existing `magic_study` world-clock stage SHALL call `accrue_magic_study()` for elapsed non-combat time, whose SKIP-only source gate remains authoritative. Combat action resolution SHALL stage `grant_combat_kill_xp()` in the same atomic commit for each unique, resolved tiered monster newly reduced from positive HP to zero, using its `threat_tier`; it SHALL not award XP for non-monsters, an already-dead target, or duplicate target references. Combat upkeep settlement SHALL additionally stage exactly one `grant_combat_kill_xp()` for a tiered monster whose lethal HP crossing was caused by an attributed damaging rate tick (a buff carrying a resolvable `source_pk`), in the same combat-round transaction. An unattributed tick, a simulated (guild-exam) tick, a non-Monster target, and a target whose death was already credited by an action SHALL award no XP.

#### Scenario: A SKIP advance reaches the real study callable
- **WHEN** `WorldClock.advance` receives `AdvanceSource.SKIP` and an eligible entity
- **THEN** its magic XP increases through `accrue_magic_study()`

#### Scenario: Defeating a tiered monster awards the attacker once
- **WHEN** a successful combat action reduces a monster with `threat_tier == "low"` from positive HP to zero
- **THEN** the acting entity receives exactly one low-tier combat-kill XP award

#### Scenario: An attributed lethal rate tick awards the caster exactly once
- **WHEN** the player's `fire_scorch` tick reduces a monster with `threat_tier == "low"` from positive HP to zero during combat upkeep
- **THEN** the acting entity receives exactly one low-tier combat-kill XP award committed with that round

#### Scenario: An unattributed or simulated lethal tick awards nothing
- **WHEN** a lethal rate tick has no resolvable source, or fires inside a guild examination
- **THEN** no entity receives combat-kill XP and no progression attribute changes as a result of the tick
