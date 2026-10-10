# Spec Delta

## REMOVED Requirements

### Requirement: The new equipment roster is registered and tradeable
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Equipment membership and stocking are authored data. Retarget substantive tests in this change.

## ADDED Requirements

### Requirement: Equipment membership and stocking are authored data
Every registered equipment item SHALL bind one-to-one to a complete budget-checked effect entry and valid presentation/price metadata. Item membership and shop listings SHALL remain authored data; registration SHALL NOT imply stocking. Declared offers SHALL resolve registered items and numeric rules without a fixed approved roster, and non-sellable restrictions SHALL prevail over any listing.

#### Scenario: New complete item
- **WHEN** a valid synthetic equipment item and effect binding are added without a shop listing
- **THEN** load, grant and equip succeed without changing a roster contract

#### Scenario: Declared listing
- **WHEN** a synthetic sellable item is listed in a valid authored shop
- **THEN** ordinary purchase exposes that listing; removing it leaves the equipment valid but unoffered

#### Scenario: Military exception
- **WHEN** military E-S equipment is checked
- **THEN** the six named sword/armor pairs remain protected by military-equipment because guild examiner content depends on them; examiner-facing statements remain named

## MODIFIED Requirements

### Requirement: Church-of-Light equipment obeys its canon doctrine
Church equipment SHALL declare its liturgical role in immutable item lore independently of effect rules. Vestment/emblem roles SHALL carry non-negative exposure_bias, pleasure_gain and any heal_gain, and positive healing or immunity. Sanctuary-device roles SHALL carry non-negative exposure_bias and positive pleasure_gain without required healing. Effect entries SHALL NOT reclassify themselves to evade doctrine; ordinary combat trade-offs remain permitted.

#### Scenario: Doctrine coverage for the named Church set
- **WHEN** all item-lore vestment/emblem members are validated
- **THEN** each has non-negative exposure and pleasure modifiers and healing or immunity; ordinary combat trade-offs remain allowed

#### Scenario: Doctrine coverage for the sanctuary-device sub-set
- **WHEN** all item-lore sanctuary-device members are validated
- **THEN** each has non-negative exposure and positive pleasure modifiers; absence of healing/immunity is accepted

#### Scenario: Doctrine violation blocks a named Church item
- **WHEN** a synthetic declared Church item receives a negative pleasure modifier
- **THEN** validation fails regardless of its key or shop listing

#### Scenario: A sanctuary device may not borrow the healing exemption
- **WHEN** a deviant effect rule tries to reclassify a vestment as a sanctuary device
- **THEN** item-lore role remains authoritative and missing vestment healing/immunity fails

#### Scenario: Sanctuary-device sub-set carries pleasure-only doctrine
- **WHEN** sanctuary-device members are validated
- **THEN** each satisfies the declared device role without healing; liturgical role expresses the unchanged ministry distinction

#### Scenario: No sub-set member carries chastity-style suppression
- **WHEN** any member of either sub-set is validated
- **THEN** it carries no chastity-style suppression, meaning neither negative `pleasure_gain` nor negative `exposure_bias`
- **AND** ordinary combat trade-offs (negative `defense`, `atk_phys`, agility, etc.) remain permitted as the mechanical cost of holiness

#### Scenario: Sub-set membership is amended by name, not by tag
- **WHEN** a new Church equipment record is authored
- **THEN** its immutable item-lore role determines doctrine coverage without a named membership list in the specification


### Requirement: Registration and tradeability are independent
An equipment item SHALL be complete when it declares a slot, binds one-to-one to a budget-checked rulebook entry, and names a resolvable price band. A shop listing SHALL NOT be part of that completeness.

#### Scenario: An unstocked binding loads clean
- **WHEN** the equipment-effect rulebook is loaded with a bound, budget-checked equipment item that no shop offers
- **THEN** the load succeeds with no unbound key and no orphaned entry, and no validator reports a missing offer

#### Scenario: An unstocked piece equips and applies
- **WHEN** an unstocked equipment item is granted into inventory and equipped
- **THEN** it occupies its declared slot and its adjustments reach the shared accessor with the authored values

#### Scenario: Tradeability is a stated roster property
- **WHEN** authored shop memberships are inspected
- **THEN** offers follow current data and do not determine equipment registration completeness

#### Scenario: Unstocked items are a valid shipped state
- **WHEN** a bound, budget-checked equipment item that no shop offers ships
- **THEN** the rulebook loads and no loader or validator reports it as unbound, orphaned, or missing an offer
- **AND** it equips and applies its adjustments exactly as a stocked item of the same shape would

#### Scenario: Stocking statements follow lore provenance
- **WHEN** equipment lore and shop membership are reviewed
- **THEN** stocking is explicitly authored according to provenance; unoffered registered equipment is valid without a fixed regional roster count

