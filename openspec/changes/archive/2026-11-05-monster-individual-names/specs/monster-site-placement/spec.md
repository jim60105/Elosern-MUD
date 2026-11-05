## RENAMED Requirements

- FROM: `### Requirement: A designated site individual carries an authored display label`
- TO: `### Requirement: A designated site individual carries an authored individual name`

## MODIFIED Requirements

### Requirement: A designated site individual carries an authored individual name
A site MAY declare an individual name only when every legal outcome of its composition is exactly one individual. The site owner SHALL construct that individual with the name, and identity, ownership, binding and defeat credit SHALL remain keyed by species, variant, site and persistent individual identity.

#### Scenario: Label applied
- **WHEN** a synthetic one-member site with a name populates
- **THEN** the constructed individual's individual name equals the site's name while its species and variant keys, site marker and group ownership equal an unnamed site's

#### Scenario: Label on a group rejected
- **WHEN** a name is declared on a site whose composition can place more than one individual, or the name is empty
- **THEN** publication raises the named placement-registry error

#### Scenario: Over-long name rejected
- **WHEN** a site declares a name longer than the shared monster name bound
- **THEN** publication raises the named placement-registry error
