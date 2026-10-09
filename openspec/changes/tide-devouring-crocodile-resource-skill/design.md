# Design

## Context

The approved authority is the monster resource-skill design sections 5 through 8. Both prerequisite changes must be applied, verified and archived first. Current frozen MonsterVariant and MonsterCombatProfile live in world/lore/monster_species.py. `construct_species_individual` validates identity/trait configuration before its atomic create/assign sequence and records `monster_individual_constructed` on durable commit. `SkillHandler` returns stored active/passive keys before innate basic_attack/flee. `BehaviourProfile` already supports first_owned/lowest_hp/no-area/flee leaves and `behaviour_tree` persistence. The action provider currently filters affordable active damage skills without shared use qualification.

## Goals / Non-Goals

Deliver the complete approved crocodile loop with existing skills, transfers, construction and combat sessions. No other species implementation, AI scoring/rotations, extra random behavior, cooldown system, HP healing, magic-power reduction, cost-tier redesign, automatic live reset or balance calibration. Architecture remains unchanged; world/ai never makes monster decisions.

## Decisions

### Authored content assembled into one registry

Add `world/skills/registry/data_monster_abilities.py` as a separate domain slice and assemble its ROWS in registry/assembly.py without a second mutable registry or handler. Declare tide_devouring_bite labeled 吞潮咬擊, active SINGLE, combat-only, water element, elemental-magic/water taxonomy, faction ANY with enemy audiences for both effects. Use `damage:water:physical`, coefficient 1.0, one strike, followed by existing fixed MP drain syntax at 10 and GaugeTransferPolicy recovery share 1.0. The second occurrence references the first's hit outcome. Cost is exactly {mp:10, sp:5}; no prerequisites/passive. Its mixed damage/transfer shape remains freeform-ineligible and apprentice single-target cost labeling remains existing behavior.

The declaration requires monster actor kind and tide_devouring_crocodile species; another monster with a corrupt stored bite cannot cast it. Enemy routing preserves the main targeting contract's unrestricted candidate selection and existing faction vocabulary. Existing physical contact and displacement consumers identify the physical school. No species branch is added to resolution or transfer.

### Literal profiles and validated configuration

Only bank_lurker and bay_warden MP/SP change. The complete profiles are respectively HP/MP/SP/atk_phys/agility/defense/magic_power 140/30/40/22/12/14/0 (grade D) and 210/50/60/28/12/15/0 (grade C). Grade and all other numeric axes remain unchanged. No measured balance claim is made. The other ten variants retain zero MP/SP/magic_power and all five deferred species retain their existing content.

Extend frozen MonsterVariant with optional ordered active/passive key tuples and optional behavior-profile key, with empty kits/default profile preserving current variants. Author both crocodile kits with the bite as the sole special active key, before innate actions. A prerequisite-free isolated ability requires no progression chain. Construction validates the entire kit, including unknown/duplicate or wrong-kind keys, identity eligibility, usable authored prerequisite closure/proficiency and supported handler references; it must not invent chains or silently seed a monster's missing authored ability prerequisites. The crocodile has no such edges. Behavior references must resolve before creation; applicable profile data remains validated through existing lore/traits paths.

Keep lore and skills read-only. The construction-owned validator can import skill registry and behavior profiles without making lore import rules. Complete validation runs before `create_object`. Apply identity, literal traits, db.skills and db.behaviour_tree in the existing transaction. Failure in any assignment or event scheduling leaves no partial object/configuration. Keep the existing durable construction event, adding kit/profile identifiers to context without new telemetry systems. Test outer rollback as well as local exceptions.

### Minimal existing behavior configuration

Add one reusable profile to monster_behaviour.yaml using first_owned, lowest_hp, prefer_area_when_multiple_enemies false and flee_hp_fraction 0.20. Do not alter tier defaults. Add `can_use_skill` qualification to `_owned_damage_skills`; retain affordable active damage shape and owned order. Basic attack remains innate and is selected after bite eligibility or MP/SP affordability fails. Resolver validation is authoritative after initiative. Existing living/knockout/displacement/lamb-seal narrowing, flee behavior and target tie-breaking remain unchanged.

### Payment, reactions and defeat

Affordability must pass before rolls, so future drain cannot finance a cast. Normal action ordering stages damage, target transfer, capped caster recovery, then MP/SP payment. Use canonical MP writers so actual removal and existing reactions are respected. Starting full at 30, bank_lurker ends at 20 after a 10-MP hit; starting at 20 it recovers to 30 and pays to 20. A 3-MP target credits at most 3 before cap; a zero-MP target still receives damage. A miss pays both costs and transfers nothing; critical damage does not multiply drain. Same-action transfer can occur after damage crosses defeat HP. Ordinary defeat settlement follows resolution. Preserve existing modifier behavior and discard overflow.

### Persistence, ecology and executable evidence

No startup mutation, migration, refill or rescaling of existing individuals. Reload retains depleted current gauges, owned order, identity and behavior. Ordinary world-clock recovery remains unchanged; any live update uses authorized GM rules, never a Django shell.

Update public ecology and author notes in monster_species.py, docs/lore/bestiary.md and docs/lore/monster-creation-guidelines.md. Document monster slice/kit authoring and resource order in existing docs/development/adding-spells.md. Remove crocodile-only deferred-mechanics/zero-pool assertions. Retain close contact, no remote drain, no HP healing and no permanent magic loss. Other species' boundaries and public/private projection discipline are unchanged. Command syntax/availability is unchanged; if implementation does alter it, update both repository command documentation files under the existing rule.

Extend existing test_monster_individual.py, test_monster_behaviour_selection.py and test_monster_behaviour_integration.py and the real combat-session tests. Use synthetic species/abilities for mechanics and a tagged, registered data-contract test for the shipped bite/profile pins and production crocodile smoke. Register any new test module's exact shard ownership in .github/evennia-shards.json and shipped assertions in tools/test_data_freeze.json. Focused tests cannot substitute the real session smoke.

The smoke constructs both variants through construct_species_individual, creates a production resolver-backed combat session, observes victim HP, both MP pools and caster SP for a deterministic hit and miss, then exhausts a bite resource until ordinary attack resolves. Keep the target alive for exhaustion via an authorized synthetic opponent fixture or deterministic miss sequence, without changing shipped crocodile stats; isolate clock recovery when asserting nominal action deltas and also prove ordinary clock recovery remains unchanged. Reload the depleted actor via the production persistence path and assert identity/kit/profile/current gauges. No live generative/image service is used. A synthetic second species demonstrates the identical APIs without new shipped content. Late action and construction failures prove complete rollback and practice-claim release.

## Risks / Trade-offs

Registry/behavior imports could cycle; construction owns cross-registry validation. Ordinary target death and flee can end a smoke before exhaustion; use controlled fixture state while exercising the real provider and resolver. Damage/diversion may reduce available MP before drain; assert actual canonical removal. Grade labels remain approved content without claiming recalibration.

## Migration Plan

No automatic existing-object migration or compatibility surface. New construction adopts approved kits/pools; live individuals stay unchanged until authorized GM action. Apply, verify and archive this change after both standalone prerequisites. Roll back the content/configuration unit without resetting persistent current resources. The approval-status documentation edit was separately committed by the parent and is not modified here.

## Batch dependency and conflict matrix

| Pair | Logical relationship | Physical conflict and sequencing |
|---|---|---|
| shared-skill-identity-eligibility / skill-hit-dependent-effects | Neither depends on the other; each has standalone synthetic acceptance | registry/vocab.py, action validation/resolution seams, shared effect/preview/atomicity fixtures, docs/development/adding-spells.md and .github/evennia-shards.json require serialized integration |
| shared-skill-identity-eligibility / tide-devouring-crocodile-resource-skill | Crocodile depends on completed eligibility | Registry metadata/builders/validation, ownership and passive/catalog tests, adding-spells.md, monster construction's qualification imports and shard/data-contract manifests require prerequisite completion before consumer integration |
| skill-hit-dependent-effects / tide-devouring-crocodile-resource-skill | Crocodile depends on completed hit dependencies | Effect policy/registry metadata, damage-transfer integration and atomicity fixtures, adding-spells.md and shard/data-contract manifests require prerequisite completion before consumer integration |

Safe order is apply, verify and archive eligibility; apply, verify and archive hit dependencies; then apply, verify and archive crocodile integration. The first two are logically interchangeable, but this fixed recommended order avoids concurrent edits. Do not run archive before that change's implementation and evidence are complete. All three proposals remain planning-only now.

## Final planning critique disposition

The single full-set rubber-duck review found two blocking contradictions in retained monster-species main requirements. Both are resolved in the delta. The complete numeric-profile requirement now permits only the explicitly approved crocodile MP/SP exceptions while preserving its other approval and tier-band scenarios. The narrative-behavior deferral scenario now applies only to the five deferred abilities, with a crocodile scenario tying execution to validated authored configuration. The reviewer found no other blockers or nonblocking issues. This disposition records the remedies; it does not claim a second independent review or runtime verification.
