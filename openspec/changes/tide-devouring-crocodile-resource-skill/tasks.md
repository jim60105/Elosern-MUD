# Tasks

## 1. Approved ability and immutable configuration

- [x] 1.1 Add data_monster_abilities.py to the existing registry assembly and declare the exact prerequisite-free tide_devouring_bite eligibility, water physical coefficient/one-strike shape, enemy component audiences, hit-dependent 10-MP fixed drain/share 1.0 and cost 10 MP plus 5 SP; add tagged data-contract definition assertions registered in tools/test_data_freeze.json and document the separate monster slice in docs/development/adding-spells.md, verifying no player catalog/lineage leak, no freeform scale and unchanged apprentice cost classification.
- [x] 1.2 Extend frozen variant kit/profile references and author only bank_lurker (140/30/40/22/12/14/0, D) and bay_warden (210/50/60/28/12/15/0, C) with bite before innate actions; extend existing registered species/profile data-contract assertions and docs/lore/monster-creation-guidelines.md, verifying the other ten complete profiles, all grades and five deferred ability boundaries are unchanged and no passive or fabricated prerequisite is added.

## 2. Formal construction and existing policy

- [ ] 2.1 Validate complete kit kinds/references/identity/prerequisite usability/effect availability and behavior profile before creation, and apply identity/literal traits/db.skills/db.behaviour_tree in construct_species_individual's transaction; extend test_monster_individual.py and construction guide, verifying every invalid reference, incompatible identity, unusable prerequisite/effect and assignment failure creates no partial individual/ownership and outer rollback suppresses the existing construction event.
- [ ] 2.2 Preserve monster_individual_constructed as the durable boundary event with kit/profile identifiers added to context; extend its boundary tests and guide, verifying event context agrees with committed configuration and rollback emits no success boundary; run observability lint on the changed boundary as part of final checks.
- [ ] 2.3 Add the reusable first_owned/lowest_hp/no-area/0.20-flee profile without changing tier defaults and filter monster damage candidates through shared use qualification; extend monster behavior selection/integration/flee tests and creation guide, verifying ineligible or MP/SP-unaffordable bite returns an available ordinary attack, real resolution remains authoritative after initiative, and existing displacement/living/knockout/target selection behavior is preserved.

## 3. Resource loop, persistence and published content

- [ ] 3.1 Add synthetic resolver/transfer integration coverage for partial/zero target MP, caster full/partial cap, both exact costs, insufficient MP/SP, miss payment, critical and defeat-crossing hits, existing modifiers/reactions and late-failure rollback; document payment/recovery order in adding-spells.md, verifying bank_lurker 30->20 and 20->30->20 MP examples, no financed unaffordable cast, no HP restoration/magic-power reduction and released practice claims after rollback.
- [ ] 3.2 Add synthetic second-species reuse plus production persistence reload coverage in the existing monster/session suites; document no startup resets or live migration in monster-creation-guidelines.md, verifying identical shared dependency/transfer APIs execute without species branches and reload retains identity, owned order/profile and depleted MP/SP while ordinary clock recovery remains unchanged.
- [ ] 3.3 Update crocodile public ecology and relevant author notes in monster_species.py, docs/lore/bestiary.md and monster-creation-guidelines.md; verify text describes implemented close-contact MP pressure with no remote drain/HP healing/permanent magic loss, removes crocodile-only deferred-mechanics/zero-resource assertions and leaves private projections and the other five species unchanged. Keep both command docs unchanged unless implementation changes their syntax/availability.
- [ ] 3.4 Add a tagged data-contract production smoke in new world.rules.tests.test_crocodile_resource_skill, registered exactly in rules-b (index 2) and tools/test_data_freeze.json; formally construct BOTH variants, exercise real resolver-backed combat sessions with deterministic hit/miss and resource exhaustion followed by resolved basic_attack, record target HP/both MP/caster SP and reload depleted participants, and verify no live generative/image call. Use a controlled valid opponent and isolate clock recovery for per-action deltas without bypassing the production provider/resolver; focused tests do not replace this smoke.

## 4. Integration acceptance

- [ ] 4.1 Run focused ability data-contract, construction, monster policy/flee, transfer/atomicity, combat-session and persistence labels plus the production smoke with approved Evennia settings/environment-file; record actual closed-loop evidence and coverage markers for affected synchronized requirements, without a recalibration claim or broad CI substitution.
- [ ] 4.2 Run uv run --locked python -m tools.contract_gate, observability lint, data lint and openspec validate tide-devouring-crocodile-resource-skill --strict; verify exact new-module shard ownership and shipped-data audit registration, both prerequisites' archived contracts are present, and all specified acceptance cases and documentation updates are complete before review/archive.

## Workflow follow-up

- Apply/verify/archive only after both prerequisites are complete and archived. A prerequisite's completion never means this crocodile feature is delivered. This proposal set performs no implementation/application/archive/sync.
