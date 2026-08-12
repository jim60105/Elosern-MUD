## ADDED Requirements

### Requirement: Menu target shorthands are convenience UI

The combat menu's target-selection options (`all-enemies`, `all-allies`, `all`) SHALL be presented as conveniences for constructing the target list; the underlying skills accept any explicit target their scope allows (enemy or ally for `ANY` skills), and the menu SHALL also allow explicit ally selection where the skill permits it.

#### Scenario: Menu shorthands do not restrict targeting

- **WHEN** the combat menu offers `all-enemies` for a damage skill
- **THEN** the option is a convenience expansion; selecting an explicit ally target for the same skill is equally valid and submits normally
