# Spec Delta

## MODIFIED Requirements

### Requirement: Professions are one validated rulebook table with keyed frozen reads
<!-- This block is written against the text `place-attendant-profession` leaves behind and
     MUST be archived after it. -->
`world/rules/rulebook/professions.yaml` SHALL declare every authored profession as a list under `professions:` with `schema_version: 1`, and `world/rules/profession_config.py` SHALL expose the loaded table as frozen dataclasses through keyed reads (`get_profession(key)` returning the profession or `None`, and `all_professions()`).

#### Scenario: The shipped table loads and exposes the three replica professions
<!-- Scenario name retained verbatim: a MODIFIED block may not rename or drop an existing
     scenario, so this historical title now covers the whole shipped table. -->
- **WHEN** the professions rulebook is loaded
- **THEN** `get_profession("merchant")` carries a `merchant` and a `scripted_dialogue`
  component, `get_profession("guild_staff")` / `get_profession("guild_exam_reception")` carry the
  component sets the guild-economy sync attaches, `get_profession("quest_issuer")` carries one
  person-bound `quest_issuer` component, `get_profession("attendant")` carries one place-bound
  `scripted_dialogue` component, and every row's `schedule_template` and `default_tier` are null

#### Scenario: Keyed reads never mutate the table
- **WHEN** a consumer calls `get_profession` twice for one key
- **THEN** both calls return equal frozen values and no mutation of the cached table is possible

#### Scenario: Loader follows the guild_config family
- **WHEN** `profession_config.py`'s load and cache code is inspected
- **THEN** it follows the `guild_config.py` load/cache family

#### Scenario: Each row's exact fields
- **WHEN** a profession row is validated at load
- **THEN** it carries exactly: a non-empty unique `key`; a `components:` list of `{type, default_binding}` pairs; a nullable `schedule_template`; and a nullable `default_tier`

#### Scenario: The shipped table's exact membership
- **WHEN** the shipped table is loaded
- **THEN** it contains exactly the `merchant`, `guild_staff`, `guild_exam_reception`, `quest_issuer`, `attendant` and `clergy` professions, each with `schedule_template: null` and `default_tier: null`

#### Scenario: The merchant blueprint trades and answers
- **WHEN** the `merchant` row is read
- **THEN** it carries a place-bound `merchant` component and a place-bound `scripted_dialogue` component, so every shopkeeper both trades and answers

#### Scenario: The guild_staff blueprint mirrors the synced host tuple
- **WHEN** the `guild_staff` row is read
- **THEN** it mirrors the guild-hall host component tuple that sync attaches

#### Scenario: The guild_examiner blueprint is a prescribed reusable subset
- **WHEN** the `guild_exam_reception` row is read
- **THEN** it is the prescribed examiner/dialogue blueprint (a reusable subset; sync attaches no examiner-only host today)

#### Scenario: The quest_issuer blueprint may not anchor a roster row
- **WHEN** the `quest_issuer` row is read
- **THEN** it is the person-bound commission blueprint that no roster row may anchor

#### Scenario: The attendant blueprint is talk-only
- **WHEN** the `attendant` row is read
- **THEN** it is the place-bound talk-only blueprint carrying one `scripted_dialogue` component
