# Spec Delta

## MODIFIED Requirements

### Requirement: A masterwork price band spans everyday and scarce prices for the same object
`PRICE_TABLE` SHALL retain `masterwork_gear` as an integer bounded authored price band spanning everyday and scarce prices for the same object. Bounds SHALL be mutable data. Its ceiling SHALL remain below the relic floor. Market scarcity SHALL NOT change item identity/definition; the band key SHALL remain race/culture-neutral.

#### Scenario: One item carries an ordinary and a scarce price
- **WHEN** two shops offer the same masterwork item near its declared floor and at a far higher valid price
- **THEN** both offers validate and purchases yield the same item key and definition

#### Scenario: A price above the masterwork ceiling is rejected
- **WHEN** an offer exceeds the currently declared finite ceiling
- **THEN** validation rejects before registry/merchant mutation, without a copied ceiling literal

#### Scenario: The masterwork ceiling does not reach the keepsake floor
- **WHEN** current masterwork and relic bounds are compared
- **THEN** masterwork maximum is strictly below relic minimum, with no price legal in both

#### Scenario: One price band describes the object, not one market
- **WHEN** the authored band width is considered
- **THEN** it accommodates an everyday price in the maker's community and a far higher price elsewhere for one unchanged item

#### Scenario: The band key names no race or culture
- **WHEN** master-crafted goods are classified
- **THEN** goods from any people are admissible and the band key names no race/culture

### Requirement: A keepsake-band item can never be offered for sale
No relic-band item SHALL be offered for sale at any price. Relic SHALL remain a one-of-a-kind non-traded keepsake category; its exact authored floor SHALL not affect the absolute prohibition.

#### Scenario: A relic-band item is unshelvable at any price
- **WHEN** a relic item is priced exactly at the current authored band floor
- **THEN** it remains unofferable because its band, not its numeric price, is prohibited

#### Scenario: A keepsake stays reachable outside trade
- **WHEN** authored non-shop content grants a relic item
- **THEN** it is held/inspected normally and only shop offers are closed

#### Scenario: The prohibition is made absolute over the band floor
- **WHEN** an author sets an offer to the current relic floor
- **THEN** it cannot reach a shelf even though that price meets the numeric band floor

#### Scenario: Enforcement is owned by the goods-list validator
- **WHEN** load-time relic-offer rejection is located
- **THEN** the commerce-assortments goods-list validator owns it
