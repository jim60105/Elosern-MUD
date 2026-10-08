## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 4.1-4.3; 9 restriction policy; 10 consumer coverage. Existing production seams are world/rules/equipment.py; world/rules/action.py; world/rules/traits.py; world/rules/combat_modifiers.py; world/rules/combat.py; world/skills/ read consumers; world/rules/combat_view.py; world/rules/rulebook/; item registry; restriction tests.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

A/S permit body_enhancement_basic at 1.2, separately sealing defense_instinct and unrelated utilities. Their real-kit pre-domain physical baselines are 30/25/29 and 36/31/35; S domain then adds its existing measured bonus.

Persist an exam-owned restriction record keyed by exam_id and host dbref, activated/removed only by rules-core APIs. Accessories are registered equipment with valid normal accessory slots, non-tradeable guild property, no shop/transfer/loot/reward routes. Profile E/D/C/B contains permitted innate ordinary attack and full lower sword lineage; D/C/B permit body_enhancement_basic 1.2, E seals it. All seal defense_instinct, concentration, heal, purify, light/elemental attacks, gale_step and higher body enhancement. A/S kits permit their full sword lineage and seal unrelated utilities for comparison; S retains measured domain bonus above pre-active attack 36.
Restriction policy is execution/effect overlay; never delete learned ownership/proficiency or overwrite immutable normal bases. ActionResolver rejects sealed direct actions before costs/effects, active availability uses the same predicate, sealed passive readers contribute zero. Cover gauges, skill-effective pregear initiative, equipment stat readers, hit/modifier resolution and combat presentation through one restriction interpretation.
E/D/C/B effective ceilings are post-permitted-passive/gear and pre-attack coefficient. Construct reduced neutral baselines first, then apply existing transient modifiers. Negative changes can fall below ceilings and must never be raised. Cap later permitted positive changes; do not clamp original stronger-host debuffs back to the target. Pregear initiative targets 8/11/14/17, final agility 8/12/16/20. D hamstring example is 11 +1 -5 =7. Qualification rejects naturally weaker/underspecified hosts or invalid lineages/loadouts instead of amplifying them. B restrictions support future A/S seniors.
A/S base references and military pairs remain separate normal builds. No combat formula change, final-damage multiplier, 100/1000 body amplification, player restriction or disguise-based scale.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after shared-military-equipment are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

Focused synthetic restriction module plus affected action/traits/initiative/equipment consumers. Wear real accessory and pair, never project equipment adjustments; compare complete base/ownership/proficiency snapshots before/after. Test slot overflow and forbidden sale/transfer/loot paths.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.

## Approved Numeric and Evidence Reference

The following excerpt is preserved from the approved design. Historical experiment outcomes remain conditional projected evidence unless explicitly replaced by recorded real-runtime measurements.

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
