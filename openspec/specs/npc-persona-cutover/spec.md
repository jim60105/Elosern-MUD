## Purpose

Define how the NPC persona content set reaches existing persisted worlds without a data migration: fresh databases are initialized with the complete marked roster directly by the creation producers, pre-amendment databases fail closed, and the supported recovery is a documented destroy-and-reinitialize of the development database.

## Requirements

### Requirement: A fresh database is initialized with the complete marked NPC roster without any rewrite step
The system SHALL materialize every production-created NPC with a complete compact card and the current content-generation marker at creation time, so that a database built from scratch and synchronized by the normal startup sequence contains an NPC family in which every instance carries a contract-valid card and the current marker before any player action, with no in-place rewrite step run.

#### Scenario: Freshly synchronized NPCs are born marked
- **WHEN** startup syncs create the shipped hosts, examiners, companions, and other production NPCs against a freshly migrated database
- **THEN** every NPC-family instance carries the current content-generation marker and a contract-valid complete compact card, and the roster validation step passes

#### Scenario: No rewrite step exists in the boot sequence
- **WHEN** the startup step order is inspected
- **THEN** it contains the roster validation step and no persona-content cutover step

### Requirement: Pre-amendment generated-quest payloads fail closed with no compatibility decoder
The system SHALL reject, at generated-quest restore validation, any stored occupant characterization that is not a complete compact card, and SHALL NOT provide any runtime decoder, migration, or fallback that admits pre-amendment payload shapes into play.

#### Scenario: A pre-amendment payload is refused at restore
- **WHEN** the restore path is given a stored payload whose occupant carries the old optional three-field persona and background shape
- **THEN** strict payload validation rejects it with a named validation failure and the quest is not restored

### Requirement: Destroying and re-initializing the development database is the documented supported recovery
The repository SHALL document, in the development docs, the operator procedure to replace an unsupported database: stop the server, delete the SQLite database named by the project settings, migrate a new database, and start the server so the normal startup sequence rebuilds world state; the procedure SHALL name the retained test database and state that the deletion also destroys player characters, progress, and generated quests.

#### Scenario: The runbook names the full reset path
- **WHEN** a developer follows the documented reset procedure against a database holding pre-amendment data
- **THEN** the runbook names stopping the server, deleting the settings-named database file, running the migration command, restarting the server, and the retained test database path, and it warns that all player and world progress in that database is destroyed
