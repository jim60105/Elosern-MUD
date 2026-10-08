## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 5; 10 equipment commerce coverage. Existing production seams are world/lore/items/; world/lore/economy.py; world/lore/settlements/; world/rules/rulebook/equipment_effects.yaml; world/rules/rulebook/commerce/; equipment and shop tests.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Use the existing closed EquipmentModifierKey vocabulary and one-to-one item/effect binding. Select existing rarities whose budgets permit the approved bonuses. Never enlarge a budget to make authoring pass. Stable new item keys use military_<grade>_sword and military_<grade>_armor for lowercase e/d/c/b/a/s. They are mass-produced goods, with B-S repeatable arsenal enchantment and no purchase-rank gate.
Add magic_armor to the integer-copper price registry with minimum 10000 and unbounded maximum. Preserve mundane armor bounds and magic weapon minimum 100000. Each weapon joins common_arms and each armor common_outfits. Add finite initial/max/restock values using existing offer rules (initial 2, max 4, restock 1 per existing merchant day) and the existing resale convention; prices remain those approved below. If established offer validation requires a stricter positive stock shape, retain the quantities and adapt only the schema shape.
All ordinary merchants using these assortments receive the same goods. Guild limiting accessories belong to another change and cannot enter these assortments.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after the current main contracts are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused equipment-effect, shop-economy and assortment tests; one real-item equip/purchase/restock smoke with identical player/NPC effects. Separate tagged authored-data price/bonus checks from synthetic mechanics.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.

## Whole-Batch Requirement Ownership and Conflict Matrix

| Approved section | Owner | Acceptance seam |
|---|---|---|
| 1-2 boundaries, alternatives and non-goals | All changes; lifecycle/monster data own superseded contracts | Single writer, immutable bases, no bookings/compatibility |
| 3.1 stable branch qualifications | persistent-human-guild-hosts; lifecycle cuts old identities | Exactly one persistent branch/target person |
| 3.2-3.3 complete normal humans | persistent-human-guild-hosts | Gear, usable lineage/proficiency, cards, ages, homes/routes |
| 4.1-4.3 caps/accessories/A-S | guild-exam-restriction-policy | Every consumer, negative ordering, S domain |
| 4.4 atomic start/terminal/recovery | persistent-guild-exam-lifecycle | Cache rollback, HP0 simulation, identity survival |
| 4.4 held schedule release | guild-exam-schedule-hold core; lifecycle atomic wiring | Crossed weekly departure, no double time |
| 5 all bonus/price/stock/band rows | shared-military-equipment | Real equipment and finite ordinary shops |
| 6.1 cycle arithmetic | weekly-npc-schedule-cycles | Daily regression, seven-day tick-zero phase |
| 6.1 actual authored visits | persistent-human-guild-hosts | Daily Hok, weekly A/S real Exit routes |
| 6.2 read-only windows | planned-npc-service-windows | Busy/skipped/held/missing/exact-boundary results |
| 7.1-7.3 request order/schema/results | guild-exam-appointment-surface | Enabled below merit, absent read-only, present gated |
| 8.1-8.3 profiles/envelopes | human-monster-balance-data | Twelve literals, independent axes, open calamity |
| 8.4-8.8 every historical table/caveat | human-combat-calibration-evidence | Conditional projection and real-kit evidence separated |
| 9 subsystem flow/errors/observability | Each owner above | Reasoned rejection, rollback and facade traces |
| 10 focused tests/shards/traceability/docs | Every slice; appointment owns command docs | Actual runtime smokes, exact manifests, contract gate |
| 11 split roadmap/non-goals | This batch | Dependency/conflict ordering below |

| Shared implementation area | Changes | Conflict policy |
|---|---|---|
| Item registry/equipment effects | equipment, restrictions, hosts | equipment first; restriction and host touch different owned rows but coordinate shared file hunks |
| npc_schedules and schedule YAML/tests | cycles, reader, hosts, hold | cycles first; hold core then reader; host authoring may run on disjoint files; lifecycle consumes hold core |
| Guild config/economy/roster/profile inventories | hosts, lifecycle | hosts adds person-source/profile acceptance while rank factories remain valid; lifecycle removes obsolete rank sources/fields |
| guild_exams/combat_session/traits | restrictions, lifecycle, hold, appointment | restriction and hold cores precede lifecycle; lifecycle wires both atomically; appointment follows |
| lore-registries spec/economy/monsters | equipment, monster data | Behavior independent; same spec.md hunks require serial integration |
| Guild-rank-exams spec | lifecycle, appointment | appointment reads predecessor delta, modifies promotion request requirement only |
| shard manifests/test freeze/traceability | all | Append exact owned entries in serialized integration; no broad freeze expansion |
| master/schedule-design docs | appointment | Final integrated semantics amendment only |

The runnable initial wave is equipment + weekly cycles + monster data (shared lore-registries delta edits require serial integration). Hold core follows cycles; reader follows hold. Hosts and restrictions can run independently after their data prerequisites, coordinating shared item/schedule files. Lifecycle joins hosts, restrictions and hold core, activating no live persistent starts before complete deferral/release exists. Calibration and appointment can run after their prerequisites in parallel except shared test ownership manifests. Dependencies require predecessor apply/archive/sync completion, not merely proposal existence. No branch/worktree is created by proposal work.

## Approved Numeric and Evidence Reference

The following excerpt is preserved from the approved design. Historical experiment outcomes remain conditional projected evidence unless explicitly replaced by recorded real-runtime measurements.

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
