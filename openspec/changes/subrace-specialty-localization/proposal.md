# Proposal: subrace-specialty-localization

## Why

Defect 4 of the approved design (`docs/superpowers/specs/2026-09-12-human-subrace-lineage-rework-design.md`
§1): the `specialty` field is rendered straight to players — `commands/character_creation.py:191`
prints `{display_name_zh}（{common_name_zh}）——{specialty}` and
`web/static/webclient/js/elosern/creation_menu.js:247` uses `entry.specialty` as the menu
description — so a character-building player reads
`底層平民（農民與勞工）——The lower class: farmers and laborers.`, English prose inline with
Chinese names. After Change 1 the human five are zh-TW; the ten elf and beastfolk entries still
leak. No spec currently constrains the language of `specialty`, while
`openspec/specs/webclient-character-creation-ui/spec.md:52` already requires the `sex` labels to
be "server-owned Traditional Chinese text derived server-side" — the precedent this change
extends to `specialty`.

## What Changes

- Rewrite the ten remaining `Subrace.specialty` values (three elf branches + seven beastfolk
  subspecies) in Traditional Chinese, faithful to each entry's existing `common_name_zh` and to
  the lore in `tmp/story_settings/world_info.md` (「亞種數值傾向」 block for beastfolk, 三分支
  block for elves) and `docs/lore/overview.md:43,51-53`. Beastfolk prose names a **physique**
  plus its habit and its tradeoff (the naming axis §1 finding 2 credits beastfolk for —
  狼人 balanced / 熊人 strength / 兔人 speed); elf prose names the clan's home, affinity and art.
  No occupational-determinism phrasing (「擅長潛行偵查」 as aptitude, never 「是刺客」).
- **ADDED** requirement in `lore-registries`: every `Subrace.specialty` SHALL be Traditional
  Chinese, server-owned, player-facing prose — covering all 15 entries (5 human + 3 elf +
  7 beastfolk), with no English sentences, derived server-side exactly like the sex labels.
  This requirement locks all 15 entries, including Change 1's five.
- **MODIFIED** requirement `Subrace registry covers elf branches, beastfolk subspecies, and
  human bloodline subraces with stat modifiers`: carry over Change 1's version of the
  requirement and its scenarios unchanged, and add a scenario pinning the ten elf/beastfolk
  `specialty` strings verbatim, mirroring how Change 1 pins the human five.
- No renderer change: `commands/character_creation.py` and `creation_menu.js` already print the
  field verbatim and stay untouched.
- No key renames, no save-data compatibility layer, no migration (design §7).

## Out of scope

- The five human `specialty` strings — already rewritten to zh-TW by Change 1
  (`human-subrace-lineage-rework`); this change MUST NOT touch that prose.
- Any UI/renderer/protocol change (both surfaces already just print the field; the
  `MAX_SPECIALTY_CODE_POINTS` bound and the JS `description` fallback stay as-is).
- Renaming subrace keys, fields, or any `### Requirement:` heading (every
  `@covers_requirement` slug stays valid).
- Translating anything other than `specialty` — `RaceProfile.description` and `StaticTier`
  prose are separate fields not rendered beside a Chinese subrace label in the §1 defect.
- Adding prune capability to `world/lore/sync.py::sync_all`; replacing `Subrace` with an
  `Origin` concept (design §6, rejected — do not reopen).

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `lore-registries`: a new requirement makes `Subrace.specialty` a Traditional-Chinese
  server-owned player-facing contract for all 15 subraces, and the Subrace-registry requirement
  gains the ten pinned elf/beastfolk `specialty` strings. No requirement heading is renamed.

## Impact

- **Code**: `world/lore/races.py` (ten `Subrace.specialty` string values only — keys, names,
  modifiers, anchors untouched).
- **Tests**: `world/lore/tests/test_races.py` gains one behavior test covering the new
  requirement. No test modules added or renamed, so `.github/evennia-shards.json` needs no
  update (`world.lore` is already registered in shard 4, `quests-skills-art-ai-lore`).
- **Specs/docs**: `openspec/specs/lore-registries/spec.md` at archive time. No lore-doc edit is
  required — the prose translates existing documented lore verbatim.
- **UI/protocol**: none. `web/webclient/presentation/creation.py` and `protocol.js` keep
  validating `specialty` as a bounded string.

## Batch:

depends-on: `human-subrace-lineage-rework` — Change 2's new requirement covers Change 1's output
(the five zh-TW human strings), so Change 1 lands first; Change 2 does not rewrite the human
five, whose strings come from Change 1's delta verbatim.
conflicts-with: `human-subrace-lineage-rework` — same `specialty` fields in
`world/lore/races.py` (disjoint entries: human five vs elf+beastfolk ten) and the same
`openspec/specs/lore-registries/spec.md` / same `Subrace` registry requirement. Change 1 MUST
sync/archive first; Change 2's MODIFIED delta is authored against Change 1's post-archive text.
conflicts-with: `custom-kit-worn-at-activation` — none. Independent capability
(`player-character-creation`), no shared file; lands after both by batch order only.
