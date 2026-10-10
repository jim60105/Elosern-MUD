# Spec Delta

## MODIFIED Requirements

### Requirement: A masterwork price band spans everyday and scarce prices for the same object
`PRICE_TABLE` SHALL retain `masterwork_gear` as an integer bounded authored price band spanning its intended everyday and scarce goods. The exact floor and ceiling SHALL be mutable game data. Existing band-membership validation and deterministic integer pricing SHALL remain mandatory.

#### Scenario: Offer above the authored ceiling
- **WHEN** an offer exceeds the currently declared finite ceiling
- **THEN** startup validation rejects it by item and band without a copied ceiling literal in tests
