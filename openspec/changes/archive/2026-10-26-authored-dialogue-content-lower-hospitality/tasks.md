# Tasks

Read design.md and Shared contract v2 first. Use the completed sorted YAML scanner through the unread-notices dependency chain; never edit profiles, region Python modules, shared manifests or a manual content registration list. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mandatory source and inventory review

- [x] 1.1 Read the mandatory world_info file and all specified skills/canonical sources before writing or review; record source-section references, all 12 stable topic IDs and service exclusions in docs/lore/lower-hospitality-dialogue-review.md. Record the exact profile-key filename mapping and verify every owned host/topic is accounted for and no private source contents are copied.

## 2. Rewrite first owned host

- [x] 2.1 Replace all four topic scenes and opening for altoria_eatery in `world/lore/dialogue/content/altoria_eatery_owner.yaml`, including full actor utterances, narration and its required domain variants/chain. Verify multiline/ID/office/no-OOC constraints and review every line against sources (no content test module added as slice ships authored data with no new logic).

## 3. Rewrite altoria_tavern

- [x] 3.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_tavern in `world/lore/dialogue/content/altoria_tavern_keeper.yaml` without reusing old fixed response prose. Maintain editorial record; verify natural register, source-backed elves/religion treatment, attribution, pure-chain continuation, and unchanged services.

## 4. Rewrite altoria_lodging

- [x] 4.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_lodging in `world/lore/dialogue/content/altoria_innkeeper.yaml` without reusing old fixed response prose. Maintain editorial record; verify natural register, source-backed elves/religion treatment, attribution and unchanged services.

## 5. Offline real-host acceptance

- [x] 5.1 Verify that the discovered immutable snapshot resolves every owned profile-key file, stable topic ID, r2 revisions and rewritten greeting without manual registration; verify existing structural and runtime test suites pass; confirm no temporary prose conversion remains for owned rows.

