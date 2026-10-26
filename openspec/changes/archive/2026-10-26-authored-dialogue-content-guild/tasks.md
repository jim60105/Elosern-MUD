# Tasks

Read design.md and Shared contract v2 first. Use the completed sorted YAML scanner through the unread-notices dependency chain; never edit profiles, region Python modules, shared manifests or a manual content registration list. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mandatory source and inventory review

- [x] 1.1 Read the mandatory world_info file and all specified skills/canonical sources before writing or review; record source-section references, all 4 stable topic IDs and service exclusions in docs/lore/guild-dialogue-review.md. Record the exact profile-key filename mapping and verify every owned host/topic is accounted for and no private source contents are copied.

## 2. Rewrite first owned host

- [x] 2.1 Replace all four topic scenes and opening for guild_staff in `world/lore/dialogue/content/altoria_guild_master.yaml`, including full actor utterances, narration and its required domain variants/chain. Verify multiline/ID/office/no-OOC constraints and review every line against sources; ships authored data with no new test because there is no new logic.

## 3. Offline real-host acceptance

- [x] 3.1 Verify existing logic tests and the discovered immutable snapshot resolve the owned profile-key file, stable topic IDs and rewritten greeting without manual registration, and no temporary prose conversion remains for owned rows; do not defer any owned prose or acceptance to a final batch change.
