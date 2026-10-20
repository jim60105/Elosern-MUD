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

#### Scenario: Fractional percentage contributions remain readable
- **WHEN** an authorized character-detail read contains authoritative percentage-point contributions of +12.5 and -2.5 together with integral percentage, multiplier and fractional flat controls
- **THEN** the breakdown section is available with signed fractional percentages and their percent suffix, integral percentages retain their numeric meaning, all layer sources and effective totals agree with the authoritative read model, and the read mutates no state
