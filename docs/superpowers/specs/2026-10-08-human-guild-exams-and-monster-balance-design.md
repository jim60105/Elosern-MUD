# Human Guild Examinations and Monster Balance Design

**Date:** 2026-10-08
**Status:** Design approved; ten OpenSpec proposals complete; implementation not started.
**Scope:** Persistent human adventurer examination hosts, ability-limiting accessories, shared military equipment, human-based monster calibration, weekly NPC visits, and schedule-first examination requests.

This document captures the approved design decisions and the resulting OpenSpec proposal roadmap. The incomplete `examiner-calibrated-combat-balance` draft was removed before the ten proposals in section 11 were created. This document does not authorize implementation or amend current main capability specs outside the OpenSpec workflow.

## 1. Purpose and Architectural Boundaries

Guild rank should describe the combat capabilities of an equipped, skilled human adventurer. Monster grades must reflect those capabilities through the real combat engine. Bare physical-stat comparisons omit equipment, passive effects, skill coefficients, multi-strike attacks, defense bypass, and resource exhaustion.

The calibration viewpoint is exclusively the human adventurer organization. Elves are outside its classification and provide no balance targets. Beastfolk are not reference combatants. Human racial and static-tier bounds remain unchanged. Imported and authored base traits remain literal; skill multipliers and equipment effects are applied at resolution time.

The architectural source is [the engine design](2026-07-29-ai-mud-engine-design.md). This design preserves the deterministic single-writer boundary. Persistent mutations belong to `world/rules/`, with room and residence materialization owned by `world/maps/`. Lore registries and skill definitions remain immutable/read-only sources. AI dialogue may submit an examination request, but cannot change eligibility, schedules, restrictions, resources, or rank itself.

This document explicitly updates the following earlier design assumptions:

- Guild hosts fight as their persistent characters. A target rank no longer creates a disposable named opponent with replacement base traits.
- Monster HP is an independent endurance input. The previous fixed 15–20-times physical-stat relationship and bare-human correspondence are superseded by the approved profiles and encounter expectations below.
- [The NPC schedule design](2026-08-09-npc-schedule-design.md), sections 3.1 and 8, is extended from daily repetition to daily or seven-game-day repetition. Existing daily schedules keep their current behavior.
- The engine design's section 5.4 describes an older HP-at-1 examination policy. This design retains the current `guild-rank-exams` simulated-battle contract: ordinary HP-to-zero combat, no real death consequences, and full HP/MP/SP restoration before and after. It introduces no new HP floor or combat formula.

## 2. Approved Approach and Alternatives

The selected approach combines persistent adventurers with temporary restrictions, shared purchasable gear, and resolver-backed measurements. It preserves each host's normal identity and abilities while providing repeatable examination conditions.

Giving every rank a disposable examiner was rejected because the named characters would have no ordinary life or reusable full-strength state. Making one S-rank character host every examination was rejected in favor of a B-rank local senior and separate A- and S-rank adventurers. Raising base traits or granting 100-times amplification merely to produce rank labels was also rejected.

For attendance, the selected approach extends the existing NPC schedule engine and derives guild visit times from it. A separate guild calendar would duplicate the NPC's actual movements. Persistent reservations were considered and rejected. The UI uses appointment language, but the system stores no booking, place in a queue, reserved slot, cancellation, or expiry.

## 3. Persistent Adventurer Hosts

### 3.1 Identity and qualification

Implementation reference (`persistent-human-guild-hosts`): normal identities and
branch/target bindings live in `world/lore/guild_adventurers.py`; persistent
assembly and fail-closed dbref selection live in `world/rules/human_guild_hosts.py`.
The three hostless residences share the existing guild frontage at `(4,3)` and
use reciprocal ordinary Exits. Daily/weekly templates own the concrete offsets
documented in `docs/development/adding-npcs.md`; assembly binds route roles to room
dbrefs. This additive slice retains silent legacy rank factories until the
lifecycle owner cuts examination starts over atomically.

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

## 4. Examination Restrictions and Lifecycle

### 4.1 Limiting accessories

E through B examinations use the same qualified B-or-higher host. Rank-specific guild accessories temporarily seal disallowed capabilities and reduce combat values. They never raise a weak host to the target state. B also requires a restriction profile because another branch may use an A- or S-rank local senior for its E–B examinations.

The accessories are registered, mechanically implemented guild equipment using existing accessory-slot rules. They are non-tradeable guild property, absent from shop assortments, and cannot become purchase, sale, transfer, or loot rewards. The examination kit must leave a valid accessory slot instead of bypassing loadout validation.

An active examination restriction is persisted with its examination identity and host identity so reload and recovery cannot lose it. The rules core owns activation and removal. Learned skills and proficiency remain intact. The skill policy and every action-resolution path enforce the same restriction; changing only the NPC's preferred attack list is insufficient. Sealed actions are rejected before costs or effects, and sealed passive effects contribute nothing.

Allowed skill lists include the required lower sword lineage. They are execution/effect restrictions, not destructive edits to prerequisite ownership. Direct action requests, active-skill availability, passive stat readers, combat modifiers, gauges, and initiative must agree about the active restriction.

The restriction core exposes `preflight_exam_restriction`, `activate_exam_restriction`,
and exam-scoped `remove_exam_restriction` from `world.rules.guild_exam_restrictions`.
Profiles live in `rulebook/guild_exam_restrictions.yaml`; `guild_exam_restriction`
persists the exam/host identities, allowed skills, reducing neutral ceilings,
effective ceilings, and pre-activation equipment/inventory. The lifecycle slice
owns live start/terminal wiring and its wider normal-outfit/pool restoration.

### 4.2 E–B target states

| Target | HP ceiling | MP ceiling | SP ceiling | Attack ceiling | Agility ceiling | Defense ceiling | Magic ceiling | Highest permitted sword skill | Body enhancement |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| E | 100 | 100 | 100 | 11 | 8 | 10 | 10 | `basic_swordplay` | Sealed |
| D | 110 | 100 | 100 | 15 | 12 | 15 | 12 | `flowing_strikes` | Basic, 1.2 |
| C | 130 | 110 | 110 | 20 | 16 | 19 | 20 | `tendon_sever` | Basic, 1.2 |
| B | 145 | 110 | 110 | 25 | 20 | 24 | 25 | `thousand_blade_art` | Basic, 1.2 |

These are effective ceilings after permitted passive and equipment effects, before the chosen attack's damage coefficient. They do not multiply the final damage result. Negative combat effects remain consequential; caps must never raise a value reduced below the target. An underspecified or naturally weaker host cannot be promoted by an accessory to reproduce the reference build. Qualification validation must reject an unusable examination setup.

Establish the reduced neutral-state baseline before applying transient combat penalties. For example, D's pre-gear agility is 11; its one-point gear bonus and a five-point hamstring penalty produce hit-resolution agility 7. Subtracting that penalty from the stronger host's original agility and then clamping to 12 would conceal the penalty. Permitted positive changes remain bounded by the ceiling. Negative effects apply to the already reduced reference through the existing modifier rules.

The standard melee examinations seal `defense_instinct`, `concentration`, healing, purification, elemental/magical attacks, `gale_step`, and higher body-enhancement variants. Innate ordinary attack remains available. The player is not subjected to the host's restrictions, and the host is not scaled from the player's traits or disguise.

The present engine's initiative reads skill-effective agility before gear, while hit resolution includes gear agility. The projected E/D/C/B builds used initiative agility 8/11/14/17 and final hit-resolution agility 8/12/16/20. Real restrictions must reproduce both paths. Clamping only the damage or hit-resolution values would leave a stronger host with an unintended initiative advantage. This change preserves the existing general initiative formula.

### 4.3 A/S examination references

| Target | Base HP/MP/SP | Base attack/agility/defense | Base magic | Military-pair physical values before active effects | Top sword skill |
|---|---|---|---:|---|---|
| A | 170/120/120 | 17/17/16 | 30 | 30/25/29 | `blade_saint_arts` |
| S | 200/120/120 | 20/20/19 | 35 | 36/31/35 | `true_sword_saint` |

The A and S hosts use their respective rank's configured examination kit and usable sword lineage, rather than increasing Hok's capabilities. Standard examination selection seals unrelated utility effects for comparability. The S reference includes the current sword-saint lineage's domain effect, including its attack bonus; 36 is its pre-active-effect attack value, not a ceiling that removes the measured domain effect. No 100-times or 1000-times body multiplier is introduced to inflate these ranks.

A/S permit `body_enhancement_basic` at its existing 1.2 multiplier while
sealing `defense_instinct` and unrelated utilities. With the real military
pairs this gives A 30/25/29 and S 36/31/35 attack/agility/defense before domain
activation. These authored runtime-reference checks do not replace the later
calibration slice's encounter outcome evidence.

### 4.4 Start, settlement, and recovery

Actual starts still pass through `start_guild_exam`. Its authority, exact-next-rank, true-merit, co-location, branch, service-state, and no-active-battle checks remain authoritative regardless of the request surface. A schedule response does not create an attempt. Merit is never spent, passing advances one rank, and the existing title settlement remains atomic and idempotent.

Preflight validates the selected persistent host, qualification, profile, wearable loadout, restriction policy, and usable permitted lineage before mutation. The normal outfit and examination-owned state are snapshotted. Kit replacement, restriction activation, effective-pool restoration, examination record, combat session, and the existing start-affinity effect commit together. A failure restores ORM and handler caches as well as persistent attributes; it leaves no partial kit, restriction, attempt, affinity award, or session.

Both participants enter the simulation at full HP/MP/SP under their applicable limits. Ordinary resource costs and upkeep apply during combat. HP reaching zero ends the simulated fight; the simulation markers suppress kill rewards, ordinary defeat progression, protected-entity failure, and skill growth. The persistent host survives and is never deleted by examination cleanup.

On pass, fail, flee, bounded termination, or invalid recovery, settlement closes the session exactly once, removes examination-owned restrictions and temporary effects, restores the host's normal outfit, and restores both participants to full normal HP/MP/SP. The normal skill/proficiency records, persona, and identity are retained. The existing simulation's resource restoration is preserved; a new ordinary-injury system is outside scope.

Routine movement/state changes cannot interrupt an active examination. Schedule occurrences due during the examination are deferred for that host. After settlement, the rules core consumes the held interval through the same schedule occurrence and traversal machinery, in authored order, without advancing the clock a second time. A departure that became due during combat must not strand a weekly visitor at the guild for another week. The held interval is recoverable from persisted examination timing and the authoritative schedule, without a general-purpose booking queue.

The `guild-exam-schedule-hold` core implements these boundaries in
`world/rules/exam_schedule_holds.py`, using the existing `npc_schedules` source.
Its begin/read/release APIs persist the host ID, unique exam ID, start and
held-through ticks, consumed occurrence identity and released marker.
Begin uses the current persisted tick; release cannot consume future time.
Lifecycle callers restore the normal host before release and snapshot the hold,
location and schedule state around their enclosing transaction. This predecessor
provides synthetic terminal/recovery API-sequence evidence; production exam
activation and recovery wiring remain owned by `persistent-guild-exam-lifecycle`.
The read result distinguishes known absence/active/released state from a named
indeterminate hold; `planned-npc-service-windows` owns its availability use.

Cold-start recovery must distinguish the exam-owned hold and temporary kit from normal character state. It must either resume a valid simulation or close an invalid one and restore the persistent host. Deleting a host is never a repair strategy. A participant-name collision must be handled by the existing NPC identity/roster discipline before combat; display names do not replace persistent participant identity.

## 5. Shared Mass-Produced Military Equipment

Add six interchangeable weapon/armor pairs for E through S. The grade labels describe manufacture and supply, not unique relics or examiner ownership. B–S grades use repeatable arsenal enchantment. Players and NPCs use identical registered item keys and modifier definitions. There is no rank-based purchase restriction.

| Grade | Supply style | Weapon attack | Weapon agility | Armor defense | Armor agility | Weapon price, copper | Armor price, copper | Pair price, copper |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E | Recruit | 3 | 0 | 3 | 0 | 350 | 300 | 650 |
| D | Infantry | 4 | 0 | 5 | 1 | 800 | 1,800 | 2,600 |
| C | Ranger | 6 | 1 | 6 | 1 | 1,600 | 3,200 | 4,800 |
| B | Veteran/rune | 8 | 1 | 8 | 2 | 100,000 | 30,000 | 130,000 |
| A | Knight arsenal | 10 | 3 | 10 | 2 | 180,000 | 60,000 | 240,000 |
| S | Command arsenal | 12 | 4 | 12 | 3 | 300,000 | 120,000 | 420,000 |

The pair agility totals are 0/1/2/3/5/7. Amounts are integer copper; 10,000 copper equals one gold. Modifier magnitudes live in the existing equipment-effect rulebook, while item identity and presentation live in lore registries. Use existing validated rarity budgets and equipment-slot constraints; do not enlarge budgets to bypass a failed item design.

Weapons join `common_arms`; armor joins `common_outfits`. The existing corresponding ordinary merchants therefore expose purchases, sale rules, finite stock, and clock-driven restocking through their shared assortments. New offer rules must include valid finite initial/max stock and restock quantities through the established commerce configuration, not an unlimited-stock exception.

E–C equipment uses the existing mundane weapon and armor price bands. B–S weapons obey the existing 100,000-copper magic-weapon floor. Enchanted armor receives an explicit magic-armor price band with a 10,000-copper floor and no upper price ceiling, so the approved armor prices validate without weakening mundane armor bounds. These prices and ordinary availability remain distinct from the guild-owned non-tradeable limit accessories.

## 6. Weekly NPC Schedules and Read-Only Availability

### 6.1 One schedule model

The `weekly-npc-schedule-cycles` implementation exposes resolved
`ParsedSchedule.cycle_days` and its configured `cycle_seconds` property.
`world.rules.npc_schedules.due_occurrences` is the shared pure occurrence API
used by the existing settlement source. The availability and examination-hold
slices consume this API; this change does not implement those consumers or
author guild visits.

Extend the parsed schedule's cycle duration to distinguish one and seven game days. Templates and custom entry lists accept `cycle_days` equal to 1 or 7, defaulting to 1. A template reference inherits its template's cycle; per-entry overrides cannot change that cycle. Template schedules and custom schedules use the same cycle semantics. Entry offsets are bounded by their containing cycle; existing daily entries retain their current meaning, validation, ordering, and effective-from behavior. The model retains `schema_version: 1` with this explicitly amended optional-field contract.

Cycle length is derived from the configured game-day seconds. The current day is 24 times 3,600 seconds; a seven-day cycle is therefore 604,800 ticks. Cycle phase is anchored to absolute world tick zero, not NPC spawn, query time, season start, or year start. Assigning or reloading a weekly schedule must not restart its week.

Cassandra and Augustine each have one fixed visit interval per seven-day cycle. Their offsets may differ. Hok's daily visit intervals use the same engine and reader. No random arrival, private guild timestamp, wall-clock timer, or AI inference determines attendance.

Movement remains real Exit traversal with locks and vetoes. Existing per-entry failure isolation, schedule tags, effective-from boundaries, stable event ordering, and no-extra-clock-charge behavior remain intact. A failed arrival does not make an absent host available. Existing companion/service schedule-silencing rules also remain authoritative.

### 6.2 Availability query contract

A read-only schedule query consumes the selected persistent NPC, the requested guild destination, and the existing current world tick. It returns the next planned service-capable presence interval, with absolute start/end ticks, or a named unavailable result. The guild layer adds the host name, branch, and target rank; the presentation layer formats the existing game calendar date and interval.

The reader and settlement share occurrence arithmetic and parsed data. A guild-specific list of appointment dates is forbidden. The query projects future movement/state entries from the NPC's actual current location and state, applies effective-from and hold/silencing constraints, and accounts for blocking states. A move to the guild followed by a busy period must not be reported as an immediately usable examination interval.

Intervals are start-inclusive and end-exclusive. Same-tick entry ordering follows the schedule's existing entry-index ordering. If a planned arrival has already been skipped and the NPC is still absent, the query must not claim that the remaining portion of that interval is an actual presence; it finds a future planned arrival or reports uncertainty. An arrival due at the exact current tick is described as planned until actual location is confirmed.

Counter responses identify the correct host and state the next **planned** guild date and start/end time. Travel locks, another activity, or later schedule changes can invalidate the plan, so actual start always rechecks the live host. Queries reveal guild attendance only, not the person's private residence route or complete schedule.

Missing or malformed schedules, missing clock state, unresolved guild destinations, absent qualification, or an indeterminate hold/silenced schedule return an explicit inability to confirm a time. The reader must not create a clock, assign a schedule, move the NPC, initialize an examination, or fabricate an arrival date to produce a response.

## 7. Schedule-First Examination Requests

### 7.1 UI meaning

The guild action label is exactly **「預約升等考核」**. It means asking the guild to arrange the next promotion examination. It does not establish a persistent reservation. If the host is present and the actor passes the examination checks, that same action starts the examination.

The action stays available when merit is below the next-rank threshold. It also stays available at a functioning guild counter when the qualified host is absent. The UI may display current merit and its threshold, but merit qualification is separate from request availability.

A valid registered next-rank target and access to the appropriate local guild service are still required. An unregistered character must register first; an S-rank character has no next promotion. These target/service constraints do not become disguised merit checks.

### 7.2 Decision order

The shared rules-core request coordinator follows this order:

1. Resolve the actor's canonical registration, branch, next-rank target, and qualified persistent host. Validate the target and local counter/direct-host access needed for the request. Do not check merit yet.
2. Inspect the host's actual presence at the required guild location.
3. If the host is absent, read the next planned service interval and report its game date/time, or a named inability to confirm it. Return without checking merit, restoring resources, awarding affinity, creating an attempt, or mutating any examination state.
4. If the host is present, enter the ordinary examination checks. Revalidate host authority and service availability, true merit, and absence of an active battle/examination through the start API. A busy or otherwise unavailable present host returns its availability reason; it does not waive service gating.
5. Only a successful start creates the simulation and its transactional effects. A rejected start reports its specific examination reason.

The absent-host branch is read-only even for a character with insufficient merit or another reason that would prevent starting a fight. Attendance is resolved before those combat-start conditions. Neither a schedule query nor a clicked button counts as an examination attempt.

Text, WebClient, and validated NPC-intent entry points share the coordinator's order. The AI path has no additional authority. Browser payloads cannot select a different examiner, supply a clock/branch, override a threshold, or skip the next-rank rule. No adapter should first require a local `GuildExaminer` and reject the request before the counter can identify the absent qualified person.

### 7.3 Presentation and action contract

The current services-panel validator requires `eligible == exam_start.enabled`. Remove that relationship. Merit qualification and appointment-request availability are distinct facts. The server-authored menu, its schema validation, action adapter, client rendering, story fixtures, and affected tests must all adopt the same distinction. Changing only the visible label is insufficient.

Cut over the existing `guild.exam_start` action to `guild.exam_request`, and the rank panel's `exam_start` field to `exam_request`. Replace `eligible` with `merit_qualified`, which reports whether the registered next-rank member meets the true merit threshold independently of attendance. `exam_request.enabled` reports whether the local request service and valid target are available, without a merit or examiner-presence gate. Increment the services-panel schema from version 4 to version 5 and migrate every producer, validator, action registration, client consumer, and fixture together. No old action/field alias remains.

The request payload remains exactly `target_rank`; the actor, host, and branch are derived server-side. Results use distinct `exam_schedule` and `exam_started` outcomes, with the established rejection shape for an unknown/unconfirmable attendance time or a failed start. A valid timetable reply is successful schedule information even below threshold, and must not be labeled `exam_started`. The only mutation-capable start API remains `start_guild_exam`.

A schedule response gives the selected host and formatted planned interval or an explicit unknown-time reason. It never says that a booking was saved or a place reserved. An examination-start response retains the simulated-battle and resource-restoration explanation. Authored NPC speech remains in-character and does not name commands, UI controls, ticks, or engine rules.

## 8. Monster Balance and Measured Evidence

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

### 8.4 Experiment conditions and limits

Exploration executed 1,554 individual trials, including current profiles, candidate refinements, party comparisons, behavior-policy checks, and backend parity checks. Current low/mid comparisons used seeds 0–7; final candidate comparisons used seeds 0–15. Upper-envelope probes used seeds 0–7; full-B and C-support follow-up comparisons used seeds 0–15.

The subprocess used `uv run --locked`, configured SQLite `:memory:` before Django setup, and created real Evennia NPC, Monster, and Room objects. It exercised existing traits, skill and buff handlers, prerequisite initialization, ActionResolver, initiative, costs, upkeep, and `run_round`. Repeated trials used Evennia's native in-memory attribute backend for persistence speed. One E-versus-reef seed-zero comparison matched the SQLite-attribute result exactly. Both produced 54 rounds, 81 human HP, 4 SP, 12 basic-swordplay uses and 42 ordinary attacks.

Gear effects were projected at the equipment-adjustment boundary. E–B profiles used lower input traits/pools and permitted ownership equivalent to the target states, rather than real accessories worn by one unchanged senior. Therefore these results do **not** validate restriction implementation, shops, persistent NPC recovery, or identical effective values across all real cap consumers. Those are implementation acceptance criteria.

The F reference used the real character-creation resolver with a valid 224-point allocation. It allocated 69/69/69 into HP/MP/SP, 4/4/4 into physical attack/agility/defense, and 5 into magic. It produced HP/MP/SP 169/169/169, physical bases 5/5/5, and magic 10. The actual plains-human starting kit was worn, including plain sword, leather armor, and silver hairpin; final physical combat values were 7/5/9. This is one valid novice build, not a universal starting-human profile.

Human attacks followed strongest-first affordable skill selection with lower-skill/ordinary-attack fallback. Full B used a simple policy that heals at or below 40 percent HP when affordable, otherwise prepares concentration and gale-step once, then attacks. It is an exploratory strategy, not an optimized production NPC policy. Purification was owned but not exercised because the sampled monsters supplied no relevant condition.

Trials used full starting pools, no potions, no manually added regeneration or clock advancement, and a 200-round bound. Every action context and the round runner carried the simulation marker to freeze skill practice and prevent unlock drift. All sampled trials terminated and recorded zero rejected actions. Combat math was not reimplemented.

### 8.5 Final low-tier stand-and-fight outcomes

The controlled comparison used ordinary monster attacks without retreat so that a win meant reducing the monster to zero HP. Values below are wins out of 16 and victory-round medians.

| Variant | F wins | F rounds | E wins | E rounds |
|---|---:|---:|---:|---:|
| Grain pecker | 16/16 | 15 | 16/16 | 7 |
| Flock leader | 16/16 | 37 | 16/16 | 15.5 |
| Shore walker | 16/16 | 23 | 16/16 | 8 |
| Reef warden | 12/16 | 76.5 | 16/16 | 20 |
| Burrow maker | 16/16 | 14.5 | 16/16 | 8 |
| Nest guard | 15/16 | 74 | 16/16 | 15.5 |

The previous F shore-walker median was 107 rounds. Ordinary F variants now take about 14.5–23 rounds in this reference. Reef and nest remain stronger E-grade targets, with F losses and long fights; the table must not be summarized as every low-tier monster being safe for a beginner.

### 8.6 Final mid-tier stand-and-fight outcomes

| Ordinary variant | D solo wins | Three D wins / all-standing | Three D rounds | C solo wins | C rounds |
|---|---:|---|---:|---:|---:|
| Cliff stepper | 0/16 | 16/16 / 16/16 | 5 | 16/16 | 15.5 |
| Wood stalker | 3/16 | 16/16 / 16/16 | 5 | 16/16 | 11.5 |
| Bank lurker | 0/16 | 16/16 / 16/16 | 6 | 16/16 | 15.5 |

Their previous C-solo round medians were 51.5, 41, and 93 respectively. Lower endurance produces ordinary mid-tier fights with a clear party-versus-solo progression.

| Stronger variant | C solo wins | Three D wins / all-standing | Two C wins / all-standing | Two C rounds |
|---|---:|---|---|---:|
| Pass warden | 9/16 | 16/16 / 9/16 | 16/16 / 16/16 | 5.5 |
| Trail hunter | 6/16 | 16/16 / 8/16 | 16/16 / 16/16 | 8.5 |
| Bay warden | 5/16 | 14/16 / 5/16 | 16/16 / 16/16 | 11 |

“All-standing” means no human participant reached zero HP in that trial. It is not a claim about permanent companion death. Strong variants are C-support encounters; three D characters are not a safe-clear benchmark. Every restricted B mid-tier matchup recorded 16/16 wins with a 1–2-round median. Full B also recorded 16/16 throughout; its fixed preparation actions added turns to already short fights.

### 8.7 Real monster-policy outcomes

A separate pass used each variant's real behavior identity and `monster_behaviour_policy`. It distinguished actual defeats, monster retreats, human losses, and unfinished fights.

| Variant | Human reference | Monster defeats | Monster retreats | Human losses |
|---|---|---:|---:|---:|
| Grain pecker | E | 6 | 10 | 0 |
| Flock leader | E | 2 | 14 | 0 |
| Shore walker | E | 5 | 11 | 0 |
| Reef warden | E | 1 | 15 | 0 |
| Burrow maker | E | 5 | 11 | 0 |
| Nest guard | E | 3 | 13 | 0 |
| Cliff stepper | C | 5 | 11 | 0 |
| Pass warden | C | 0 | 14 | 2 |
| Wood stalker | C | 7 | 9 | 0 |
| Trail hunter | C | 0 | 11 | 5 |
| Bank lurker | C | 4 | 12 | 0 |
| Bay warden | C | 0 | 11 | 5 |

Every row contains 16 trials with zero unfinished fights and rejected actions. A retreat resolves an encounter without proving a kill, loot award, or hunt-objective completion. This change preserves that distinction and does not alter retreat credit.

### 8.8 Higher-tier probes

| Probe | HP / attack / agility / defense | Restricted B solo | A solo | S solo | Three A |
|---|---|---:|---:|---:|---:|
| High lower | 320 / 28 / 18 / 20 | 8/8 | 8/8 | 8/8 | 8/8 |
| High upper | 700 / 38 / 26 / 28 | 0/8 | 0/8 | 7/8 | 7/8 |
| Calamity lower | 1,200 / 60 / 60 / 60 | 0/8 | 0/8 | 0/8 | 0/8 |
| Calamity upper | 3,000 / 150 / 150 / 150 | 0/8 | 0/8 | 0/8 | 0/8 |

The high-lower restricted-B median was 14 rounds. Full B recorded 16/16 wins with a five-round median against that probe and 0/16 against high upper, despite successfully exercising utility and healing. These are results for the tested policy; they do not prove that every B strategy fails or establish a universal A boundary.

At high upper, the S victory median was 54 rounds. Only five of eight A-party trials finished all-standing. That endpoint is a hazardous upper-high challenge, not a comfortable or guaranteed S solo clear. The calamity probes exceed the tested lone-human and three-A capabilities. None of these four points validates every combination in its authoring envelope.

One existing skill issue remains outside this change. `basic_swordplay` has the same coefficient 1 as free `basic_attack` while spending eight SP. The measurements include that inefficiency. Do not silently change the skill or attack-selection optimization to make the approved balance appear stronger.

## 9. Components, Data Flow, and Failure Handling

| Unit | Responsibility | Input/output boundary | Dependencies |
|---|---|---|---|
| Lore and rulebook authoring | Stable NPC, branch, qualification, item, monster and schedule definitions | Validated keyed definitions | Existing registries, human/age bounds, lineage, slot and commerce validation |
| Schedule model and occurrence arithmetic | Daily/weekly parsing and due intervals | Parsed schedule and ordered occurrences | Existing clock day math and effective-from contract |
| Schedule availability reader | Next planned guild service interval, no mutation | NPC/destination/current tick to interval or named absence | Parsed schedule, actual location/state, shared occurrence arithmetic |
| Examination request coordinator | Presence-first branching across all request surfaces | Actor/target request to schedule information, rejection, or started simulation | Qualification, local service gate, availability reader, start API |
| Restriction and examination lifecycle | Reversible kit, caps, seals, persistent simulation and recovery | Validated profile and persistent host to atomic session/settlement | Equipment, skills, traits, ActionResolver, combat sessions, affinity and titles |
| Presentation adapters | Appointment label, request availability, calendar/time response | Server-authored menu and exact action results | Shared coordinator and existing OOB/command surfaces |
| Balance data | Approved literal variants and independent tier envelopes | Registry profiles consumed by normal construction/combat | Existing monster identity and behavior engine |

The schedule extension must reuse the existing settlement source; no second NPC movement scheduler is introduced. Pure occurrence arithmetic and the read-only query can be kept in focused sibling modules if adding them would overgrow `npc_schedules.py`, without moving unrelated scheduling behavior.

Start and settlement mutations remain transactional. Persistent exam state and in-process handler caches participate in rollback. Broken live schedule reads degrade to explicit unknown attendance. Invalid shipped item, skill, qualification, or loadout references reject authoring/start instead of substituting an unnamed host or fake equipment.

Operational events use named imports from `world.observability`, stable English snake-case events, and identifier-rich context. Start, restriction application/restoration, terminal settlement, schedule deferral/release, and recovery leave boundary traces. Exceptions are re-raised, logged with `exc`, or carry the existing reasoned exemption convention. No new direct logging import or freeze-list expansion is allowed.

## 10. Verification and Documentation Contract

Permanent mechanics tests use synthetic humans, items, schedules, branches, and monsters. Resolver-backed assertions establish behavior, boundaries, transitions, precedence, and rollback; they do not copy approved rows or inspect wording/source text. Authored-content checks remain separate data-contract checks under the existing freeze discipline.

Required behavior coverage includes:

- One persistent host starts repeated E–B exams without changing its normal base traits or learned ownership; stronger-qualified hosts are lowered, never raised.
- Permitted lineages resolve successfully, sealed direct actions cannot commit costs/effects, sealed passives do not contribute, and gauge/equipment/initiative cap consumers agree.
- Loadout and accessory-slot errors reject before mutation; fault-injected start/settlement failures restore inventory, equipment, restrictions, resources, affinity, records, sessions, and caches.
- Pass, fail, flee, and cold-start recovery preserve the host object, restore its normal capabilities, and settle promotion/title exactly once.
- Ordinary player and NPC use of the same military items produces the same equipment effects; commerce remains finite, transactional, and price-band validated.
- Daily behavior remains unchanged; weekly occurrences cross days, seasons, and years without phase reset or duplication; bulk and consecutive bounded advances agree.
- A weekly departure crossed during an examination is completed after the host's hold releases through real traversal, without double clock advancement.
- Attendance prediction agrees with the authored service-capable window; exact boundaries, busy states, skipped arrivals, missing data, and schedule silencing produce the defined outcomes.
- An absent-host request from a below-threshold member returns attendance information without a merit rejection or any examination state/resource/affinity change.
- A present-host request from the same member reaches the merit check and rejects without starting; an eligible present-host request starts the simulation.
- The below-threshold browser action remains available, its adapter reaches the shared coordinator, and command/intent paths cannot bypass the actual start gates.

Implementation smoke evidence must exercise a real persistent host wearing actual gear/restrictions, a weekly NPC's actual movement, and the actual guild appointment surface. The projected exploration is not a substitute. A focused browser test must observe the enabled appointment action below threshold and its schedule response, then the present-host merit rejection. Use a bounded local test class/file, not the CI-owned full browser suite.

Update `docs/game/commands.md` and `docs/game/command-reference.md` for changed examination semantics/availability, and preserve the command-doc contract. Update affected main/delta specs through the repository OpenSpec workflow. Main capability traceability uses canonical requirement IDs and substantive tests. Register any new test modules and browser methods in their exact shard manifests. Before implementation handoff, run the focused tests, observability/data lints when affected, and `uv run --locked python -m tools.contract_gate`; complete evidence verification remains CI-owned.

## 11. OpenSpec Proposals, Dependencies, and Implementation Batches

### 11.1 Proposal inventory and direct dependencies

The approved design is decomposed into ten one-workday-sized OpenSpec proposals. Each change has `proposal.md`, `design.md`, delta specs, and `tasks.md` under `openspec/changes/<change>/`. All ten proposal sets passed strict validation and were committed on `master`; none has been implemented or archived. The links below point to the active proposals. Their declared `depends-on` entries are the direct dependencies, including explicitly declared edges already implied by another predecessor.

| OpenSpec change | Deliverable | Direct predecessors |
|---|---|---|
| [`shared-military-equipment`](../../../openspec/changes/archive/2026-10-08-shared-military-equipment/proposal.md) | Six real weapon/armor pairs, effects, price bands, finite stock and restocking | None |
| [`weekly-npc-schedule-cycles`](../../../openspec/changes/archive/2026-10-08-weekly-npc-schedule-cycles/proposal.md) | Shared daily/seven-day parsing and absolute-tick occurrence arithmetic | None |
| [`human-monster-balance-data`](../../../openspec/changes/archive/2026-10-08-human-monster-balance-data/proposal.md) | Twelve literal profiles and independent tier envelopes with open calamity upper references | None |
| [`guild-exam-schedule-hold`](../../../openspec/changes/guild-exam-schedule-hold/proposal.md) | Persisted exam schedule holds and ordered departure replay through real Exits without a second clock advance | `weekly-npc-schedule-cycles` |
| [`persistent-human-guild-hosts`](../../../openspec/changes/persistent-human-guild-hosts/proposal.md) | Complete persistent Hok, Cassandra and Augustine, qualifications, skills, equipment, residences and daily/weekly routes | `shared-military-equipment`, `weekly-npc-schedule-cycles` |
| [`guild-exam-restriction-policy`](../../../openspec/changes/guild-exam-restriction-policy/proposal.md) | Wearable reducing-only accessories and consistent skill/stat restrictions, including penalty ordering and the S domain | `shared-military-equipment` |
| [`planned-npc-service-windows`](../../../openspec/changes/planned-npc-service-windows/proposal.md) | Read-only next planned service interval from actual location/state, including busy, missed-arrival and unknown-time outcomes | `weekly-npc-schedule-cycles`, `guild-exam-schedule-hold` |
| [`persistent-guild-exam-lifecycle`](../../../openspec/changes/persistent-guild-exam-lifecycle/proposal.md) | Atomic persistent-host simulations, outfit/resource restoration, rollback, cold-start recovery and disposable-factory removal | `persistent-human-guild-hosts`, `guild-exam-restriction-policy`, `guild-exam-schedule-hold` |
| [`human-combat-calibration-evidence`](../../../openspec/changes/human-combat-calibration-evidence/proposal.md) | Preserve conditional historical evidence and run bounded resolver probes with real gear, restrictions and hosts | `shared-military-equipment`, `human-monster-balance-data`, `persistent-guild-exam-lifecycle`, `guild-exam-schedule-hold` |
| [`guild-exam-appointment-surface`](../../../openspec/changes/guild-exam-appointment-surface/proposal.md) | Presence-before-merit coordinator across text/browser/NPC intents and complete services-v5 action/field cutover | `planned-npc-service-windows`, `persistent-guild-exam-lifecycle`, `guild-exam-schedule-hold` |

Monster data has no equipment prerequisite. Actual-kit calibration owns that dependency separately. Schedule holds must exist before the lifecycle enables persistent examinations; the lifecycle activates and releases them atomically with exam state.

### 11.2 Implementation batches

The following batches are a dependency-safe execution order. Changes within a batch may be implemented concurrently only when their shared-file ownership is coordinated. Individual `tasks.md` files remain the implementation checklists. Proposal existence or an unmerged implementation branch does not satisfy a dependency.

| Batch | Changes | Entry and completion boundary |
|---|---|---|
| 1: Shared data and schedule foundations | `shared-military-equipment`, `weekly-npc-schedule-cycles`, `human-monster-balance-data` | No new-change predecessors. Verify real equipment/commerce, daily/weekly occurrence behavior, and monster authoring independently; serialize shared lore-spec integration. |
| 2: Hosts and exam policies | `guild-exam-schedule-hold`, `persistent-human-guild-hosts`, `guild-exam-restriction-policy` | Required batch-1 predecessors are applied, verified, archived, synced and merged. Verify hold/release APIs, complete normal adventurers, and all restriction consumers. No persistent examination starts are enabled in this batch. |
| 3: Availability and persistent simulation | `planned-npc-service-windows`, `persistent-guild-exam-lifecycle` | Required batch-2 predecessors are complete. Verify read-only planned windows and real-host start/settlement/recovery independently; lifecycle integrates restrictions and schedule holds before enabling starts. |
| 4: Runtime evidence and request surfaces | `human-combat-calibration-evidence`, `guild-exam-appointment-surface` | Required predecessors from batches 1–3 are complete. Record bounded actual-kit evidence and verify the actual appointment surface, including absent-host/below-merit replies, present-host merit rejection, and successful starts. |

These batches are conservative synchronization points. A change may start once all of its direct predecessors have completed the apply, verification, archive/sync and primary-branch merge sequence, even if an unrelated change in an earlier batch is still running. For example, the availability reader can follow the hold change without waiting for host authoring or restriction policy.

### 11.3 Shared-file conflicts and integration ownership

The [whole-batch requirement ownership and conflict matrix](../../../openspec/changes/archive/2026-10-08-shared-military-equipment/design.md#whole-batch-requirement-ownership-and-conflict-matrix) records the approved-section owners. Parallel behavior slices still have shared integration boundaries.

| Shared area | Integration policy |
|---|---|
| Item registry, equipment effects and settlement assortments | Equipment lands first. Restrictions and hosts coordinate shared item/effect and settlement hunks while retaining their own authored rows. |
| Schedule model, YAML, occurrence helpers and tests | Cycles land before holds and the reader. Hosts coordinate authored routes; the reader consumes the completed hold contract. |
| Guild roster, qualifications and profile inventories | Hosts first add complete normal persistent people while old rank factories remain valid. Lifecycle subsequently removes obsolete factory fields, provenance and cards. |
| Examination, combat-session and trait consumers | Restriction and hold cores precede lifecycle. Lifecycle owns atomic activation/release wiring; appointment follows its authoritative start contract. |
| `lore-registries` main/delta spec | Equipment and monster data are behaviorally independent, but same-file spec synchronization and merge are serialized. |
| `guild-rank-exams` main/delta spec | Appointment preserves the completed lifecycle contract and changes the promotion-request contract after it. |
| Shard manifests, traceability and data-contract registrations | Each change registers only its owned entries; shared manifest integration is serialized. No freeze-list expansion is permitted. |
| Command references and earlier engine/schedule designs | Appointment owns the final integrated command documentation and earlier-design wording updates. |

### 11.4 Per-change gates and authorization

After implementation is authorized, apply each selected change on `feat/<change>` in `.worktrees/<change>` through the repository OpenSpec workflow. Read the completed predecessor contracts and the selected change's artifacts before editing. Follow its `tasks.md`; mark work complete only after verification.

Each change must pass `openspec validate <change> --strict`, its focused tests, its actual changed-path smoke, and `uv run --locked python -m tools.contract_gate` before handoff. Section 10 defines the runtime, browser, traceability and shard obligations; complete evidence verification remains CI-owned. Archive only completed, verified changes, sync their delta specs, pass the archive/post-sync gates, merge into the primary branch, and run `openspec validate --all --strict` as required by the archive workflow. A dependent implementation then consumes the merged current contracts.

This documentation update records the proposal plan without starting an apply or archive operation. The next execution gate is explicit authorization to implement selected proposals in dependency order.

### 11.5 Non-goals

Non-goals are difficulty selectors, race-specific combat exceptions, elf/beastfolk calibration, new F examinations, merit/reward changes, automatic reservations or queues, paid appointments, automatic waiting/teleportation/combat, new monster abilities, retreat kill credit, combat formula changes, general NPC strategy optimization, unrelated refactoring, database migrations, and backward-compatibility layers.
