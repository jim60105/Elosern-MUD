## MODIFIED Requirements

### Requirement: The catalog indexes the mounted layout once at startup and serves from that snapshot
The catalog SHALL index admitted monster, preset, npc, scene and room content once at startup and resolve from that snapshot. Root-relative paths SHALL be stable identities. Scene membership SHALL use the scene archetype registry; room membership SHALL retain its authored room-art registry. Subject-reference consumers SHALL recognize monster, preset, npc and scene; room SHALL remain an authored override.

#### Scenario: The snapshot is built at startup and reused
- **WHEN** the server starts with a populated official root and ten portraits resolve during ordinary play
- **THEN** the filesystem index was walked once at startup and all ten resolutions answered from the snapshot without re-walking the root

#### Scenario: Replacement takes effect after restart only
- **WHEN** an operator replaces a file inside the live root and gameplay continues before any restart
- **THEN** the catalog continues to serve the previously indexed identity and fingerprint, and the replacement appears only after the next startup

#### Scenario: Unsupported content directories are ignored with a diagnostic
- **WHEN** the root contains a top-level directory whose name is outside `monster`, `preset`, `npc`, `scene`, or `room`
- **THEN** it is skipped with one bounded diagnostic and valid known-kind directories still index

#### Scenario: Unknown registry references are skipped, not fatal
- **WHEN** the root holds a content directory keyed to a name that no registry declares
- **THEN** that directory is skipped with a bounded diagnostic and unrelated valid artwork indexes normally

#### Scenario: Directory keys name authored content only
- **WHEN** an indexed directory key is resolved
- **THEN** it identifies registered authored content — never a runtime database row or a translated display name

#### Scenario: Artwork updates restart-only with no external acquisition
- **WHEN** artwork in the official root is updated
- **THEN** it takes effect only through a restart: no file watcher, hot activation, or refresh path exists, and the catalog never calls Git, S3, an archive extractor, or an external host

#### Scenario: Indexing is owned by the art service's startup steps
- **WHEN** the official root is indexed
- **THEN** it is owned by the art service alongside the other startup synchronization steps

#### Scenario: Scene and room keys are authored
- **WHEN** operator scene/room directories are indexed
- **THEN** scene keys and room-art keys must be registered authored content, not database ids or translated labels

#### Scenario: Scene reference vocabulary agrees with admission
- **WHEN** a synthetic registered archetype has a valid scene directory
- **THEN** catalog admission and official-reference validation both admit it; an unknown archetype is rejected without affecting another directory
