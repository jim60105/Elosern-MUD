## ADDED Requirements

### Requirement: Registration and tradeability are independent
An equipment item SHALL be complete when it declares a slot, binds one-to-one to a budget-checked rulebook entry, and names a resolvable price band. A shop listing SHALL NOT be part of that completeness. A bound, budget-checked equipment item that no shop offers SHALL be a valid shipped state: the rulebook SHALL load, no loader or validator SHALL report it as unbound, orphaned, or missing an offer, and it SHALL equip and apply its adjustments exactly as a stocked item of the same shape would. Each roster this capability adds SHALL state whether its members are stocked, and that statement SHALL follow the roster's lore provenance rather than a default.

#### Scenario: An unstocked binding loads clean
- **WHEN** the equipment-effect rulebook is loaded with a bound, budget-checked equipment item that no shop offers
- **THEN** the load succeeds with no unbound key and no orphaned entry, and no validator reports a missing offer

#### Scenario: An unstocked piece equips and applies
- **WHEN** an unstocked equipment item is granted into inventory and equipped
- **THEN** it occupies its declared slot and its adjustments reach the shared accessor with the authored values

#### Scenario: Tradeability is a stated roster property
- **WHEN** a roster added by this capability is inspected
- **THEN** its requirement states whether its members are stocked, and the shipped offers match that statement
