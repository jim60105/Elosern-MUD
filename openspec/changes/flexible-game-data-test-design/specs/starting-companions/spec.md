# Spec Delta

## MODIFIED Requirements

### Requirement: A preset declares its starting companions by partner preset key
`world/lore/player_presets.py` SHALL define a frozen `StartingCompanion` carrying
exactly `preset_key` (the companion's own `PLAYER_PRESET_REGISTRY` key),
`affinity` (the value seeded into the companion's relationship record), and
`relationship` (the label composed into the companion's owner relationship
line). `PlayerPreset` SHALL carry a keyword-only `starting_companions` tuple of
these entries, defaulting to empty.

#### Scenario: The twins declare each other
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** `yuna_darknight` declares `yuka_darknight` and `yuka_darknight` declares `yuna_darknight`, each at its valid authored affinity with a relationship label and no profile reference

#### Scenario: A preset without companions is unchanged
- **WHEN** any preset other than the four companion-declaring presets is inspected
- **THEN** its `starting_companions` is empty

#### Scenario: Extension fields never reach a player persona record
- **WHEN** a preset authors `speech_style` and `greeting` and its `PresetPersona.to_record()` is inspected
- **THEN** the record carries exactly its existing persona keys and neither extension value

#### Scenario: An invalid declaration is rejected at lore load
- **WHEN** a preset declares an unregistered partner key, names itself, or declares the same partner twice
- **THEN** importing `world.lore.player_presets` raises

#### Scenario: An out-of-bounds declaration is rejected at rules load
- **WHEN** a preset declares more than `PARTY_MAX_COMPANIONS` companions, an affinity below 1 or above `NATURAL_CAP`, or its partner preset cannot derive a card that holds the owner relationship line for a maximum-length owner name within the card bounds
- **THEN** importing `world.rules.starting_companions` raises from its registry sweep, naming the offending preset

#### Scenario: The declaration carries no profile reference
- **WHEN** a `StartingCompanion` is declared
- **THEN** it carries no NPC profile reference, because the partner preset itself is the companion's single authored characterization source

#### Scenario: A preset that declares none behaves as today
- **WHEN** a preset declares no `starting_companions` and defaults to the empty tuple
- **THEN** it behaves exactly as it does today

#### Scenario: PresetPersona carries optional NPC-need extension fields
- **WHEN** a `PresetPersona` is authored
- **THEN** it may set `speech_style` (the compact card's speech leaf, which the player persona record does not carry) and `greeting` (the companion's offline voice line), both optional and defaulting to empty

#### Scenario: The greeting is bounded at lore import
- **WHEN** a `greeting` is imported
- **THEN** it must be single-paragraph plain text of at most 300 code points after the card leaf normalization rule, and a newline or overflow is rejected at lore import

#### Scenario: Extension fields stay out of the player persona record
- **WHEN** a character is activated from a preset that authors the extension fields
- **THEN** neither field is projected into the player persona record, so every preset's existing player-side persona output is unchanged

#### Scenario: Mechanical identity comes only from the partner preset
- **WHEN** a companion's stats, skills, items, ages, and mechanical identity are determined
- **THEN** they come from the partner's own `PlayerPreset`, never from a second authored copy, so the twin who arrives as an NPC is mechanically the same character the player could have chosen

#### Scenario: The companion persona never touches NPC profiles
- **WHEN** a companion's persona is determined
- **THEN** it derives from the partner preset's persona (including its `speech_style` extension field) and reads or copies no NPC profile

#### Scenario: Declaring and building never mutate a player preset
- **WHEN** a companion is declared or built
- **THEN** no player preset is modified

#### Scenario: The twins' affinity leaves stage headroom
- **WHEN** `yuna_darknight` and `yuka_darknight` declare each other symmetrically at valid authored affinity
- **THEN** the value is above the rulebook `invite_threshold` and inside the 至愛 stage with headroom, so a single negative delta cannot drop the pair a stage and the companion can never be auto-dismissed on arrival

#### Scenario: Declaration errors surface at load, never at activation
- **WHEN** a companion declaration is invalid or out of bounds
- **THEN** it fails at load, never at player activation

#### Scenario: Rules-derived bounds are swept outside the lore layer
- **WHEN** validation needs bounds derived from rules constants
- **THEN** they are swept at `world/rules/` import time, because `world/lore/` SHALL NOT import `world/rules/`

#### Scenario: The lore-side rejections are enumerated
- **WHEN** lore-side validation runs
- **THEN** it rejects an unregistered `preset_key`, a preset naming itself, and the same partner declared twice by one preset
