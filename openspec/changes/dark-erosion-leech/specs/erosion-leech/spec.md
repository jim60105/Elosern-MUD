## ADDED Requirements

### Requirement: A damaging hp rate tick credits its origin caster through one clamped exactly-once leg
A buff definition whose fixed-delta `rate` modifier targets `hp` with a negative delta and declares a
validated `caster_share` clause SHALL, on each tick, credit the buff's origin caster HP equal to
`floor(actual_loss × caster_share)`, where `actual_loss` is the victim's HP actually removed by that
tick after clamping — never the nominal delta. The credit SHALL be paid in the same tick pass,
SHALL increase (never decrease) the caster's HP, SHALL clamp at the caster's HP maximum, SHALL
dispatch no further outcome events (no `hp_loss`, no reaction re-entry on either party), and SHALL
leave the victim's existing single `hp_loss` dispatch and the combat round's tick-record settlement
exactly as they are. A row without the clause SHALL tick bit-identically to its pre-clause behavior.
The mechanism SHALL read no element, skill or buff-key identity — any element's damaging hp rate row
may declare it.

#### Scenario: Full-share erosion tick moves the actual loss to the caster
- **WHEN** a synthetic hp rate row with `caster_share: 1.0` applied by a living caster ticks a victim
  holding more HP than the delta
- **THEN** the victim loses exactly the delta, the caster gains exactly that amount, and exactly one
  `hp_loss` outcome fires — for the victim only

#### Scenario: A floor-bound tick credits only what actually left
- **WHEN** a share-bearing tick's nominal delta exceeds the victim's remaining HP above zero
- **THEN** the caster gains exactly the HP actually removed before the zero floor and nothing for the
  remainder, and no second settlement or credit is produced for the crossing

#### Scenario: A dead origin caster is silently skipped
- **WHEN** the origin caster's HP is zero at a share-bearing tick
- **THEN** the victim still loses the tick's HP, the dead caster gains nothing and is not revived, and
  the tick otherwise behaves unchanged

#### Scenario: The credit clamps at the caster's maximum without spill
- **WHEN** a share-bearing tick would push a wounded origin caster above their HP maximum
- **THEN** the caster lands exactly at maximum and no other entity or gauge changes

#### Scenario: The victim's reactions fire once per tick
- **WHEN** a share-bearing tick fires a victim-side reaction rule on the `hp_loss` outcome
- **THEN** the rule executes exactly once for that tick and the caster credit leg triggers no reaction
  dispatch on either party

#### Scenario: A non-share row is untouched by the mechanism
- **WHEN** `poisoned`-shaped (no `caster_share`) hp rate ticks settle alongside a share-bearing row
- **THEN** the non-share row's victim and any other entity change exactly as before the clause
  existed

### Requirement: Leech origin is the grant-time snapshot and extinguishes with either party
The credit recipient SHALL be resolved from the buff cache's persisted grant-time source identity —
never from any caller-supplied field and never re-derived at tick time from anything but that stored
identity. Re-application by a different caster SHALL redirect subsequent ticks' credit to the newest
applier exactly as the shipped damaging-buff source-replacement contract already replaces the cached
source, while a refresh carrying no new source SHALL retain the previous one. Credit SHALL extinguish
— with zero writes and no errors — when the buff instance expires, is dispelled or cleansed, when the
victim dies, or when the origin caster is dead or unresolvable; the victim's tick damage itself SHALL
be unaffected by extinguishment.

#### Scenario: Refresh redirects the origin to the newest applier
- **WHEN** caster B re-applies the same share-bearing erosion key caster A applied, before expiry
- **THEN** the next tick credits B, and a refresh that supplies no new source keeps crediting A

#### Scenario: Expiry and dispel end the credit
- **WHEN** the share-bearing buff expires by elapsed game seconds or is removed by a cleanse, then the
  victim continues to lose HP from another source
- **THEN** the former origin caster gains nothing from any later loss

#### Scenario: A dead or unresolvable origin stops crediting without stopping the tick
- **WHEN** the origin entity is deleted or otherwise unresolvable while the victim keeps ticking
- **THEN** the victim keeps losing HP at the configured rate, no credit is paid, and no exception or
  fabricated entity appears

#### Scenario: Caller data cannot spoof the origin
- **WHEN** a direct caller attempts to apply the share-bearing buff with cache data naming a different
  source identity than the resolving actor
- **THEN** the persisted origin remains the actor-derived identity the shipped attribution contract
  establishes, and credit follows it
