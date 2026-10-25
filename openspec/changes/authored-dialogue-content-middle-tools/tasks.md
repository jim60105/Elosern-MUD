# Tasks

Read design.md and Shared contract v2 first. Use the completed sorted YAML scanner through the unread-notices dependency chain; never edit profiles, region Python modules, shared manifests or a manual content registration list. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mandatory source and inventory review

- [x] 1.1 Read the mandatory world_info file and all specified skills/canonical sources before writing or review; record source-section references, all 12 stable topic IDs and service exclusions in docs/lore/middle-tools-dialogue-review.md. Record the exact profile-key filename mapping and verify every owned host/topic is accounted for and no private source contents are copied.

## 2. Rewrite first owned host

- [x] 2.1 Replace all four topic scenes and opening for altoria_general_store in `world/lore/dialogue/content/altoria_merchant.yaml`, including full actor utterances, narration and its required domain variants/chain. Verify multiline/ID/office/no-OOC constraints and review every line against sources; per project policy tests cover logic only and content testing is omitted.

## 3. Rewrite altoria_forge

- [x] 3.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_forge in `world/lore/dialogue/content/altoria_blacksmith.yaml` without reusing old fixed response prose. Include the SkillOwned variant at priority 10. Verify natural register, source-backed elves/religion treatment, attribution and unchanged services.

## 4. Rewrite altoria_tailor

- [x] 4.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_tailor in `world/lore/dialogue/content/altoria_tailor.yaml` without reusing old fixed response prose. Include the SocialIdentityIs variant at priority 10. Verify natural register, source-backed elves/religion treatment, attribution and unchanged services.

## 5. Offline real-host acceptance

- [x] 5.1 Verify that the discovered immutable snapshot resolves every owned profile-key file, stable topic ID and rewritten greeting without manual registration. Run existing logic test suites (world.lore.tests.test_dialogue_assembly, world.rules.tests.test_dialogue_sources, world.rules.tests.test_authored_dialogue_runtime) and contract_gate; update editorial review documentation.

