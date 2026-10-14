# Spec Delta

## MODIFIED Requirements

### Requirement: Official artwork lives outside git behind one directory-root setting
`server/conf/settings.py` SHALL declare `ART_OFFICIAL_ROOT`, defaulting to the `art-official` directory under `GAME_DIR` and overridable through an environment variable of the same name. The repository SHALL gitignore the default directory, and the variable SHALL be carried in the exact `.env.example` inventory and the settings-and-environment guide. `ART_OFFICIAL_ROOT` SHALL be distinct from `ART_STORE_ROOT` and `ART_SEED_ROOT`, and the game process SHALL treat it as read-only.

#### Scenario: The environment override is honored
- **WHEN** settings import runs with `ART_OFFICIAL_ROOT` set in the environment to an operator directory
- **THEN** the effective `ART_OFFICIAL_ROOT` is that directory and ordinary startup reads it

#### Scenario: The default directory is not tracked
- **WHEN** tracked artwork paths are inspected
- **THEN** art-official/ remains gitignored; only the closed eleven scene paths under web/static/art/scenes and the existing six alpha defaults are permitted tracked exceptions; packs validate owned files and the complete collection gate begins with catalog integration, while operator artwork stays external

#### Scenario: The game never writes the official root
- **WHEN** the production modules are inspected for filesystem writes
- **THEN** no module resolves a write path under `ART_OFFICIAL_ROOT`

#### Scenario: The setting follows the directory-root precedent
- **WHEN** `ART_OFFICIAL_ROOT` is declared
- **THEN** it follows the `ART_SEED_ROOT`/`PROMPT_ROOT` directory-root precedent rather than the typed `ART_SD_*` knob table

#### Scenario: Read-only means no create, rename, replace, or delete
- **WHEN** any game code path touches `ART_OFFICIAL_ROOT`
- **THEN** it never creates, renames, replaces, or deletes any file under it

