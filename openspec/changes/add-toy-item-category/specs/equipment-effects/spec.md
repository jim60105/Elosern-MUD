## MODIFIED Requirements

### Requirement: Church-of-Light equipment obeys its canon doctrine
The named 光明教會 equipment set is governed by the Church's canon doctrine (坦露與歡愉為正向、光之治療與淨化) and is split into two sub-sets by liturgical function. The **vestment-and-emblem** sub-set — `sister_vestments`, `radiant_holy_emblem`, `saintess_vestments`, and `pilgrim_medallion` — SHALL carry non-negative `exposure_bias` and non-negative `pleasure_gain`, and SHALL provide at least one of `heal_gain` or an immunity, because a garment or sigil of the faith channels the Light's healing and cleansing. The **sanctuary-device** sub-set — the 聖所 devices the codex catalogues, currently `nymph_buds_clamp`, `warm_honey_orb`, and `hyperesthesia_charm` — SHALL carry non-negative `exposure_bias` and positive `pleasure_gain`, and SHALL NOT be required to provide `heal_gain` or an immunity, because a device serves the rite of pleasure itself rather than dispensing the Light. No member of either sub-set SHALL carry chastity-style suppression (negative `pleasure_gain` or negative `exposure_bias`); ordinary combat trade-offs (negative `defense`, `atk_phys`, agility, etc.) remain permitted as the mechanical cost of holiness. A future registry-owned faith-identity tag is out of scope here; membership is these named sets, and a new Church item enters by amending this requirement in the change that adds it, naming the sub-set it joins.

#### Scenario: Doctrine coverage for the named Church set
- **WHEN** the rulebook entries of the four named vestment-and-emblem keys are validated
- **THEN** each has non-negative `exposure_bias` and `pleasure_gain`, at least one of `heal_gain` or an immunity, and no suppression value

#### Scenario: Doctrine coverage for the sanctuary-device sub-set
- **WHEN** the rulebook entries of the named 聖所 device keys are validated
- **THEN** each has non-negative `exposure_bias`, positive `pleasure_gain`, and no suppression value, and none is failed for lacking `heal_gain` or an immunity

#### Scenario: Doctrine violation blocks a named Church item
- **WHEN** a deviant rulebook copy gives a named Church item a negative `pleasure_gain`
- **THEN** the doctrine coverage test fails and the change cannot ship

#### Scenario: A sanctuary device may not borrow the healing exemption
- **WHEN** a deviant rulebook copy moves a vestment key into the sanctuary-device sub-set to drop its healing obligation
- **THEN** the coverage test still fails, because sub-set membership is the named list in this requirement and not a property the rulebook can assert
