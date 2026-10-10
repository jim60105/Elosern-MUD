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