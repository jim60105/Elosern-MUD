# Spec Delta

## MODIFIED Requirements

### Requirement: Guild service hosts reuse by service anchor and never rename
Service hosts SHALL reuse canonical authored profile provenance independent of component IDs/order and preserve existing identity and live state. Whole-row retirement SHALL use explicit source ownership and SHALL never consult title content.

#### Scenario: Canonical host remains stable
- **WHEN** a service ID, display-name declaration or capability order changes
- **THEN** the existing host dbref/name/location/state survive

#### Scenario: No title-based ownership inference
- **WHEN** a host carries an arbitrary historical title
- **THEN** it grants no lookup or deletion authority
