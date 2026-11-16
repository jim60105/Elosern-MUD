## MODIFIED Requirements

### Requirement: Monster portraits never borrow runtime state across visual species
A monster SHALL resolve reusable gallery cards only inside its declared visual species. Individual official selections and geometry SHALL remain entity-local. Missing, failed or invalid images SHALL retain truthful state and carry monster_anon for browser load failure.

#### Scenario: Same-tier species do not share imagery
- **WHEN** two monsters share a combat tier but declare different visual species, and only one species has a card
- **THEN** only that species presents the card; the other presents its own official image or monster_anon

#### Scenario: Same-species individuals keep independent official choices
- **WHEN** two individuals of one species select different official images and geometry through entity-context preferences
- **THEN** each presents its own selection and geometry, while source files and the species card remain shared and unchanged

#### Scenario: Broken species images degrade without substitution
- **WHEN** a valid species image fails admission or a browser image load fails
- **THEN** presentation uses monster_anon without reaching another species, a tier image or the deprecated humanoid SVG
