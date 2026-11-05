## ADDED Requirements

### Requirement: Composition rows resolve one effective activity binding
Each composition row SHALL resolve exactly one activity binding: a site's declared override applies to every row of that site; otherwise the row's own binding applies; otherwise the composition binding applies. Publication SHALL reject an unknown row or site binding, and every writer and the forecast SHALL form groups from the resolved bindings.

#### Scenario: Mixed manual encounter
- **WHEN** a synthetic site without an override holds a cohesive-bound two-member row and a solitary-bound one-member row
- **THEN** population creates one two-member group and one one-member group, both owned by the site, and their decisions run independently

#### Scenario: Site override precedence
- **WHEN** a synthetic site declares a stationary override over a composition whose rows declare their own bindings
- **THEN** every member forms a stationary one-member group and no row binding moves any member

#### Scenario: Zone row bindings
- **WHEN** a synthetic zone births a composition with one row-bound row and one unbound row
- **THEN** the unbound row uses the composition binding, the bound row uses its own, and the forecast projects the same groups

#### Scenario: Unknown binding
- **WHEN** a row or site names an activity absent from the activity registry
- **THEN** placement publication raises the named placement-registry error and nothing is published

### Requirement: A designated site individual carries an authored display label
A site MAY declare a display label for its individual only when every legal outcome of its composition is exactly one individual. The site owner SHALL construct that individual with the label as its display name, and identity, ownership, binding and defeat credit SHALL remain keyed by species, variant, site and persistent individual identity.

#### Scenario: Label applied
- **WHEN** a synthetic one-member site with a label populates
- **THEN** the constructed individual's display key equals the label while its species and variant keys, site marker and group ownership equal an unlabelled site's

#### Scenario: Label on a group rejected
- **WHEN** a label is declared on a site whose composition can place more than one individual, or the label is empty
- **THEN** publication raises the named placement-registry error
