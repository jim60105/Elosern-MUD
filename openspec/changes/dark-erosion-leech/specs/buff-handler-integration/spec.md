## MODIFIED Requirements

### Requirement: Buff definitions configure a subset of rate of change, clamped bounds, and decay rate
— never a combat-stat multiplier
`world/rules/rulebook/buffs.yaml` SHALL define each buff's tunable parameters (duration, tick interval,
stacking policy, and a `modifiers` mapping using at most the keys `rate`, `bounds`, `divert`, and
`decay`) with rate choosing either a fixed delta or a validated recovery profile (never both), per
design doc §6.4's exhaustive list of what a buff may modify. A buff definition SHALL NOT configure a
combat-stat multiplier (`atk_phys`/`agility`/`defense` scaling) — that remains the combat-modifier/`SkillHandler.effective_value()`
territory. A buff MAY declare an empty `modifiers` mapping when its
sole purpose is being detectable as present (a marker buff). A `divert` modifier SHALL be validated
fail-closed at load: its `target` must be a gauge key, its `fraction` a finite number in (0, 1], its
`cap` a positive integer, and the row must carry a finite duration; malformed divert rows SHALL make
the buff-definition load fail with the offending key named. A fixed-delta `rate` modifier targeting
`hp` with a negative delta MAY additionally declare one `caster_share` transfer clause: a finite
number in (0, 1] naming the fraction of each tick's actual HP loss credited to the buff's origin
caster. The clause SHALL be validated fail-closed at load — rejected on a non-`hp` rate target, on a
non-negative delta, on a boolean or non-finite or out-of-range value, and on any co-declaration with
a `recovery` or `scale_from_source` rate — the offending definition key SHALL be named and the load
SHALL fail. Rows without the clause SHALL keep ticking exactly as before.

#### Scenario: A rate-of-change buff definition is well-formed
- **WHEN** `buffs.yaml`'s `poisoned` definition is inspected
- **THEN** its `modifiers` mapping contains a `rate` key naming a target field and a per-tick delta, and
  contains neither `bounds` nor a combat-stat-multiplier key

#### Scenario: A marker-only buff definition has an empty modifiers mapping
- **WHEN** `buffs.yaml`'s `paralysis` and `fear` definitions are inspected
- **THEN** each has an empty `modifiers` mapping, and each is still loadable and applyable via
  `BuffHandler`

#### Scenario: No buff definition configures a combat-stat multiplier
- **WHEN** every entry in `buffs.yaml` is inspected
- **THEN** none contains a `modifiers` key resembling a multiplicative combat-stat scale (e.g.
  `atk_phys_multiplier`); combat-facing consequences of a buff's presence are expressed exclusively
  through the validated modifier vocabulary

#### Scenario: A divert-profile buff definition is well-formed and malformed ones fail closed
- **WHEN** a synthetic divert row (gauge target, fraction in (0,1], positive cap, finite duration) is
  loaded, and separately rows with a fraction of 1.5, a zero/negative cap, a non-gauge target, or a
  null duration are loaded
- **THEN** the well-formed row loads as a divert-capable definition and each malformed row raises at
  load time naming the offending definition key

#### Scenario: A caster-share clause loads only on a damaging hp rate row
- **WHEN** a synthetic hp-target negative-delta rate row declaring `caster_share` in (0, 1] is loaded
- **THEN** the definition loads carrying the validated share

#### Scenario: Every misplaced caster-share clause fails the load closed
- **WHEN** rows declaring `caster_share` on an mp-target rate, on a non-negative hp delta, on a
  recovery-profile rate, on a `scale_from_source` rate, or with a boolean, zero, negative, greater
  than one, or non-finite value are loaded
- **THEN** each raises at load time naming the offending definition key and no definition is
  produced
