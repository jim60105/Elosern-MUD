# saintess-vessel Specification

## Purpose
Defines the 聖女容器 (`saintess_vessel`) passive: the church-enrollment-granted Saintess vessel whose 聖光涓流 keeps her arousal idling in the 微興奮～中等 band on the world clock, whose two named public blessing ceremonies each read her excitement tier exactly once, and whose boundary transitions are recorded through the observability facade.

## Requirements

### Requirement: saintess_vessel is a church-enrollment-granted clergy qualifier passive
`SKILL_REGISTRY` SHALL contain `saintess_vessel`（聖女容器）declared `kind=SkillKind.PASSIVE`, `target_spec=TargetSpec.NONE`, `usable_out_of_combat=True`, `element="light"`, `category=SkillCategory.ENHANCEMENT`, with an EMPTY effects collection and no lineage prerequisites. The ONLY production path that places it on an entity is the church enrollment transaction of a female `human_royal` character, and the vessel SHALL NEVER be a redemption-catalogue row at any price.

#### Scenario: The vessel row exists with the clergy qualifier shape
- **WHEN** `SKILL_REGISTRY["saintess_vessel"]` is read
- **THEN** it is a PASSIVE light-attribute ENHANCEMENT skill with `TargetSpec.NONE`, an empty effects collection, and no prerequisites, and its label and description are non-empty Traditional Chinese strings

#### Scenario: The vessel is not reachable by practice or lineage
- **WHEN** a practice award (use-driven or booked study) names `saintess_vessel`, or the cross-lineage unlock engine is offered a rule whose source is a PASSIVE node
- **THEN** each rejects the key through the pre-existing PASSIVE guards, and no shipped lineage graph or unlock rule names it

#### Scenario: The vessel cannot be conferred
- **WHEN** `validate_conferrable_skill` is called with `saintess_vessel`
- **THEN** it raises, exactly as it does for `pain_to_pleasure`

#### Scenario: Church enrollment by a female royal is the sole grant path
- **WHEN** a female `human_royal` character's church enrollment transaction commits
- **THEN** her stored passive skill list contains `saintess_vessel` and exactly one `saintess_vessel_granted` observability event is emitted at that commit, and activating the shipped preset grants neither the vessel nor the event

#### Scenario: No other initiate is granted the vessel
- **WHEN** an initiate of any other subrace, or a male `human_royal`, enrolls
- **THEN** no `saintess_vessel` grant or granted event occurs

#### Scenario: There is no office uniqueness
- **WHEN** two distinct female `human_royal` characters each complete enrollment
- **THEN** both hold the vessel; nothing tracks or caps a global office holder

#### Scenario: The vessel is never purchasable
- **WHEN** the church redemption catalogue is enumerated
- **THEN** `saintess_vessel` is absent at every price, permanently

#### Scenario: The row carries the clergy qualifier shape with an empty-by-emptiness effects collection
- **WHEN** the vessel's registered effects collection and row shape are inspected
- **THEN** effects emptiness is asserted by emptiness, not container type — the shipped builder defaults the omitted field to its shared frozen empty list — and the row is the same qualifier-row shape as `pain_to_pleasure`, `rapture_renewal`, and `priestly_grace`

#### Scenario: The redemption-catalogue absence is negative-set pinned
- **WHEN** the assertion pinning the vessel out of the church redemption catalogue is inspected
- **THEN** the absence is pinned as a negative set, permanently at every price

#### Scenario: The vessel appears in no genealogy tree and stays unearnable by kind
- **WHEN** every shipped genealogy tree is enumerated and the practice-award entries or the cross-lineage unlock engine are offered `saintess_vessel`
- **THEN** the row appears in no genealogy tree, and the passive kind itself keeps it unearnable: each rejects it exactly as they already reject PASSIVE skills

#### Scenario: The vessel joins the non-conferrable clergy qualifier class
- **WHEN** `validate_conferrable_skill` evaluates `saintess_vessel`
- **THEN** it rejects because the validator accepts only stat-multiply/rule-table shaped rows and the vessel carries neither, joining the same non-conferrable qualifier class as the other three clergy passives

#### Scenario: The enrollment grant replaces the preset-activation grant through unchanged machinery
- **WHEN** the shipped `violet_altoria` preset's `passive_skills` and the enrollment write path are inspected
- **THEN** the preset's `passive_skills` do not include `saintess_vessel`, and the enrollment transaction reuses the same canonical granted-passive write path and the same `saintess_vessel_granted` event — the PASSIVE guards, the granted-only character, and the granted-event observability are unchanged

#### Scenario: Office uniqueness does not exist
- **WHEN** every eligible royal completes enrollment
- **THEN** each becomes a saintess and no global office state exists

### Requirement: Saintess trickle pins the holder's idle arousal inside the idle band
For an entity owning `saintess_vessel`, the world-clock settlement SHALL guarantee that after any settlement step the entity's pleasure is never below the 微興奮 floor (15) while the holder sits below the 中等/高度 boundary, and all trickle writes go through the sanctioned `world/rules/` pleasure writers only, never a typeclass, AI, or presentation module. The holder's arousal level therefore never leaves 微興奮～中等, and a non-holder SHALL decay and settle byte-for-byte exactly as before this change.

#### Scenario: A completely idle holder at zero is pinned up in one advance
- **WHEN** a vessel holder with pleasure 0 and no buffs or other pending settlement work is settled by one world-clock advance
- **THEN** her pleasure reads exactly 15 after the advance (the pin runs even though the quantum decay loop has no pending work to do)

#### Scenario: The band oscillation stays inside [15, 59] and visibly moves
- **WHEN** a vessel holder with pleasure 30 is settled by many successive advances
- **THEN** every reading stays within [15, 59], successive readings differ by at most 1 per advance, and at least one reading differs from 30

#### Scenario: Decay cannot push a holder out of the band
- **WHEN** a vessel holder inside the band is advanced longer than the pleasure decay interval
- **THEN** her pleasure never falls below 15 and her arousal level never reads 平靜

#### Scenario: A holder at or above 高度 is left to ordinary decay
- **WHEN** a vessel holder with pleasure 70 (高度) is settled after more than one decay interval
- **THEN** the trickle adds nothing, ordinary decay applies, and the pin/oscillation resume only once the gauge re-enters [15, 59]

#### Scenario: A retried failed advance recomputes the identical step
- **WHEN** a world-clock advance for a mid-band holder is forced to fail after the trickle step and is retried with the same inputs
- **THEN** both attempts compute the same fluctuation direction and the restored holder's pleasure equals the single-apply value

#### Scenario: The idle trickle never opens a climax
- **WHEN** a holder whose climax phase rests at 接近 (left there by an earlier 極限 spike) is settled by repeated advances inside [15, 59]
- **THEN** the phase never reads 進行中 and no extension is staged

#### Scenario: Non-holders are byte-identical
- **WHEN** a non-holder with pleasure 20 is settled over the same advances
- **THEN** she receives no fluctuation, no pin, and her decay follows the unchanged 平靜-floor behavior

#### Scenario: The holder's decay floor is the 微興奮 floor
- **WHEN** the pleasure decay step runs for a vessel holder
- **THEN** `decay_tick` targets `max(15, band_floor − 1)` and a holder at or below 15 with decay due is a no-op

#### Scenario: The pin runs once per advance over settled non-combat scopes
- **WHEN** one world-clock `advance()` with `seconds > 0` settles non-combat-sourced scopes containing entities below 15
- **THEN** each such entity is raised to exactly 15 via `apply_pleasure_gain(..., stimulus=False)`, once per `advance()` and NOT per settlement quantum

#### Scenario: The band step is a deterministic stateless hash draw
- **WHEN** a vessel holder inside [15, 59] is settled by one advance
- **THEN** she receives exactly one ±1 step whose direction is a stateless hash of the FULL resulting world tick and the entity identity — no RNG is consumed, and raw tick parity is refuted as the draw source because every shipped non-combat advance duration is even and the draw would freeze per entity
- **AND** the result is clamped so the gauge never leaves [15, 59], and a clamped-to-zero delta issues no writer call

#### Scenario: The trickle leaves an entity at or above 60 untouched
- **WHEN** a vessel holder's gauge reads 60 or above at settlement
- **THEN** the trickle touches nothing, ordinary decay owns the descent, and the pin and band step re-arm only when the gauge re-enters the band

#### Scenario: Trickle writes carry the writer's explicit non-stimulus policy
- **WHEN** a trickle write lands on a holder
- **THEN** the sanctioned writer's explicit non-stimulus policy applies: the gauge write and the wetness-on-band-up cascade apply, while the climax-phase edges (接近→進行中, 極限→接近) and extension staging NEVER fire — the idle fluctuation must not autonomously open a climax below the 85 gate for a holder parked at 接近

#### Scenario: A holder resting at the floor stays pinned with at most ±1 movement
- **WHEN** a vessel holder rests at the 微興奮 floor across advances
- **THEN** she stays never-below-15 with at most ±1 movement per advance

### Requirement: Each named public blessing ceremony reads the holder's excitement tier exactly once
`world/rules/rulebook/combat_modifiers.yaml` SHALL carry two distinct vessel rows and no others: (a) `blessing_arousal_scale: 0.1` gated on `skill_owned: saintess_vessel`, and (b) a grace row gated on `skill_owned: saintess_vessel` together with `buff_active: light_blessing` and `field: arousal, gte: 中等`, granting a flat defense +6. The cast-time recovery grace snapshot SHALL fold `1 + max(recovery_arousal_scale, blessing_arousal_scale) × cast-time arousal ordinal`.

#### Scenario: The vessel alone reads the tier on a ward cast
- **WHEN** a holder of `saintess_vessel` only, at arousal ordinal 2 (中等), casts `sanctified_ward`
- **THEN** the mounted buff instance's grace multiplier is 1.2

#### Scenario: Holding both clergy passives does not double the read
- **WHEN** a holder of both `saintess_vessel` and `priestly_grace`, at arousal ordinal 2, casts `sanctified_ward`
- **THEN** the mounted grace multiplier is still 1.2, not 1.4

#### Scenario: priestly_grace alone is unchanged
- **WHEN** a holder of `priestly_grace` only, at arousal ordinal 3, casts `sanctified_ward`
- **THEN** the mounted grace multiplier is 1.3 exactly as before this change

#### Scenario: The goddess blessing ceremony reads the tier through its own grace row
- **WHEN** a vessel holder at arousal 中等 or above has her own `light_blessing` live
- **THEN** the merged defense bundle carries the authored +18 plus the vessel's independent +6, both listed as separately matched status-sourced conditions, and at arousal 微興奮 the +6 row does not match
- **AND** the authored +18 rule row is unchanged

#### Scenario: A non-holder casts either ceremony plainly
- **WHEN** a caster owning neither clergy passive casts `sanctified_ward` or `goddess_blessing`
- **THEN** the ward mounts grace 1.0 and the blessing mounts only the authored +18

#### Scenario: The scale key is deliberately distinct from priestly_grace's key
- **WHEN** the vessel's arousal-scale key is compared against `priestly_grace`'s `recovery_arousal_scale`
- **THEN** the keys differ deliberately, because same-key numerics ADD at merge

#### Scenario: The +6 grace row follows the established 恩典 pattern
- **WHEN** the vessel's tier-gated blessing-defense row is authored
- **THEN** it grants the flat defense +6 in the established arousal-tier 恩典 pattern

#### Scenario: The ward grace stays 0.1-scaled under every clergy holding
- **WHEN** a vessel holder casts `sanctified_ward` holding `saintess_vessel` alone, `priestly_grace` alone, or both
- **THEN** the mounted `sanctified_ward` HOT carries grace exactly `1 + 0.1 × ordinal` in all three cases — never `1 + 0.2 × ordinal`

#### Scenario: The authored goddess_blessing numbers stay byte-identical
- **WHEN** the authored `goddess_blessing` numbers are compared against the pre-change rulebook
- **THEN** the heal coefficient 2.8 and the `light_blessing` defense +18/60 s are byte-identical

#### Scenario: The second ceremonial read stacks independently and adds no recovery profile
- **WHEN** the vessel's second ceremonial read lands on a live `light_blessing`
- **THEN** it stacks as an independent status-sourced +6, and `light_blessing` SHALL NOT gain a recovery profile

### Requirement: The vessel adds no combat numbers beyond the two ceremonial reads
The vessel's rulebook rows SHALL carry exactly the `blessing_arousal_scale` value and the tier-gated blessing-defense grace value. Owning the vessel SHALL change the merged combat-modifier bundle ONLY by those two keys, and the grace row SHALL NOT match unless the holder's own `light_blessing` instance is active.

#### Scenario: The merged bundle of a resting holder carries only the ceremonial scale
- **WHEN** `evaluate_combat_modifiers` is evaluated for a vessel holder who owns no other modifier-bearing skill, buff, or equipment and has no active blessing
- **THEN** the merged bundle contains exactly `blessing_arousal_scale` and no numeric combat axis

### Requirement: The oath flip stays observable through the facade and the office-name title ban holds
The irreversible flip of the `virgin` flag by the `first_vaginal_penetration` event, for an entity owning `saintess_vessel`, SHALL emit exactly one `saintess_oath_broken` observability event through the `world.observability` facade, registered through the transaction-commit seam so a rolled-back transaction emits nothing. A non-holder's flag flip SHALL emit no `saintess_oath_broken` event, and the flip SHALL NOT create, bank, remove, or mutate any title state.

#### Scenario: A holder's oath flip logs exactly once at commit
- **WHEN** a vessel holder's `virgin` flag flips via the `first_vaginal_penetration` rulebook event and the enclosing transaction commits
- **THEN** exactly one `saintess_oath_broken` log event is emitted with entity and event context, and her `title_collection` and `title_equipped` state are byte-identical to before

#### Scenario: A rolled-back transition emits nothing
- **WHEN** the transaction carrying a holder's oath flip is rolled back
- **THEN** no `saintess_oath_broken` event is emitted

#### Scenario: A non-holder's virginity flip is not a Saintess oath event
- **WHEN** an entity without `saintess_vessel` suffers the same flag flip
- **THEN** no `saintess_oath_broken` event is emitted

#### Scenario: Repeat events never re-emit
- **WHEN** `first_vaginal_penetration` fires again for an entity whose flag is already false
- **THEN** the rule's irreversibility yields no state change and no further oath event

#### Scenario: The oath event context is plain data
- **WHEN** a holder's oath event is emitted
- **THEN** its context is plain data carrying at least the entity identifier and the event name

#### Scenario: The only sanctioned predicate-family extension is the church redemption count
- **WHEN** `TitlePredicateFamily` members and fixed-title registry rows are enumerated at this capability's landing and after the sibling order-catalogue change lands
- **THEN** the family set differs from the pre-church set by at most the church redeemed-count family and nothing else, the title bank and removal paths are unchanged, and no fixed-title row — church or otherwise — names the Saintess office

#### Scenario: The title system is untouched and the 聖女 title stays narrative prose
- **WHEN** the title-system's bank path, removal path, and fixed-title rows are compared against the pre-capability state
- **THEN** all are unchanged by this capability, and the 聖女 title remains narrative identity prose read alongside the stored `virgin` flag

#### Scenario: The sanctioned predicate-family extension can never reference the vessel
- **WHEN** the church redeemed-count predicate family landed by the sibling order-catalogue change is considered — a count of redeemed church-catalogue skills
- **THEN** it by construction can never reference the vessel, since the vessel never enters the redeemed set; the extension is what this amendment sanctions, and until that change lands the `TitlePredicateFamily` closed set stays unchanged with no predicate family beyond it added

#### Scenario: The office-name ban is reaffirmed globally
- **WHEN** every fixed-title registry row of ANY category is enumerated
- **THEN** no row displays or otherwise names the 聖女 office, and the office-name ban is reaffirmed unchanged and stays global