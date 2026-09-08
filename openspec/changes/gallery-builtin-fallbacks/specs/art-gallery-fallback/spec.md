## ADDED Requirements

### Requirement: The built-in fallback set is a closed vocabulary committed to the repository
The project SHALL commit exactly one image per key of the closed fallback vocabulary `man`, `woman`,
`boy`, `girl`, `elder`, `monster_anon` into one fixed in-repo defaults directory, served through the
existing `/art/defaults/<key>.<ext>` route. These SHALL be the only generated-art files the
repository tracks: every runtime and seed-synced image stays outside git under the art store root. A
contract test SHALL lock the vocabulary and the directory to each other in both directions — every
key resolves to exactly one committed file, and every file in the directory belongs to the
vocabulary — so a key can never resolve to a missing image and an untracked stray file can never be
served. Each committed image SHALL be bounded in file size and SHALL depict no sexualized content.

#### Scenario: Every key resolves to a committed file
- **WHEN** the contract test enumerates the fallback vocabulary
- **THEN** each key has exactly one committed file in the defaults directory, within the declared size bound

#### Scenario: No stray file is servable
- **WHEN** the contract test enumerates the defaults directory
- **THEN** every file corresponds to a vocabulary key and nothing else is present

#### Scenario: Runtime art is still absent from git
- **WHEN** the repository is inspected for tracked art files
- **THEN** only the defaults directory carries images, and the art store root and the seed directory remain untracked

### Requirement: A fallback key resolves by declaration, then band, then deterministic hash
`world/art/gallery_fallback.py` SHALL resolve a subject's fallback key by this ordered rule: (1) a
fallback key explicitly declared by the subject's registry entry — player presets and the NPC and
monster registries MAY declare one and every existing entry stays valid without one — wins outright;
(2) otherwise a monster subject resolves `monster_anon`; (3) otherwise the subject's stored sex and
apparent age select one band, and the subject's full key is hashed deterministically into that band's
ordered key pool. A band's pool MAY hold more than one key, which is how a sex outside the
female/male pair resolves. The resolution SHALL be a pure function of the subject key and the stored
sex and apparent age: the same subject SHALL resolve the same key on every restart, on every process,
and on every machine. Missing or malformed sex or apparent-age values SHALL fail closed to the adult
band rather than raising.

#### Scenario: A declared key wins over the band rule
- **WHEN** a subject's registry entry declares a fallback key
- **THEN** that key is resolved regardless of the subject's sex or apparent age

#### Scenario: Sex and apparent age select the band
- **WHEN** subjects with adult, child, and elder apparent ages and female and male sexes resolve without a declaration
- **THEN** each resolves the key its band declares for that sex

#### Scenario: A sex outside the pair hashes deterministically inside its band
- **WHEN** a subject whose sex is neither female nor male resolves without a declaration
- **THEN** its key is chosen from its band's pool by a hash of the subject key, and repeating the resolution yields the same key

#### Scenario: Determinism survives a restart
- **WHEN** the same subject is resolved before and after a server restart
- **THEN** the same fallback key, and therefore the same image, is resolved

#### Scenario: Malformed sex or age fails closed to the adult band
- **WHEN** a subject's stored sex or apparent age is missing or malformed
- **THEN** the adult band is used, no exception propagates, and a key is still resolved

### Requirement: The fallback seam supplies a URL and a face rectangle and reports its use
`world/art/gallery_match.py::fallback_for(subject)` SHALL return the resolved key's
`/art/defaults/<key>.<ext>` URL together with that key's declared face rectangle, taken from a fixed
per-key rectangle map that falls back to the shared default rectangle for any key without its own
entry. Each use SHALL emit one `gallery_fallback_used` info event through the `world.observability`
facade carrying the `subject`, `kind`, and resolved fallback `key` in `context`. The seam SHALL NOT
create a record, append a card, copy a file into the store, or write any state.

#### Scenario: A subject with no card and no classic asset resolves a fallback image
- **WHEN** the chain reaches the seam for a subject with no card and no `done` classic asset
- **THEN** the payload carries the `/art/defaults/<key>.<ext>` URL and that key's face rectangle, and one `gallery_fallback_used` event is logged

#### Scenario: The fallback writes nothing
- **WHEN** the fallback resolves for a subject that has no gallery record
- **THEN** no record is created, no card is appended, no file is copied into the store, and the subject still has no gallery record

#### Scenario: A fresh database with every service offline still shows art
- **WHEN** a character is resolved on a database with no generated art while the image server and every LLM service are unreachable
- **THEN** the payload carries a fallback image URL and its face rectangle rather than a placeholder
