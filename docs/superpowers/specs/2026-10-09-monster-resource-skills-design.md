# Monster Resource Skills and Shared Eligibility Design

**Date:** 2026-10-09
**Status:** Design sections and written specification approved; implementation not started.
**Scope:** Shared skill identity eligibility, reusable hit-dependent effects, and one complete tide-devouring crocodile resource-skill integration.

Extend the existing player/NPC skill system to support authored monster abilities. Keep one execution engine and separate monster ability declarations from character skill-tree content. The first delivered species is 吞潮鱷 (`tide_devouring_crocodile`), whose physical bite drains MP on a successful hit and consumes both MP and SP. Combat AI receives the minimum integration needed to execute this ability. Its strategy redesign belongs to the next change.

## 1. Authority and Scope

The [engine architecture](2026-07-29-ai-mud-engine-design.md) remains authoritative. `world/skills/` supplies immutable definitions and read-only queries. `world/lore/` supplies identity and variant registries. `world/rules/` validates and applies skill, resource, and combat state changes. `world/ai/` does not participate in monster decisions or mutate state.

This design updates the ability deferral in the [monster data model](2026-10-05-monster-data-model-design.md), sections 3 and 8, for the crocodile alone. It supersedes the earlier zero-MP/SP approval for its two variants with the literal values in section 5. Other species retain their approved profiles and deferred special abilities.

The [human guild and monster balance design](2026-10-08-human-guild-exams-and-monster-balance-design.md) remains separate. This change does not retune human references, change combat formulas, or claim that existing crocodile danger grades have been recalibrated after adding resource pressure. The new values are user-approved initial settings, with no measured balance claim.

Implementation follows the repository OpenSpec workflow. This document records approved design decisions; it does not change current main capability specifications or authorize implementation before written-spec approval.

## 2. Current Implementation and Selected Approach

`MonsterCombatProfile` already carries literal HP, MP, SP, physical attack, agility, defense, and magic power. All twelve currently registered variants have zero MP, SP, and magic power. `initial_trait_config_for_variant()` applies approved profile values through the shared gauge/static trait construction path. `construct_species_individual()` currently applies identity and traits inside a transaction.

Monsters share `SkillHandler` with characters. Its owned list comes from individual skill storage plus universal innate actions. `SkillDef.prerequisites` may be empty. An owned ability without prerequisites needs no fabricated progression chain. The lineage view starts chains from prerequisite-free roots consumed by another skill; isolated abilities do not create trees.

`ActionResolver` owns action validation, effect staging, resource costs, and transactional commit. Existing `GaugeTransferEffect` and `GaugeTransferPolicy` support MP drain with caster recovery calculated from the amount actually removed. Damage and gauge transfer are currently dispatched independently. Listing both effects alone does not make transfer conditional on a damage hit.

Monster policy currently selects affordable active damage skills. The crocodile's damage-plus-drain composition fits that existing action shape. Qualification filtering needs the shared eligibility predicate; a generalized utility-skill planner is outside scope.

### Alternatives

| Approach | Benefit | Limitation | Decision |
|---|---|---|---|
| Shared execution with separate monster declarations and identity eligibility | Reuses resource, targeting, event, and rollback behavior while preserving species abilities | Requires explicit eligibility metadata and a hit-dependency contract | Selected |
| Use existing character skills unchanged for every monster | Smallest content changes | Existing spells may lack the required contact or species semantics | Reuse when semantics already match |
| Separate monster skill engine | Independent authoring model | Duplicates resolution and persistence rules and creates divergent behavior | Rejected |

## 3. Shared Identity Eligibility

### 3.1 Definition contract

Extend `SkillDef` with immutable, declarative identity eligibility. The supported vocabulary is closed and typed. It covers allowed actor kinds, registered races, registered subraces, registered monster species, and required race capabilities. An omitted restriction adds no requirement. Ownership, prerequisite proficiency, restrictions, and action-specific validation still apply.

An allowed list accepts any member. Different declared restrictions are combined with AND. An explicitly supplied empty allowed list is an authoring error, avoiding an ambiguous distinction between unrestricted and impossible. Unknown identifiers, unsupported capability names, and contradictory actor/identity requirements fail during registry validation.

Character race and subrace continue to use `RACE_REGISTRY` and `SUBRACE_REGISTRY`. A subrace restriction validates the entity's stored race/subrace pair and the registry's parent relationship. If both race and subrace lists are declared, every allowed subrace must belong to an allowed race.

Monsters continue to use `species_key` and `variant_key`. They are not added as artificial races or subraces. Actor-kind identification uses deterministic typeclass identity; the presence of a race-like attribute does not turn a monster into a character. Monster-only eligibility can accept every monster or narrow to registered species. A species restriction requires a valid species/variant identity pair. Variant-specific skill gates are outside this change; variants author different owned kits instead.

The crocodile bite declares monster identity and the `tide_devouring_crocodile` species. A different monster cannot execute the bite even if its skill storage is misconfigured. Shared skills retain no additional identity requirement.

### 3.2 Divine-arts cutover

Replace `SkillDef.requires_divine_arts` and its independent action gate with the shared eligibility contract. Divine skills declare the required race capability corresponding to `RaceProfile.can_use_divine_arts`. Keep that race-profile field and its existing values as the authority. Do not replace the capability lookup with a hardcoded elf-name check.

Migrate every consumer of the old skill marker, including import validation, registry/category invariants, availability queries, and the sexual-act mastery blanket's divine exclusion. Preserve the separate divine acquisition rules, category-specific practice cadence, and non-divine shared behavior. Eligibility does not grant ownership. No deprecated field, alias, or parallel eligibility path remains.

### 3.3 Shared consumers

A pure identity-eligibility query must be reusable by record validation and runtime entities. Record validation provides the intended actor kind and authored identity; it does not need to construct an entity. Runtime queries use the entity's persistent identity.

`can_use_skill()` combines identity eligibility with its existing ownership, restriction, and prerequisite checks. The resolver must distinguish an identity failure from a missing prerequisite without assuming that every false result has a prerequisite edge. Qualification rejection occurs before dice, costs, effects, or practice writes.

Passive-effect reads also enforce identity eligibility, preventing an accidentally assigned racial or monster passive from changing effective traits. Import and grant paths reject ineligible ownership. Monster construction validates the complete kit before persistence. Presentation uses the same identity query to exclude ineligible player catalog and lineage entries; eligibility checks do not duplicate proficiency or resource rules.

Keep skill category and group as presentation taxonomy. They do not grant permission. Store monster-specific declarations in separate domain data modules and assemble them into the existing runtime registry. Do not create a second mutable registry or skill handler.

This change supplies the mechanism for future beastfolk subrace abilities without authoring those abilities now.

## 4. Reusable Hit-Dependent Effects

Add per-effect metadata allowing an effect to require a hit from one explicitly referenced earlier damage occurrence in the same skill. Use the existing ordered effect and per-occurrence policy model. Validate dependencies at registry load. The source must exist, precede the dependent occurrence, and be a damage effect. Unsupported references fail before play.

During final resolution, expose typed, invocation-local hit outcomes keyed by source occurrence and target identity. The damage handler supplies the outcomes from its existing hit rolls. The dependent effect receives the subset of its already-valid audience that the referenced damage occurrence hit. Do not parse `PendingEffect.description`, `EventLog` prose, or client-supplied context to determine success. Caller input cannot forge the outcome record. Preflight checks dependency structure without rolling or manufacturing hit outcomes.

Dependency means hit, independent of final HP loss. A hit whose damage is diverted or absorbed still qualifies. A miss does not qualify. A dependency never adds a second hit roll. For a source with multiple strikes, a dependent occurrence executes once per target if any source strike hits; it does not multiply per strike. The first skill has exactly one strike.

Keep ordinary audience restrictions and target validation in force. A hit-dependent target effect cannot expand its recipients to an entity absent from the referenced source's hit set. Skills without dependency metadata retain their existing behavior. The contract permits later status or other supported target effects to use the same dependency mechanism.

Damage, dependent MP transfer, resource payment, and existing practice writes share the normal action transaction and rollback surfaces. Any failure restores both participants and releases rolled-back practice claims. There is no persistent cross-round hit flag.

## 5. Approved Crocodile Ability and Profiles

### 5.1 Ability

Use the player-facing ability label 吞潮咬擊 and the authored key `tide_devouring_bite`. Both existing crocodile variants own the same active ability. It has no prerequisites and no new passive. Existing innate `basic_attack` and `flee` remain available.

| Property | Approved value |
|---|---|
| Identity eligibility | Monster, species `tide_devouring_crocodile` |
| Presentation taxonomy | Existing elemental-magic category, water group; eligibility keeps it out of the player catalog |
| Action shape | Active, one enemy target, combat only |
| Contact | Existing close physical-attack targeting and displacement rules |
| Physical component | Ordinary physical attack formula, coefficient 1.0, one strike |
| Elemental identity | Water; physical school remains the damage stat source |
| MP cost | 10 per use |
| SP cost | 5 per use |
| Hit-dependent drain | Up to 10 current target MP |
| Recovery | 100% of actual MP removed, capped at caster MP maximum |
| HP restoration | None |
| Fixed magic-power reduction | None |
| Freeform scaling | Ineligible under the existing mixed damage/transfer shape rule |

The bite uses the existing water-associated physical damage representation and gauge-transfer effect. Its damage reads `atk_phys`; fixed MP drain reads neither attack nor `magic_power`. The 10-MP elemental cost belongs to the existing single-target apprentice cost band. Do not change cost classifications to accommodate the ability.

The target's zero MP does not cancel the physical component. Critical hits affect the ordinary damage result and do not increase drain quantity or occurrence count. A hit may complete its dependent transfer as part of the same action even if its damage crosses the target's defeat threshold; ordinary defeat settlement follows the action. No healing or permanent stat change is implied.

### 5.2 Literal complete profiles

| Variant | HP | MP | SP | Physical attack | Agility | Defense | Magic power | Existing danger grade |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `bank_lurker` | 140 | 30 | 40 | 22 | 12 | 14 | 0 | D |
| `bay_warden` | 210 | 50 | 60 | 28 | 12 | 15 | 0 | C |

Only MP and SP change from the current profiles. Magic power stays zero because damage uses physical attack and drain is fixed. Existing zero magic-power tier bands remain valid. No resource values are inferred from tier, player power, prose, or another variant.

At 5 SP per use, the initial SP pools can pay for eight and twelve uses respectively before any recovery. These are resource-capacity counts, not predictions of how many bites a fight contains.

### 5.3 Cost and recovery order

Preserve the resolver's current order. Validate affordability before resolution. Stage damage, target drain, caster recovery, and then MP/SP costs in the existing transaction. The actor must already be able to pay both costs; the proposed drain cannot finance a previously unaffordable action.

Recovery is capped before the later cost payment. A full 30-MP `bank_lurker` that hits and removes 10 MP remains at 30 after recovery and finishes at 20 after paying. Starting at 20, it recovers to 30 and finishes at 20. When the target has 3 MP, at most 3 MP is removed and credited before the caster cap. At zero target MP, nothing is recovered. A miss still pays 10 MP and 5 SP.

Existing resource modifiers and MP reaction paths continue to apply through the shared cost and transfer APIs. Authoring establishes the nominal values above. Recovery overflow is discarded and never stored for later use. This change does not reorder settlement for existing skills.

## 6. Construction, Persistence, and Minimum Policy Integration

Extend the frozen variant configuration to reference an ordered active/passive skill kit and an existing behavior-profile key. Validate registry references, identity eligibility, prerequisite usability, effect availability, and applicable profile data before creating the individual. Apply identity, literal traits, skill ownership, and behavior binding atomically. Preserve the existing construction boundary event and include available kit/profile identifiers in its context when the boundary changes.

Variants without authored special abilities continue with the existing innate actions and tier-default behavior. They receive no invented resource pools or automatic spells. Species-specific abilities remain owned configuration rather than an inference from names.

For the crocodile, configure a minimal reusable profile using the existing `first_owned` skill strategy, `lowest_hp` target strategy, no area preference, and the current mid-tier flee fraction of 0.20. Put the bite before innate attack in owned order. Other profiles and their target selection remain unchanged.

Add shared eligibility/prerequisite filtering where required by the existing monster action provider. Keep its affordable-damage-skill shape. An ineligible or unaffordable bite falls back to an available ordinary attack. Final action resolution remains authoritative if initiative changes state after policy selection. Respect existing displacement, living-target, knockout, and flee behavior.

Do not add MP-aware target evaluation, benefit scoring, cooldowns, rotations, utility-skill planning, new randomness, or a new behavior engine. The next AI change can replace policy without changing skill definitions or execution.

Persist owned kits and current gauge values using existing Evennia Attributes and handlers. Reload retains depleted resources. Registry edits do not silently rescale or refill already-existing individuals. Ordinary world-clock recovery remains unchanged. Updating an existing live individual, if needed, uses the authorized GM rules workflow rather than startup overwrite or a Django shell. No automatic data migration or compatibility layer is added.

## 7. Content and Consumer Updates

Update the crocodile's public ecology and relevant author notes to describe the implemented bite and its limits. Retain close contact, MP resource pressure, no remote river-wide drain, no HP healing, and no permanent magic-power loss. Remove assertions that this species' effect or numbers remain unimplemented. Other five species keep their deferred content and existing boundaries.

Document the eligibility authoring contract, separate monster ability modules, effect dependency semantics, and the crocodile resource behavior in the affected existing documentation. The implementation must update every old divine-marker consumer and affected tests. Main-spec amendments occur through OpenSpec deltas, including replacement of literal old-marker requirements and changes to lineage filtering and monster construction contracts.

The registered player command surface remains unchanged. If implementation changes any command syntax or availability, both command documentation files must be updated under the existing repository rule.

## 8. Verification and Acceptance

Use deterministic synthetic identities and abilities for reusable behavior tests. Shipped crocodile content assertions belong to explicitly registered data-contract tests. New test modules must have exact shard ownership.

| Boundary | Required observable evidence |
|---|---|
| General eligibility | Race, subrace, parent mismatch, missing identity, actor kind, species, and race-capability allow/reject cases |
| Shared skill behavior | Existing shared skills remain usable by eligible owning characters and monsters; eligibility never grants ownership |
| Divine cutover | Existing divine racial rejection, valid casts, passive behavior, acquisition exclusions, and practice cadence remain intact |
| Misconfigured kits | Ineligible active casts reject before costs/dice; ineligible passive ownership contributes no effect; imports and construction reject invalid assignments |
| Player exposure | Monster-only abilities and trees do not enter player catalogs or lineage counts; valid racial character abilities remain eligible for their identities |
| Hit dependency | Hit executes the rider, miss does not, no extra hit roll, diverted damage still qualifies, malformed references fail, multi-strike source yields one rider per target |
| Resources | Partial/zero target MP, full caster MP, exact costs, insufficient MP or SP, miss payment, and approved effect-before-cost order |
| Atomicity | Failure after staged damage/transfer restores actor and target gauges plus other touched state; no partial ownership/configuration on construction failure |
| Real crocodile path | Formal construction creates both approved variants with usable kits; actual combat rounds execute the bite and fallback attack after exhaustion |
| General reuse | A synthetic second species executes an eligible ability through the same dependency/transfer APIs without a species-specific branch |
| Persistence | Reload retains identity, owned kit, behavior profile, and current depleted gauges |

The runtime smoke must construct the approved crocodile through the production entry point and exercise a real resolver-backed combat session. Observe HP loss and both participants' MP plus caster SP, a miss, and resource exhaustion followed by ordinary attack. No live generative or image service is used. Focused tests complement that smoke; they do not replace it.

Run the focused affected tests, observability lint when logging changes, data lint, strict OpenSpec validation, and the local contract gate. Broad CI evidence remains CI-owned. No passing runtime or calibration claim is made by this design document.

## 9. Delivery Order and Non-goals

Keep one design document for the shared eligibility and effect contracts plus their crocodile consumer. The implementation planning step must size repository OpenSpec changes to the project convention. Eligibility cutover and hit-dependency work are prerequisite units; the crocodile integration consumes both and supplies the end-to-end acceptance evidence. A prerequisite alone does not complete this feature.

### OpenSpec proposal set

All three changes have complete proposal, design, delta-spec, and task artifacts. Implementation has not started.

| Order | Proposal | Scope | Dependencies | Proposal commit |
|---|---|---|---|---|
| 1 | [shared-skill-identity-eligibility](../../../openspec/changes/shared-skill-identity-eligibility/proposal.md) | Shared race, subrace, species, actor-kind, and race-capability qualification; complete divine-marker cutover | None | `d33f993a` |
| 2 | [skill-hit-dependent-effects](../../../openspec/changes/skill-hit-dependent-effects/proposal.md) | Typed invocation-local hit dependencies, audience intersection, and existing atomic settlement | Logically independent of the eligibility change; serialize because of shared files | `2c0d92ae` |
| 3 | [tide-devouring-crocodile-resource-skill](../../../openspec/changes/tide-devouring-crocodile-resource-skill/proposal.md) | Approved bite and resource profiles, atomic construction, minimal existing-policy integration, persistence, and complete combat-loop verification | Both preceding changes | `753d065a` |

Apply, verify, and archive each change in the listed order before starting the next. The two prerequisite changes overlap in skill definition, action tests, authoring documentation, and shard ownership. The crocodile integration also shares documentation and test-registration surfaces with its prerequisites. Avoid concurrent implementation despite the prerequisites' logical independence.

### Non-goals

Excluded work includes other species abilities, new beastfolk content, a second skill engine, artificial monster race records, arbitrary rule expressions, creature-specific resolver branches, combat AI redesign, new battle formulas, global cost-order changes, difficulty scaling, automatic existing-object resets, and recalibration of human references or monster grades.

The written specification must be reviewed and approved before implementation planning proceeds.
