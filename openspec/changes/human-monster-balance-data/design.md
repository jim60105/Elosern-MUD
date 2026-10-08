## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 1 HP supersession; 8.1-8.3; 9 balance data; 10 data-contract discipline. Existing production seams are world/lore/monster_species.py; world/lore/monsters.py; world/lore/__init__.py; world/rules/monster_individual.py consumers; synthetic tier faces; monster lore/data docs.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Set all twelve variants to the approved literal HP/attack/agility/defense below, with MP/SP/magic zero. Retain species/variant keys, names, grades, ecology and behavior identities, and add no spells/abilities. Newly constructed instances read authoritative new rows; existing live instances are not migrated.
Replace the symmetric band projection in _default_tier_band_face with independent per-axis bands, validate each axis and HP separately with named errors, and migrate all registry/constructor/synthetic/export consumers. Calamity HP and physical upper limits are None/open-ended, with 3000/150 as reference points. Keep finite human RaceProfile/StaticTier validation unchanged and monster zero-magic policy. No static-to-HP ratio or elf/beastfolk equivalence remains in classification.
Envelopes express authored boundaries, not universal Cartesian balance. Future concrete monsters need complete literals and encounter evidence; no shipped high/calamity species are added. §8.1 human encounter expectations are policy context; resolver verification using actual military kits is separately owned by calibration evidence, which depends on this and equipment. Data can land independently of gear because no runtime dependency exists.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after the current main contracts are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused monster species/band/construction tests with asymmetric synthetic axes and calamity values beyond references; separate literal authored data-contract checks. Do not label projected balance evidence a real-kit test.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.

## Approved Numeric and Evidence Reference

The following excerpt is preserved from the approved design. Historical experiment outcomes remain conditional projected evidence unless explicitly replaced by recorded real-runtime measurements.

### 8.1 Human progression targets

| Human grade | Encounter expectation |
|---|---|
| F | A representative equipped beginner can handle ordinary F low-tier variants; stronger E variants remain risky |
| E | An equipped, basically trained human can defeat low-tier variants alone |
| D | A three-person human party can handle ordinary mid-tier variants; solo success is unreliable |
| C | A trained human can handle ordinary mid-tier variants alone; stronger variants need preparation or support |
| B | Mid-tier variants are decisively below the reference; lower high-tier threats can be faced |
| A | Upper-human capabilities support difficult high-tier assignments with explicit solo/party assumptions |
| S | Legendary human capability does not imply reliable solo victory over every high-tier or calamity threat |

These expectations describe the listed human builds and encounter conditions. They do not imply that every possible character allocation or strategy has the same outcome.

### 8.2 Approved twelve-variant profiles

MP, SP, and magic power remain zero for all twelve existing variants. Species keys, variant keys, names, grades, ecology, and existing behavior identities are retained. This change adds no monster spell or special ability.

| Variant key | Display name | Grade | Previous HP | Approved HP | Approved attack | Approved agility | Approved defense |
|---|---|---|---:|---:|---:|---:|---:|
| `grain_pecker` | 穗鳴雀・啄穗型 | F | 55 | 30 | 4 | 7 | 3 |
| `flock_leader` | 穗鳴雀・領群型 | E | 80 | 55 | 8 | 10 | 4 |
| `shore_walker` | 潮燈蟹・灘行型 | F | 70 | 30 | 5 | 4 | 5 |
| `reef_warden` | 潮燈蟹・守礁型 | E | 110 | 60 | 12 | 4 | 7 |
| `burrow_maker` | 築埂兔・掘巢型 | F | 60 | 30 | 4 | 8 | 3 |
| `nest_guard` | 築埂兔・護巢型 | E | 95 | 55 | 11 | 6 | 6 |
| `cliff_stepper` | 岩響山羊・踏崖型 | D | 240 | 130 | 20 | 16 | 12 |
| `pass_warden` | 岩響山羊・守隘型 | C | 330 | 170 | 26 | 14 | 14 |
| `wood_stalker` | 霧鬃山貓・林伏型 | D | 220 | 115 | 20 | 20 | 10 |
| `trail_hunter` | 霧鬃山貓・獵道型 | C | 280 | 165 | 25 | 22 | 12 |
| `bank_lurker` | 吞潮鱷・潛岸型 | D | 340 | 140 | 22 | 12 | 14 |
| `bay_warden` | 吞潮鱷・守灣型 | C | 400 | 210 | 28 | 12 | 15 |

Lower HP and selected defense reductions remove extended attrition. Stronger forms retain danger through increased offense or agility. Independent axes preserve the cat's mobility, crocodile's endurance, and crab's defensive character.

### 8.3 Approved authoring envelopes

| Monster tier | HP | Physical attack | Agility | Defense |
|---|---|---|---|---|
| Low | 25–70 | 3–12 | 3–12 | 2–8 |
| Mid | 110–230 | 18–28 | 10–24 | 10–16 |
| High | 300–750 | 26–40 | 16–30 | 18–32 |
| Calamity | 1,200–3,000+ | 60–150+ | 60–150+ | 60–150+ |

These are authoring bounds and reference envelopes, not a guarantee for every Cartesian combination. Taking every axis at its maximum can exceed the intended encounter difficulty. Calamity upper reference values are open-ended for monster classification; this does not open human racial validation bounds. Every future concrete monster still needs explicit literal values and encounter evidence.

High and calamity tiers have no approved existing species in this roster. Their probes below are unshipped representative monsters, not newly authored species. Newly constructed instances use the updated authoritative variant data. No live-instance migration is introduced.
