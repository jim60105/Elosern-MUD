# Tasks

Read design.md and Shared contract v2 first. Use the completed sorted YAML scanner through the unread-notices dependency chain; never edit profiles, region Python modules, shared manifests or a manual content registration list. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mandatory source and inventory review

- [x] 1.1 Read the mandatory world_info file and all specified skills/canonical sources before writing or review; record source-section references, all 8 stable topic IDs and service exclusions in docs/lore/lower-civic-dialogue-review.md. Record the exact profile-key filename mapping and verify every owned host/topic is accounted for and no private source contents are copied.

## 2. Rewrite first owned host

- [x] 2.1 Replace all four topic scenes and opening for altoria_bathhouse in `world/lore/dialogue/content/altoria_bathhouse_keeper.yaml`, including full actor utterances, narration and its required domain variants/chain. Per user binding constraint, tests cover logic only (no content testing for authored prose); verify multiline/ID/office/no-OOC constraints and review every line against sources.

## 3. Rewrite altoria_guardhouse

- [x] 3.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_guardhouse in `world/lore/dialogue/content/altoria_guard_captain.yaml` without reusing old fixed response prose. Extend the slice editorial review record; verify natural register, source-backed elves/religion treatment, attribution and unchanged services.

## 4. Offline real-host acceptance

- [x] 4.1 Run the existing logic modules exercising dialogue snapshot loading (`world.lore.tests.test_dialogue_assembly`, `world.rules.tests.test_dialogue_sources`, `world.rules.tests.test_authored_dialogue_runtime`). The slice ships pure authored YAML data and editorial review records with no new test module because there is no new code logic. Verify the discovered immutable snapshot resolves every owned profile-key file, stable topic ID and rewritten greeting without manual registration, and no temporary prose conversion remains for owned rows.
