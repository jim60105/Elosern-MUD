# saintess-vessel Specification

## Purpose
Defines the 聖女容器 (`saintess_vessel`) passive: the 劇情/聖職敘階-granted Saintess vessel whose 聖光涓流 keeps her arousal idling in the 微興奮～中等 band on the world clock, whose two named public blessing ceremonies each read her excitement tier exactly once, and whose boundary transitions are recorded through the observability facade.

## Requirements

### Requirement: saintess_vessel is a granted-only clergy qualifier passive
`SKILL_REGISTRY` SHALL contain `saintess_vessel`（聖女容器）declared `kind=SkillKind.PASSIVE`, `target_spec=TargetSpec.NONE`, `usable_out_of_combat=True`, `element="light"`, `category=SkillCategory.ENHANCEMENT`, with an EMPTY effects collection (asserted by emptiness, not container type — the shipped builder defaults the omitted field to its shared frozen empty list) and no lineage prerequisites — the same qualifier-row shape as `pain_to_pleasure`, `rapture_renewal`, and `priestly_grace`. The row SHALL NOT appear in any genealogy tree, and the passive kind itself SHALL keep it unearnable: the practice-award entries and the cross-lineage unlock engine SHALL reject it exactly as they already reject PASSIVE skills. It SHALL NOT be conferrable (`validate_conferrable_skill` accepts only stat-multiply/rule-table shaped rows and the vessel carries neither), joining the same non-conferrable qualifier class as the other three clergy passives. The ONLY production paths that place it on an entity are preset activation (`passive_skills`) and an import record. The shipped Saintess preset's `passive_skills` SHALL include `saintess_vessel`.

#### Scenario: The vessel row exists with the clergy qualifier shape
- **WHEN** `SKILL_REGISTRY["saintess_vessel"]` is read
- **THEN** it is a PASSIVE light-attribute ENHANCEMENT skill with `TargetSpec.NONE`, an empty effects collection, and no prerequisites, and its label and description are non-empty Traditional Chinese strings

#### Scenario: The vessel is not reachable by practice or lineage
- **WHEN** a practice award (use-driven or booked study) names `saintess_vessel`, or the cross-lineage unlock engine is offered a rule whose source is a PASSIVE node
- **THEN** each rejects the key through the pre-existing PASSIVE guards, and no shipped lineage graph or unlock rule names it

#### Scenario: The vessel cannot be conferred
- **WHEN** `validate_conferrable_skill` is called with `saintess_vessel`
- **THEN** it raises, exactly as it does for `pain_to_pleasure`

#### Scenario: The shipped Saintess preset carries the vessel at activation
- **WHEN** the Saintess preset is activated and its activation transaction commits
- **THEN** her stored passive skill list contains `saintess_vessel` and exactly one `saintess_vessel_granted` observability event is emitted at commit

### Requirement: Saintess trickle pins the holder's idle arousal inside the idle band
For an entity owning `saintess_vessel`, the world-clock settlement SHALL guarantee that after any settlement step the entity's pleasure is never below the 微興奮 floor (15) while the holder sits below the 中等/高度 boundary behavior defined below. Concretely, all writes through the sanctioned `world/rules/` pleasure writers only (never a typeclass, AI, or presentation module):

1. The pleasure decay step's floor for a holder is the 微興奮 floor: `decay_tick` targets `max(15, band_floor − 1)` and a holder at or below 15 with decay due is a no-op.
2. Once per world-clock `advance()` with `seconds > 0` (NOT per settlement quantum), for every settled non-combat-sourced scope, an entity below 15 is raised to exactly 15 via `apply_pleasure_gain(..., stimulus=False)`.
3. An entity inside [15, 59] receives exactly one deterministic ±1 step per advance whose direction is a stateless hash of the FULL resulting world tick and the entity identity (a rolled-back, retried advance recomputes the identical direction; no RNG is consumed; raw tick parity is refuted — every shipped non-combat advance duration is even, so the draw would freeze per entity), with the result clamped so the gauge never leaves [15, 59] and a clamped-to-zero delta issuing no writer call.
4. An entity at or above 60 is left untouched; ordinary decay owns the descent and steps 2–3 re-arm when the gauge re-enters the band.

All trickle writes carry the sanctioned writer's explicit non-stimulus policy: the gauge write and the wetness-on-band-up cascade apply, while the climax-phase edges (接近→進行中, 極限→接近) and extension staging NEVER fire — the idle fluctuation must not autonomously open a climax below the 85 gate for a holder parked at 接近. A holder resting at the floor therefore stays never-below-15 with at most ±1 movement per advance — its arousal level never leaves 微興奮～中等. An entity that does not own `saintess_vessel` SHALL decay and settle byte-for-byte exactly as before this change.

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

### Requirement: Each named public blessing ceremony reads the holder's excitement tier exactly once
`world/rules/rulebook/combat_modifiers.yaml` SHALL carry two distinct vessel rows and no others: (a) `blessing_arousal_scale: 0.1` gated on `skill_owned: saintess_vessel` — a key deliberately distinct from `priestly_grace`'s `recovery_arousal_scale` because same-key numerics ADD at merge — and (b) a grace row gated on `skill_owned: saintess_vessel` together with `buff_active: light_blessing` and `field: arousal, gte: 中等`, granting a flat defense +6 (the established arousal-tier 恩典 pattern). The cast-time recovery grace snapshot SHALL fold `1 + max(recovery_arousal_scale, blessing_arousal_scale) × cast-time arousal ordinal`, so the `sanctified_ward` HOT mounted from a vessel-holder cast carries grace exactly `1 + 0.1 × ordinal` whether she holds `saintess_vessel` alone, `priestly_grace` alone, or both — never `1 + 0.2 × ordinal`. The authored `goddess_blessing` numbers (heal coefficient 2.8, `light_blessing` defense +18/60 s) SHALL stay byte-identical; the vessel's second ceremonial read stacks as an independent status-sourced +6 on the live blessing, and `light_blessing` SHALL NOT gain a recovery profile.

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

### Requirement: The vessel adds no combat numbers beyond the two ceremonial reads
The vessel's rulebook rows SHALL carry exactly the `blessing_arousal_scale` value and the tier-gated blessing-defense grace value. Owning the vessel SHALL change the merged combat-modifier bundle ONLY by those two keys, and the grace row SHALL NOT match unless the holder's own `light_blessing` instance is active.

#### Scenario: The merged bundle of a resting holder carries only the ceremonial scale
- **WHEN** `evaluate_combat_modifiers` is evaluated for a vessel holder who owns no other modifier-bearing skill, buff, or equipment and has no active blessing
- **THEN** the merged bundle contains exactly `blessing_arousal_scale` and no numeric combat axis

### Requirement: The oath flip and vessel grant are observable through the facade without title state
The irreversible flip of the `virgin` flag by the `first_vaginal_penetration` event, for an entity owning `saintess_vessel`, SHALL emit exactly one `saintess_oath_broken` observability event through the `world.observability` facade, registered through the transaction-commit seam so a rolled-back transaction emits nothing, with a plain-data context carrying at least the entity identifier and the event name. A non-holder's flag flip SHALL emit no `saintess_oath_broken` event. The flip SHALL NOT create, bank, remove, or mutate any title state, and the title-system's predicate families, bank path, removal path, and fixed-title rows SHALL be unchanged by this capability; the 聖女 title remains narrative identity prose read alongside the stored `virgin` flag.

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

#### Scenario: No title predicate family is added
- **WHEN** `TitlePredicateFamily` members and fixed-title registry rows are enumerated after this capability ships
- **THEN** both sets are unchanged and no fixed-title row names the Saintess office
