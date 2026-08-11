## ADDED Requirements

### Requirement: Imported entity keys use a safe character set

The import schema SHALL constrain every entity `key` to printable characters excluding the structural separators `|`, `/`, and `:`, with a maximum length of 64 characters.

#### Scenario: Pipe key is rejected

- **WHEN** a character or world-entry record declares a `key` containing `|`
- **THEN** the record fails structural validation and is not instantiated

#### Scenario: Over-long key is rejected

- **WHEN** a record declares a `key` longer than 64 characters
- **THEN** the record fails structural validation and is not instantiated

#### Scenario: Valid printable keys pass

- **WHEN** a record declares a printable key without separators within the length bound
- **THEN** the record passes the key checks
