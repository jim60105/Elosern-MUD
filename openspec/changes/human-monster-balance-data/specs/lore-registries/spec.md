## MODIFIED Requirements

### Requirement: MonsterTier registry has physical stat and HP bands derived from guild rank
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

