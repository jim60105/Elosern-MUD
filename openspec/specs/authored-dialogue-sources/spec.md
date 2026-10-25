# authored-dialogue-sources Specification

## Purpose
Discover immutable per-NPC dialogue content by stable profile identity without manual file registration or unsafe source execution.

## Requirements

### Requirement: Static dialogue discovery derives owner from profile-key filename
Static dialogue SHALL be discovered from the flat `world/lore/dialogue/content/<NpcProfile.key>.yaml` directory in stable filename order. Each filename SHALL identify an existing stable profile key. Content SHALL contain no duplicate owner identifier and SHALL require no manual file registration.

#### Scenario: Registered profile file is discovered automatically
- **WHEN** a valid new file for an existing canonical dialogue/profile binding is added without changing a file index
- **THEN** the next initialization discovers its dialogue exactly once

#### Scenario: Runtime or display identity cannot name an owner
- **WHEN** a filename uses a dbid, display name or service key different from the bound profile key
- **THEN** loading rejects that file with an identity-named error

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
