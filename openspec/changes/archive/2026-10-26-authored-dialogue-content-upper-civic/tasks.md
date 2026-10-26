# Tasks

Read design.md and Shared contract v2 first. Use the completed sorted YAML scanner through the unread-notices dependency chain; never edit profiles, region Python modules, shared manifests or a manual content registration list. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own documentation and review and is bounded to 45-120 minutes.

## 1. Mandatory source and inventory review

- [x] 1.1 Read the mandatory world_info file and all specified skills/canonical sources before writing or review; record source-section references, all 12 stable topic IDs and service exclusions in docs/lore/upper-civic-dialogue-review.md. Record the exact profile-key filename mapping and verify every owned host/topic is accounted for and no private source contents are copied.

## 2. Rewrite first owned host

- [x] 2.1 Replace all four topic scenes and opening for altoria_noble_watch in `world/lore/dialogue/content/altoria_noble_watch_captain.yaml`, including full actor utterances, narration and its required domain variants/chain. Record the line-by-line editorial review as the prose lands; verify multiline/ID/office/no-OOC constraints and review every line against sources.

## 3. Rewrite altoria_drill_yard

- [x] 3.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_drill_yard in `world/lore/dialogue/content/altoria_drill_instructor.yaml` without reusing old fixed response prose. Extend the same editorial review record; verify natural register, source-backed elves/religion treatment, attribution and unchanged services.

## 4. Rewrite altoria_academy

- [x] 4.1 Replace all four topic scenes/opening and declared variants/refusals for altoria_academy in `world/lore/dialogue/content/altoria_academy_dean.yaml` without reusing old fixed response prose. Extend the same editorial review record; verify natural register, source-backed elves/religion treatment, attribution and unchanged services.

## 5. Offline real-host acceptance

- [x] 5.1 Run the existing logic tests that cover the shipped snapshot plus one real-host text consumer
smoke with replay and saved-reading assertions; add no test module and no manifest entry; update
any affected documentation examples. Verify the discovered immutable snapshot resolves every owned profile-key file, stable topic ID and rewritten greeting without manual registration, and no temporary prose conversion remains for owned rows; do not defer any owned prose or acceptance to a final batch change.

