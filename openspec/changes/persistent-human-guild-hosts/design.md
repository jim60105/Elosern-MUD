## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 3.1-3.3; 6.1 authored visits; 9 authoring; 10 roster coverage. Existing production seams are world/lore/npc_profiles/altoria_guild.py; world/lore/dialogue/; world/lore/settlements/altoria/; world/rules/guild_config/; world/rules/guild_economy.py; world/rules/npc_roster_validation.py; world/maps/; NPC inventory and age ownership data.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Use authored profile identity and a stable persistent roster identity separate from profession and examination qualification. Qualification binds (guild_branch_altoria,target_rank) to exactly one authored person and persistent dbref; E/D/C/B select Hok, A Cassandra, S Augustine. Missing/duplicate/wrong-branch bindings fail closed. A new branch must author its own senior; no implicit Altoria fallback.
Normal bases are literal approved inputs, with no repeated coastal adjustment or player scaling. Initialize full actual sword prerequisites and required proficiency through existing lineage initialization; distinguish active/passive records. All three own Hok's shared utility set, with A blade_saint_arts and S true_sword_saint lineages. Their rank-matched military pair uses predecessor items. Normal Hok physical reference with passives is 25/20/29.
Author connected residences as ordinary Altoria places with world/maps-owned materialization and reciprocal Exit connectivity to existing public paths/guild. Choose concrete residence place keys and route entry targets during this change, validate every target and traversed Exit. No holding rooms or unresolved targets. Author Hok's morning/evening daily intervals and one fixed guild interval per weekly cycle for each A/S host in schedule data; document exact offsets and route hops in the implemented authoring doc. Routine includes departure/home/rest/service state and real traversal, not teleportation. No guild-counter timestamps.
Update cards, appearance, inventory and dialogue together. Hok is 45, coastal B, nearshore ship protection/escort/large hunts, using the B rune sword; remove far-ocean/fire-sword claims. Cassandra age/apparent 40/40 and Augustine 68/52 retain identity. Enforce 0..10000 integer ages, human restrictions and card bounds. Dialogue stays in-character, JRPG zh-TW, no commands/controls/ticks.
Idempotent synchronization never repositions or overwrites a live host's normal state, mutable persona, gear or active exam. Register new sources in the existing source/age inventories and roster preflight. This additive authoring slice does not retire rank-owned temporary examiner contracts: lifecycle owns that atomic cutover, and no gameplay compatibility aliases are added here.
Concrete residence bindings are hostless HOME places altoria_hok_home, altoria_cassandra_home and altoria_augustine_home, each with its own ordinary doorway at existing guild frontage exterior (4,3,capital_altoria). Distinct residences share the same public street node, consistent with the forge/outfitter shared-exterior pattern. Homes contain normal living descriptions, and host assembly associates the respective resident without a duplicate place-host creation path. Routes are home -> public frontage -> altoria_guild_hall and the reciprocal sequence; no private direct teleport or invented map cell. At schedule assignment, resolve stable place/grid bindings to the parser's already supported #<room-id> targets after map materialization; never persist display-name targets or hardcoded dbrefs. Missing/multiple room matches fail authoring preflight.
Hok's daily service windows are [08:00,12:00) and [18:00,20:00). Schedule each home-to-frontage hop 30 ticks before guild arrival; departure to frontage occurs at window end and home 30 ticks later. Cassandra's weekly service window is day index 1 [10:00,16:00), absolute cycle offsets [122400,144000). Augustine's is day index 4 [10:00,16:00), offsets [381600,403200). Their outward/inward hops likewise use 30-tick spacing. Day indices begin at absolute cycle tick zero. Home/resting state after return and service-capable state at guild arrival are explicit ordered entries; available daytime home interaction remains authored separately from sleep. Initialization starts each at its normal residence and does not replay past arrivals or restart cycle phase.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after shared-military-equipment, weekly-npc-schedule-cycles are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused roster/assembly/schedule integration tests using synthetic humans; tagged authored checks for exact host bindings, age pairs, bases and gear. Actual three-host smoke observes homes, Exit traversal and weekly arrival without forced positioning.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.

## Approved Numeric and Evidence Reference

The following excerpt is preserved from the approved design. Historical experiment outcomes remain conditional projected evidence unless explicitly replaced by recorded real-runtime measurements.

### 3.1 Identity and qualification

A character's profession is **adventurer**. Examination authority is a separate capability attached to that person for a named branch and supported target ranks. An adventurer can have normal dialogue, a residence, a schedule, equipment, learned skills, and relationships outside an examination.

Rank definitions retain rank order, rewards, titles, and progression meaning. Host identity moves to branch/rank qualification data instead of being a global per-rank opponent factory. Selection uses stable authored identity and persistent object identity, never a display-name search or the first NPC carrying an examiner component.

The initial branch is the currently registered `guild_branch_altoria`. No additional branch is invented by this change. Future branches must author their own local senior identities and qualification bindings; they must not silently reuse Altoria's person as a remote host.

| Examination target | Altoria host | Normal rank | Attendance |
|---|---|---|---|
| E, D, C, B | 霍克‧赤刃 | B | Authored daily routine with recurring morning/evening guild visits |
| A | 卡珊卓‧銀輝 | A | One authored guild visit per seven-game-day cycle |
| S | 奧古斯丁‧無名 | S | One authored guild visit per seven-game-day cycle |

Every host is one persistent NPC both inside and outside combat. An absent host is not summoned, cloned, teleported, or replaced. The current branch qualification must select exactly one person for the requested target; missing or ambiguous bindings fail closed. Multiple differently qualified hosts may be at the guild simultaneously without creating a generic-host ambiguity.

Each person needs a real, connected residence and a normal routine expressed through existing place and movement systems. The implementation must author complete residence and route bindings; an out-of-world holding room or an unresolved destination is not an acceptable residence. Exact daily/weekly visit offsets belong to NPC schedule data, separate from guild-counter code.

### 3.2 Hok's normal character

Hok remains a 45-year-old coastal human B-rank adventurer. His background is nearshore merchant-ship protection, land escort work, and large-monster hunts. The earlier far-ocean voyage claim is removed. His normal weapon is the registered B-grade mass-produced rune sword rather than an unimplemented personal fire sword. His persona, appearance, dialogue, and inventory must agree with his actual gear and occupation.

| HP | MP | SP | Physical attack | Agility | Defense | Magic power |
|---:|---:|---:|---:|---:|---:|---:|
| 145 | 110 | 110 | 14 | 14 | 13 | 25 |

These are literal final base inputs, already accounting for his authored subrace. The coastal adjustment must not be applied again. Human lore bounds still validate them.

His normal learned capabilities include the sword lineage through `thousand_blade_art`, `body_enhancement_basic`, `defense_instinct`, `concentration`, `heal`, `light_arrow`, `purify`, and `gale_step`. Active and passive ownership remain distinct. Existing lineage initialization supplies actual prerequisite ownership and required proficiency; listing a high-tier skill without a usable lineage is invalid.

With the B military pair and the listed passives, the measured normal physical reference is attack 25, agility 20, defense 29. This normal state remains available for ordinary interaction and any later story or companion use. This change does not add new companion recruitment rules.

### 3.3 A- and S-rank continuity

Cassandra and Augustine retain their existing identities and canonical age pairs. Cassandra is 40/40; Augustine is 68/52. Their cards are rewritten around their lives as adventurers, with occasional examination duty. Age and apparent age remain integers in `0..10000`.

Their initial normal base inputs use the A/S rows in section 4.3, with full normal skill ownership. Examination configuration seals unrelated capabilities without replacing those bases. Their combat authoring must provide the full usable sword lineage corresponding to their ranks, ordinary survival/utility capabilities, and registered normal equipment. The shared utility set is the existing healing, purification, concentration, light attack, movement enhancement, body enhancement, and defensive instinct capabilities listed for Hok, plus the appropriate sword lineage. Human-only skill restrictions remain enforced. Their cards may describe only equipment and abilities that their actual configuration supports.

The A/S upper-tier probes in section 8 are reference builds. They establish initial examination-kit targets and conditional balance evidence; they do not verify fully authored Cassandra/Augustine objects, weekly schedules, or restrictions.

### Normal A/S numeric references
| Target | Base HP/MP/SP | Base attack/agility/defense | Base magic | Military-pair physical values before active effects | Top sword skill |
|---|---|---|---:|---|---|
| A | 170/120/120 | 17/17/16 | 30 | 30/25/29 | `blade_saint_arts` |
| S | 200/120/120 | 20/20/19 | 35 | 36/31/35 | `true_sword_saint` |

The A and S hosts use their respective rank's configured examination kit and usable sword lineage, rather than increasing Hok's capabilities. Standard examination selection seals unrelated utility effects for comparability. The S reference includes the current sword-saint lineage's domain effect, including its attack bonus; 36 is its pre-active-effect attack value, not a ceiling that removes the measured domain effect. No 100-times or 1000-times body multiplier is introduced to inflate these ranks.
