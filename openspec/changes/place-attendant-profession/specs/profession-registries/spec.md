## MODIFIED Requirements

### Requirement: Professions are one validated rulebook table with keyed frozen reads
`world/rules/rulebook/professions.yaml` SHALL declare every authored profession as a list under
`professions:` with `schema_version: 1`, and `world/rules/profession_config.py` SHALL expose the
loaded table as frozen dataclasses through keyed reads (`get_profession(key)` returning the
profession or `None`, and `all_professions()`), following the `guild_config.py` load/cache family.
Each profession row SHALL carry exactly: a non-empty unique `key`; a `components:` list of
`{type, default_binding}` pairs; a nullable `schedule_template`; and a nullable `default_tier`.
The shipped table SHALL contain exactly the `merchant`, `guild_staff`, `guild_examiner`,
`quest_issuer` and `attendant` professions, each with `schedule_template: null` and
`default_tier: null`.
The `merchant` and `guild_staff` rows SHALL mirror the store and guild-hall host component
tuples that sync attaches today; `guild_examiner` is the prescribed examiner/dialogue blueprint
(a reusable subset; sync attaches no examiner-only host today); `quest_issuer` is the
person-bound commission blueprint that no roster row may anchor; `attendant` is the place-bound
talk-only blueprint carrying one `scripted_dialogue` component.

#### Scenario: The shipped table loads and exposes the three replica professions
<!-- Scenario name retained verbatim: a MODIFIED block may not rename or drop an existing
     scenario, so this historical title now covers the whole shipped table. -->
- **WHEN** the professions rulebook is loaded
- **THEN** `get_profession("merchant")` carries one `merchant` component,
  `get_profession("guild_staff")` / `get_profession("guild_examiner")` carry the component sets
  the guild-economy sync attaches today, `get_profession("quest_issuer")` carries one
  person-bound `quest_issuer` component, `get_profession("attendant")` carries one place-bound
  `scripted_dialogue` component, and every row's `schedule_template` and `default_tier` are null

#### Scenario: Keyed reads never mutate the table
- **WHEN** a consumer calls `get_profession` twice for one key
- **THEN** both calls return equal frozen values and no mutation of the cached table is possible
