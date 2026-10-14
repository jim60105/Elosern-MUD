# Spec Delta

## MODIFIED Requirements

### Requirement: The built-in fallback set is a closed vocabulary committed to the repository
The project SHALL commit exactly one image per key of the closed fallback vocabulary `man`, `woman`,
`boy`, `girl`, `elder`, `monster_anon` into one fixed in-repo defaults directory, served through the
existing `/art/defaults/<key>.<ext>` route. Required bundled official scenes SHALL be an additional tracked-art exception; every runtime and seed-synced image stays outside git under the art store root.
Each committed image SHALL be bounded in size and SHALL depict no sexualized content.

#### Scenario: Every key resolves to a committed file
- **WHEN** the contract test enumerates the fallback vocabulary
- **THEN** each key has exactly one committed file in the defaults directory, within the declared size bound

#### Scenario: No stray file is servable
- **WHEN** the contract test enumerates the defaults directory
- **THEN** every file corresponds to a vocabulary key and nothing else is present

#### Scenario: Runtime art is still absent from git
- **WHEN** tracked artwork is inspected
- **THEN** the six alpha defaults, required bundled scenes and existing reviewed documentation fixtures are tracked; runtime store, seed images and operator artwork remain untracked

#### Scenario: A contract test locks the vocabulary and directory together
- **WHEN** the contract test locks the fallback vocabulary and the defaults directory to each other
  in both directions
- **THEN** every key resolves to exactly one committed file and every file in the directory belongs
  to the vocabulary, so a key can never resolve to a missing image and an untracked stray file can
  never be served

