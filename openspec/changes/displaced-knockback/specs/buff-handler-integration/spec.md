## MODIFIED Requirements

### Requirement: Buff definitions configure a subset of rate of change, clamped bounds, and decay rate
— never a combat-stat multiplier
`world/rules/rulebook/buffs.yaml` SHALL define each buff's tunable parameters (duration, tick interval, stacking policy, and a `modifiers` mapping using at most the keys `rate`, `bounds`, `divert`, and `decay`) with rate choosing either a fixed delta or a validated recovery profile (never both), per design doc §6.4's exhaustive list of what a buff may modify. A buff definition SHALL NOT configure a combat-stat multiplier (`atk_phys`/`agility`/`defense` scaling) — that remains the combat-modifier/`SkillHandler.effective_value()` territory. A buff MAY declare an empty `modifiers` mapping when its sole purpose is being detectable as present (a marker buff). A `divert` modifier SHALL be validated fail-closed at load: its `target` must be a gauge key, its `fraction` a finite number in (0, 1], its `cap` a positive integer, and the row must carry a finite duration; malformed divert rows SHALL make the buff-definition load fail with the offending key named. A fixed-delta `rate` modifier targeting `hp` with a negative delta MAY additionally declare one `caster_share` transfer clause: a finite number in (0, 1] naming the fraction of each tick's actual HP loss credited to the buff's origin caster. The clause SHALL be validated fail-closed at load — rejected on a non-`hp` rate target, on a non-negative delta, on a boolean or non-finite or out-of-range value, and on any co-declaration with a `recovery` or `scale_from_source` rate — the offending definition key SHALL be named and the load SHALL fail. Rows without the clause SHALL keep ticking exactly as before. Additionally, a definition MAY carry one top-level `marker` clause outside `modifiers` whose value belongs to the closed marker vocabulary — now `ground` or `positional`; a malformed value SHALL fail the load naming the offending definition key, and every row without the clause SHALL load bit-identically to its pre-clause behavior. The public buff-application entry point SHALL, for a definition declaring the `positional` marker value, first remove the recipient's live `ground`-marker instances through the existing scoped removal path before mounting (zero damage or revive side effects, non-marker instances untouched), and SHALL refuse the mount entirely on an entity that is defeated (hp ≤ 0) or recorded fled or knocked-out in its active combat session; both behaviors SHALL consult only the marker clause and SHALL NOT change the mount semantics of any ground or non-marker row.

#### Scenario: A rate-of-change buff definition is well-formed
- **WHEN** `buffs.yaml`'s `poisoned` definition is inspected
- **THEN** its `modifiers` mapping contains a `rate` key naming a target field and a per-tick delta, and contains neither `bounds` nor a combat-stat-multiplier key

#### Scenario: A marker-only buff definition has an empty modifiers mapping
- **WHEN** `buffs.yaml`'s `paralysis` and `fear` definitions are inspected
- **THEN** each has an empty `modifiers` mapping, and each is still loadable and applyable via `BuffHandler`

#### Scenario: No buff definition configures a combat-stat multiplier
- **WHEN** every entry in `buffs.yaml` is inspected
- **THEN** none contains a `modifiers` key resembling a multiplicative combat-stat scale (e.g. `atk_phys_multiplier`); combat-facing consequences of a buff's presence are expressed exclusively through the validated modifier vocabulary

#### Scenario: A divert-profile buff definition is well-formed and malformed ones fail closed
- **WHEN** a synthetic divert row (gauge target, fraction in (0,1], positive cap, finite duration) is loaded, and separately rows with a fraction of 1.5, a zero/negative cap, a non-gauge target, or a null duration are loaded
- **THEN** the well-formed row loads as a divert-capable definition and each malformed row raises at load time naming the offending definition key

#### Scenario: A caster-share clause loads only on a damaging hp rate row
- **WHEN** a synthetic hp-target negative-delta rate row declaring `caster_share` in (0, 1] is loaded
- **THEN** the definition loads carrying the validated share

#### Scenario: Every misplaced caster-share clause fails the load closed
- **WHEN** rows declaring `caster_share` on an mp-target rate, on a non-negative hp delta, on a recovery-profile rate, on a `scale_from_source` rate, or with a boolean, zero, negative, greater than one, or non-finite value are loaded
- **THEN** each raises at load time naming the offending definition key and no definition is produced

#### Scenario: A marker clause loads only with a vocabulary value
- **WHEN** a synthetic row declaring the closed-vocabulary ground marker value is loaded, and separately rows declaring the positional marker value, an element name, a boolean, or a number as the marker value are loaded
- **THEN** each well-formed row (ground and positional) loads carrying the validated marker clause and each malformed row raises at load time naming the offending definition key

#### Scenario: Mounting a positional row sweeps ground markers at the entry point
- **WHEN** the public entry point applies a synthetic positional row to an entity holding a live synthetic ground-marker instance plus an ordinary timed buff
- **THEN** the ground instance is removed first with no damage or revive side effects, the ordinary buff is untouched, and the positional instance mounts live

#### Scenario: The positional mount refuses impossible recipients
- **WHEN** the public entry point applies a synthetic positional row to a defeated, fled, or knocked-out entity
- **THEN** nothing is written for any of the three, while the identical call on a living still-fighting entity mounts the instance
