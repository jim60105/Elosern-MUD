# Spec Delta

## MODIFIED Requirements

### Requirement: Complete curated entity summaries
Each entity page SHALL offer a curated summary and a raw representation. Curated summaries SHALL include the kind-specific fields stated in the scenarios below.
Stored truth and `disguised_stats` SHALL be shown side by side; disguise SHALL be labelled 僅顯示用 and SHALL never replace or merge into true traits. Currency SHALL remain integer-based. Missing or failed sources SHALL not be fabricated.

#### Scenario: Entity inventory coverage
- **WHEN** fixed fixtures for every listed kind and narrative subtype are inspected
- **THEN** each curated summary exposes all applicable named fields and real relationships, including generated payload and available art thumbnail

#### Scenario: Disguised character and NPC
- **WHEN** a character or NPC has disguise values different from true traits
- **THEN** both are independently emitted and rendered side by side, the disguise is labelled display-only, and breakdowns retain true values

#### Scenario: Accounts summary fields
- **WHEN** an account curated summary is rendered
- **THEN** it includes name, permissions, created/last-login dates, live sessions, owned characters

#### Scenario: Player character summary fields
- **WHEN** a player character curated summary is rendered
- **THEN** it includes race/subrace/sex/age/apparent age; true traits; separate displayed disguise; per-trait base → skills → equipment → conditions breakdown; gauges, conditions/buffs, skills/lineage, equipment/inventory, integer-copper wallet and derived gold/silver/copper display, guild rank/merit, titles, affinity, party/possession, sexual state, and current room

#### Scenario: NPC summary fields
- **WHEN** an NPC curated summary is rendered
- **THEN** it includes character fields plus title/profession, shop/guild service components, seven-section persona and version, today's schedule/current slot, dialogue key, memory and dialogue tabs

#### Scenario: Monster summary fields
- **WHEN** a monster curated summary is rendered
- **THEN** it includes species/variant/threat tier, approved-profile or interim numeric source, owning site or ambient placement, loot table, behaviour profile, and the shared resource, condition, and true-trait sections read through the authoritative status/character read model

#### Scenario: A monster with sanctioned zero-maximum gauges renders its shared sections
- **WHEN** a monster whose numeric source carries a zero MP/SP maximum (an approved-profile or tier-band zero) is rendered
- **THEN** its resource, condition, and trait sections render from the stored state — the zero gauge shown as its stored value over a zero maximum — rather than degrading those sections to their unavailable form

#### Scenario: Room summary fields
- **WHEN** a room curated summary is rendered
- **THEN** it includes coordinates/map, place kind, exits, occupants grouped by kind, instance ownership/lifetime

#### Scenario: Quest record summary fields
- **WHEN** a quest record curated summary is rendered
- **THEN** it includes definition key, issuer, status/stage, progress counters, bound targets, deadline, rewards, failure reason, owning character; generated quests also show stored payload

#### Scenario: Narrative summary fields
- **WHEN** a narrative curated summary is rendered
- **THEN** it includes event content/participants/location/visibility; thread status/links/revisions; letter exchanges/state/reply work; dream sessions/exchanges; director decisions/scheduled beats; authoring drafts/creative requests

#### Scenario: Art asset summary fields
- **WHEN** an art asset curated summary is rendered
- **THEN** it includes subject key, status, prompt summary, source_hash, generated time, failure reason, and existing `/art/` thumbnail only when a file exists

### Requirement: Independent failures and precise lookup errors
Each curated summary section SHALL compute independently. A failed section SHALL carry `{"error":{"code":"<snake_case>","message":"<zh-TW>"}}` in its own slot while unaffected sections render in the success envelope. Errors SHALL remain visible diagnostic evidence and clients SHALL branch on codes only.

#### Scenario: Corrupt section isolation
- **WHEN** each summary section is independently made to fail, including a corrupt status-query source
- **THEN** only that slot exposes its stable error and all unaffected sections remain readable

#### Scenario: A sanctioned zero-maximum gauge is not a section failure
- **WHEN** a monster summary's shared sections read a gauge whose maximum is a sanctioned zero
- **THEN** no section slot carries an error and none reports `source_unavailable` for that reason

#### Scenario: A negative-maximum gauge still fails its sections closed
- **WHEN** a stored gauge's modifiers compute to a negative maximum
- **THEN** each section routed through the status/character read model carries its stable error while unaffected sections remain readable

#### Scenario: Lookup and length error matrix
- **WHEN** requests target an absent object, an existing object of the wrong kind, a 2000-character recall query, or a 2001-character recall query
- **THEN** they respectively receive 404 object_not_found, 404 kind_mismatch, valid recall, and 400 query_too_long with no recall execution for the oversized request

#### Scenario: Unknown object lookup error
- **WHEN** a request targets an unknown object
- **THEN** the API returns HTTP 404 object_not_found

#### Scenario: Kind mismatch lookup error
- **WHEN** a requested object is incompatible with the requested kind
- **THEN** the API returns HTTP 404 kind_mismatch

#### Scenario: Oversized recall query rejected before execution
- **WHEN** recall query text exceeds 2000 characters
- **THEN** the API returns HTTP 400 query_too_long before recall execution
