# Spec Delta

## MODIFIED Requirements

### Requirement: A fallback key resolves by declaration, then band, then deterministic hash
`world/art/gallery_fallback.py` SHALL resolve a subject's fallback key in order: (1) every monster
entity or subject resolves `monster_anon`, including unresolved visual provenance; (2) a non-monster
registry-declared fallback key wins; (3) otherwise stored sex and apparent age select a band, and
the full key hashes deterministically into that band's ordered key pool. Resolution SHALL be a pure
function of the subject key and the stored sex and apparent age.

#### Scenario: A declared key wins over the band rule
- **WHEN** a non-monster subject's registry entry declares a fallback key
- **THEN** that key is resolved regardless of the subject's sex or apparent age

#### Scenario: Sex and apparent age select the band
- **WHEN** non-monster subjects with adult, child, and elder apparent ages and female and male sexes resolve without a declaration
- **THEN** each resolves the key its band declares for that sex

#### Scenario: A sex outside the pair hashes deterministically inside its band
- **WHEN** a non-monster subject whose sex is neither female nor male resolves without a declaration
- **THEN** its key is chosen from its band's pool by a hash of the subject key, and repeating the resolution yields the same key

#### Scenario: Determinism survives a restart
- **WHEN** the same subject is resolved before and after a server restart
- **THEN** the same fallback key, and therefore the same image, is resolved

#### Scenario: Malformed sex or age fails closed to the adult band
- **WHEN** a non-monster subject's stored sex or apparent age is missing or malformed
- **THEN** the adult band is used, no exception propagates, and a key is still resolved

#### Scenario: A declaration is optional and existing entries stay valid
- **WHEN** player presets and the NPC registries declare, or do not declare, a fallback
  key
- **THEN** declaring one is permitted (MAY) and every existing entry stays valid without one

#### Scenario: Monsters always carry the authoritative monster fallback
- **WHEN** a monster has absent or invalid visual provenance, no real image, or a failed image load
- **THEN** its fallback is `monster_anon`, independent of sex, age and threat tier; no tier fallback declaration is read

#### Scenario: A band pool may hold several keys
- **WHEN** a band's ordered key pool holds more than one key
- **THEN** that is how a sex outside the female/male pair resolves

#### Scenario: The same key resolves on every process and machine
- **WHEN** the same subject is resolved on another process or another machine
- **THEN** the pure resolution of subject key, stored sex, and apparent age yields the same key

#### Scenario: Missing or malformed values fail closed rather than raising
- **WHEN** a non-monster subject's stored sex or apparent-age value is missing or malformed
- **THEN** resolution SHALL fail closed to the adult band rather than raising

#### Scenario: Creation previews resolve draft values without an entity write
- **WHEN** a pending character’s custom silhouette table is built for each advertised sex and apparent-age interval
- **THEN** the same band resolver consumes explicit sex/age values and the full identity `portrait:character:<pending character pk>`, so each row, including a sex outside the female/male pair, equals later undeclared resolution for that character at those values
- **AND** this read neither establishes a portrait policy nor changes stored identity, and the table is rebuilt for each pending character rather than shared between characters

#### Scenario: Preset previews resolve their own registry declaration
- **WHEN** a synthetic preset is previewed with no character subject
- **THEN** its declared fallback wins; otherwise its declared sex and apparent age select the ordinary band using `preset:<preset key>` as the full stable preview hash input, with no registry write
