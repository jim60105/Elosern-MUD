## MODIFIED Requirements

### Requirement: MonsterTier registry has physical stat and HP bands derived from guild rank
The registry SHALL remain frozen keyed MonsterTier lore data with key, display_name_zh, guild_rank_range, independent-axis static_band, hp_band and example_monsters_zh. It SHALL contain exactly four tiers corresponding to F-E, D-C, B-A and S/calamity, preserving non-empty canonical examples and rank-range partitioning.

#### Scenario: Registry has exactly the four threat bands
- **WHEN** the keyed registry loads
- **THEN** its four guild_rank_range values partition F-E, D-C, B-A and S/calamity without gaps

#### Scenario: Example monsters are non-empty for every tier
- **WHEN** each tier's example list is inspected
- **THEN** it retains at least one canonical example from world_info.md
MonsterTier SHALL retain four keyed threat tiers, their names/examples and guild-rank ranges, with independent HP/attack/agility/defense authoring bounds below and zero magic for current profiles. HP SHALL be independent endurance; no fixed 15-20-times relationship or elf/beastfolk calibration SHALL remain. Calamity upper reference values SHALL be open-ended (None upper limits), without altering human racial/static-tier bounds. Every future concrete monster SHALL have explicit literals and encounter evidence; maximum-axis Cartesian products SHALL NOT imply guaranteed balance.


| Monster tier | HP | Physical attack | Agility | Defense |
|---|---|---|---|---|
| Low | 25–70 | 3–12 | 3–12 | 2–8 |
| Mid | 110–230 | 18–28 | 10–24 | 10–16 |
| High | 300–750 | 26–40 | 16–30 | 18–32 |
| Calamity | 1,200–3,000+ | 60–150+ | 60–150+ | 60–150+ |

These are authoring bounds and reference envelopes, not a guarantee for every Cartesian combination. Taking every axis at its maximum can exceed the intended encounter difficulty. Calamity upper reference values are open-ended for monster classification; this does not open human racial validation bounds. Every future concrete monster still needs explicit literal values and encounter evidence.

High and calamity tiers have no approved existing species in this roster. Their probes below are unshipped representative monsters, not newly authored species. Newly constructed instances use the updated authoritative variant data. No live-instance migration is introduced.



#### Scenario: No ratio requirement
- **WHEN** valid independent axis/HP values do not satisfy legacy HP ratio
- **THEN** they validate under their own ranges

#### Scenario: No new species
- **WHEN** updated envelopes load
- **THEN** no high/calamity species are shipped solely from representative probes

#### Scenario: Each monster tier's static band is beatable by the guild rank that handles it
- **WHEN** authoring classifies encounters relative to the listed equipped skilled human builds
- **THEN** section 8.1 solo/party expectations govern conditional evidence, with no bare-human-band overlap test or universal maximum-axis guarantee

#### Scenario: Calamity-tier monsters deliberately exceed the elf band and this is not corrected away
- **WHEN** an explicit calamity monster has values beyond the upper reference envelopes
- **THEN** open-ended monster bounds accept valid literals without consulting elf/beastfolk targets or changing finite human bounds

#### Scenario: HP bands scale with static bands at the documented ratio
- **WHEN** an authored monster HP is compared with its independent physical axes
- **THEN** the superseded fixed-ratio rule is not enforced; independent endurance and resolver encounter evidence govern authoring

