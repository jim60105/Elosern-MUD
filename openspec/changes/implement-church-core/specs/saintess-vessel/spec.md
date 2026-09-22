## REMOVED Requirements

### Requirement: saintess_vessel is a granted-only clergy qualifier passive
**Reason**: design §9.1 (owner amendment) replaces the preset-activation grant path with the church-enrollment grant path; the old block's preset-grant scenario is replaced, not duplicated.
**Migration**: superseded by the ADDED requirement 「saintess_vessel is a church-enrollment-granted clergy qualifier passive」 in this same delta; re-annotate its tests with the new identifier.

### Requirement: The oath flip and vessel grant are observable through the facade without title state
**Reason**: design §9.2 amends the title-invariant clause to sanction exactly one predicate-family extension (the church redeemed-count family), replacing the old block's "No title predicate family is added" scenario.
**Migration**: superseded by the ADDED requirement 「The oath flip stays observable through the facade and the office-name title ban holds」 in this same delta; re-annotate its tests with the new identifier.

## ADDED Requirements

### Requirement: saintess_vessel is a church-enrollment-granted clergy qualifier passive
`SKILL_REGISTRY` SHALL contain `saintess_vessel`（聖女容器）declared `kind=SkillKind.PASSIVE`, `target_spec=TargetSpec.NONE`, `usable_out_of_combat=True`, `element="light"`, `category=SkillCategory.ENHANCEMENT`, with an EMPTY effects collection (asserted by emptiness, not container type — the shipped builder defaults the omitted field to its shared frozen empty list) and no lineage prerequisites — the same qualifier-row shape as `pain_to_pleasure`, `rapture_renewal`, and `priestly_grace`. The row SHALL NOT appear in any genealogy tree, and the passive kind itself SHALL keep it unearnable: the practice-award entries and the cross-lineage unlock engine SHALL reject it exactly as they already reject PASSIVE skills. It SHALL NOT be conferrable (`validate_conferrable_skill` accepts only stat-multiply/rule-table shaped rows and the vessel carries neither), joining the same non-conferrable qualifier class as the other three clergy passives. The ONLY production path that places it on an entity is the church enrollment transaction of a female `human_royal` character — the enrollment grant replaces the former preset-activation grant (the shipped `violet_altoria` preset's `passive_skills` SHALL NOT include `saintess_vessel`), there is no office uniqueness (every eligible royal who enrolls becomes a saintess; no global office state exists), and the vessel SHALL NEVER be a redemption-catalogue row at any price (negative-set pinned). The PASSIVE guards, the granted-only character, and the granted-event observability are unchanged: the enrollment transaction reuses the same canonical granted-passive write path and the same `saintess_vessel_granted` event.

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

### Requirement: The oath flip stays observable through the facade and the office-name title ban holds
The irreversible flip of the `virgin` flag by the `first_vaginal_penetration` event, for an entity owning `saintess_vessel`, SHALL emit exactly one `saintess_oath_broken` observability event through the `world.observability` facade, registered through the transaction-commit seam so a rolled-back transaction emits nothing, with a plain-data context carrying at least the entity identifier and the event name. A non-holder's flag flip SHALL emit no `saintess_oath_broken` event. The flip SHALL NOT create, bank, remove, or mutate any title state, and the title-system's bank path, removal path, and fixed-title rows SHALL be unchanged by this capability; the 聖女 title remains narrative identity prose read alongside the stored `virgin` flag. The `TitlePredicateFamily` closed set SHALL be extended by at most one member — the church redeemed-count family (a count of redeemed church-catalogue skills which by construction can never reference the vessel, since the vessel never enters the redeemed set), landed by the sibling order-catalogue change; the extension is what this amendment sanctions, and until that change lands the family set stays unchanged — and no predicate family beyond it SHALL be added. The office-name ban is reaffirmed unchanged: no church fixed-title row SHALL display 聖女.

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

#### Scenario: The only sanctioned predicate-family extension is the church redemption count
- **WHEN** `TitlePredicateFamily` members and fixed-title registry rows are enumerated at this capability's landing and after the sibling order-catalogue change lands
- **THEN** the family set differs from the pre-church set by at most the church redeemed-count family and nothing else, the title bank and removal paths are unchanged, and no fixed-title row — church or otherwise — names the Saintess office
