# Spec Delta

## MODIFIED Requirements

### Requirement: Unsafe or invalid content rejects the whole candidate snapshot
Loading SHALL reject duplicate mapping keys, unsafe YAML constructs, unknown profiles, duplicate bindings, schema/reference errors and exceeded bounds before publishing any candidate entries. Successful publication SHALL expose one deeply immutable snapshot. Generated/private package dialogue SHALL remain outside this static snapshot.

#### Scenario: One invalid neighbor prevents partial publication
- **WHEN** several valid files and one invalid file are loaded together
- **THEN** no partial replacement snapshot is published and no previously accepted immutable content is mutated

#### Scenario: Unsafe declarations are never executed
- **WHEN** a file declares an object-construction tag, alias/merge, duplicate nested key or symlink outside the directory
- **THEN** loading rejects it without executing code or reading escaped content

#### Scenario: Common primitives have common meaning
- **WHEN** equivalent valid scene/topic primitives originate from YAML and generated JSON
- **THEN** they obey the same scene bounds, attribution, priorities and predecessor rules

#### Scenario: A bound host cannot lose its file silently
- **WHEN** a supplied canonical dialogue binding has no discovered file, a discovered file names no registered profile, or a discovered file has no canonical binding
- **THEN** the whole candidate rejects with the binding identity instead of publishing a host with no dialogue

#### Scenario: Service association validation is batch atomic
- **WHEN** one static file or generated package has invalid service metadata
- **THEN** the entire candidate rejects before publication without mutating the previously accepted source or producing partial service entries
