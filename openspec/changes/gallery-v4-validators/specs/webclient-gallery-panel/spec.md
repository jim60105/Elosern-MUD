## ADDED Requirements

### Requirement: The version-4 gallery payload has an exact category-scoped shape
The version-4 available form SHALL contain exactly `schema_version` (4), `available`, `kind`, `categories`, `category`, `groups`, `selected`, `description`, `cards`, `official_entries`, `equipment_summary`, `capabilities`, `binding_warnings` and `error_state`. `categories` SHALL list the five category keys in fixed order with count, enabled and reason; `category` SHALL name an enabled one.

#### Scenario: A payload naming a disabled category is rejected
- **WHEN** a v4 payload's `category` names a category whose `enabled` is false
- **THEN** both validators reject it

#### Scenario: A reordered or partial category list is rejected
- **WHEN** `categories` omits a key, repeats one or changes the order
- **THEN** both validators reject it

#### Scenario: Reason accompanies only disabled categories
- **WHEN** an enabled category carries a reason or a disabled one carries none
- **THEN** both validators reject it

### Requirement: Version-4 groups carry ordered subjects or a collapsed count
Each group SHALL be exactly `{key, label, seen, total, expanded, count, subjects}`. An expanded group SHALL list exactly `count` subjects; a collapsed group SHALL carry an empty list. Each subject SHALL be exactly `{subject_key, kind, display_name, is_current, card_count, artwork}` with unique keys across groups, a coherent kind and a nullable canonical artwork descriptor.

#### Scenario: A collapsed group with subjects is rejected
- **WHEN** a group has `expanded: false` and a non-empty `subjects` list
- **THEN** both validators reject it

#### Scenario: Group counts sum to the category count
- **WHEN** the groups' counts do not sum to the selected category's `count`
- **THEN** both validators reject it

#### Scenario: A collapsed group is accepted
- **WHEN** a group has `expanded: false`, a label, `count: 7` and no subjects, and the counts sum correctly
- **THEN** both validators accept it

#### Scenario: Seen and total are paired and bounded
- **WHEN** a group carries `seen` without `total`, or `seen` greater than `total`
- **THEN** both validators reject it

### Requirement: Selection decides the version-4 card fields
`selected` SHALL be null exactly when no expanded group lists a subject, and otherwise SHALL name a listed subject. While `selected` is null, `cards`, `official_entries` and `binding_warnings` SHALL be empty, and `equipment_summary`, `capabilities`, `error_state` and `description` SHALL be null. Otherwise the card fields SHALL follow the existing row, official, warning and equipment rules.

#### Scenario: An empty category carries no card facts
- **WHEN** a payload has no listed subject, `selected: null` and an empty `cards` list
- **THEN** both validators accept it, and they reject the same payload when `capabilities` is not null

#### Scenario: A selection outside the listed subjects is rejected
- **WHEN** `selected` names a subject that only a collapsed group would contain
- **THEN** both validators reject it

#### Scenario: Capabilities carry the declared card operations
- **WHEN** `capabilities` omits `supports_face_rect`, `supports_stage` or `supports_card_delete`, or carries a non-boolean for one
- **THEN** both validators reject it

### Requirement: A panel past the subject ceiling is unavailable, never truncated
Both validators SHALL reject a version-4 payload listing more than 256 subjects in total. The gallery presenter SHALL NOT drop subjects to fit; a rejected payload SHALL degrade to the common unavailable form through the presenter registry and log the error.

#### Scenario: One subject over the ceiling fails closed
- **WHEN** a payload lists 257 subjects
- **THEN** both validators reject it, and a payload listing 256 otherwise valid subjects is accepted

### Requirement: The version-4 validators are exact mirrors
Every version-4 rule SHALL be enforced identically by the Python and JavaScript validators, and the dual-direction parity cases SHALL fail when a payload is accepted on one side and rejected on the other.

#### Scenario: Parity cases cover every rule
- **WHEN** the parity test runs its v4 accept and reject cases through both validators
- **THEN** every case has the same verdict on both sides
