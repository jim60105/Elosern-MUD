## MODIFIED Requirements

### Requirement: Imported entity keys use a safe character set

The import schema SHALL constrain every entity `key` to printable characters excluding the structural separators `|`, `/`, `:`, `{`, `}`, and control characters, with a maximum length of 64 characters. The schema SHALL additionally reject digit-only keys (ASCII digits only, e.g. `"42"`): the digit-only region of the character-portrait keyspace is reserved for player characters, whose stable keys are `str(pk)`, so no imported entity key may ever equal a player's pk string.

#### Scenario: Pipe key is rejected

- **WHEN** a character or world-entry record declares a `key` containing `|`
- **THEN** the record fails structural validation and is not instantiated

#### Scenario: Over-long key is rejected

- **WHEN** a record declares a `key` longer than 64 characters
- **THEN** the record fails structural validation and is not instantiated

#### Scenario: Valid printable keys pass

- **WHEN** a record declares a printable key without separators within the length bound
- **THEN** the record passes the key checks

#### Scenario: A digit-only key is rejected for both record kinds

- **WHEN** a character or world-entry record declares a `key` consisting only of ASCII digits
- **THEN** the record fails structural validation on the key pattern and is not instantiated

#### Scenario: A key with letters and digits passes

- **WHEN** a record declares a key that contains digits alongside non-digit characters (e.g. `"bandit_02"`)
- **THEN** the record passes the key checks, since only an entirely digit-only key is reserved
