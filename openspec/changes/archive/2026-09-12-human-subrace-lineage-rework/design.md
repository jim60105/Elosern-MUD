# Design: human-subrace-lineage-rework

## Context

`SUBRACE_REGISTRY` models the five human groups as `Subrace` entries structurally identical
to the elf branches and beastfolk subspecies; the current entries, defects, and the approved
naming/stat/specialty/kit tables are in the design document
`docs/superpowers/specs/2026-09-12-human-subrace-lineage-rework-design.md` (§1–§3), which this
change transcribes — every decision below was settled with the project owner and is not
re-openable here. See `proposal.md` for motivation and `specs/lore-registries/spec.md` for the
resulting contract.

Constraints: no save-data compatibility layer (no characters exist; the DB is rebuilt); every
`### Requirement:` heading name stays stable so `@covers_requirement` slugs remain valid;
deterministic single-writer core and registry source-of-truth invariants hold; player-facing
prose is zh-TW, code comments and commits English.

## Goals / Non-Goals

**Goals:**
- Re-anchor the three non-noble human subraces from the wealth ladder onto a geographic
  lineage axis; rename keys, set zh-TW names/specialty, re-justify (unchanged) stat values,
  equalize the three commoner kits.
- Make the human stat values lore-documented: a human 〈數值傾向〉 block in
  `tmp/story_settings/world_info.md` mirroring the beastfolk block's format.

**Non-Goals:**
- Localizing the ten elf/beastfolk `specialty` values or adding a registry-wide
  specialty-language requirement — successor change `subrace-specialty-localization`.
- Wearing kits at activation — successor change `custom-kit-worn-at-activation`.
- Adding pruning to `world/lore/sync.py::sync_all` (orphan `lore:subraces:*` Scripts are
  removed by the DB rebuild, not by code).
- Renaming any `### Requirement:` heading or any `@covers_requirement`-decorated test module.

## Decisions

**D1 — Geographic lineage replaces the wealth ladder.** `human_wealthy`→`human_coastal`,
`human_commoner`→`human_plains`, `human_laborer`→`human_highland`. coastal/plains/highland
map word-for-word onto 濱海/平原/山地 and onto the economy already documented in
`docs/lore/overview.md:77` (empire agriculture = plains, kingdom crafts/ore = hills,
port-city maritime trade = coast). Alternative considered: substituting gentler occupation
labels — rejected because the naming *axis* is wrong (occupational determinism against
fixed-at-birth stats), not the words.

**D2 — Synonymy rule.** The English key, `display_name_zh`, and `common_name_zh` MUST all be
synonymous: key = display = common minus the 血脈 suffix. This necessarily compresses
`common_name_zh` into a near-duplicate of `display_name_zh`; elves can afford an informative
pairing (斐歐恩族 / 森林精靈) because a clan name and an outsiders' name are two different
words, humans have no such pair. A region name in `common_name_zh` (e.g. 西部丘陵與谷地)
would break synonymy — a place is not a group of people. The owner chose to keep the rule and
accept the repetition.

**D3 — 王族/貴族 stay title-based.** They are hereditary offices describing who governs,
not value judgements about persons, so they escape the occupational/classist defect; their
keys are unchanged.

**D4 — 農民 becomes an occupation inside 平原民.** Farming is practised within the largest
human group, which is also the `StatModifiers()` zero baseline — so the demographics
(agriculture is the empire's dominant industry, `overview.md:77`) and the mechanics now agree
instead of contradicting: farmers are neither a one-fifth minority nor the smallest-kit group.

**D5 — Stat values unchanged, rationale rewritten.** All five zero-sum modifier sets and the
王族 MP override (120–220) keep their exact values; only their documentation source changes
(the new human 〈數值傾向〉 block), because the old values had no lore justification to remove.

**D6 — Kits: equality among commoners only.** The three commoner lineages get identical
COMMON-rarity triads differentiated only by the third item, each choice quoting the item
registry's own `summary_zh` (鐵短刀 「王國鍛坊量產的輕便副手短刀」 → dockhands; 狩獵擲斧
「獵手常用的短柄擲斧」 → hill woodland; 銀髮簪 「市井常見的細銀髮簪」 → everyday, never a
luxury marker). 木製棍棒 disappears from every kit. Rejected: `great_axe` (UNCOMMON weapon
「熊人戰士慣用」, incongruous for a civilian lineage at +10% atk_phys), `storage_pouch`
(RARE, 帝國壟斷的空間魔法小袋) and `gliding_cloak` (EPIC) — far above starting tier.

**D7 — No compatibility layer.** Clean breaking rename (precedent: `1fa6ea5
feat(traits)!: retype magic_level counter as magic_power static trait`). No alias table, no
migration; DB rebuild retires the three orphan `lore:subraces:*` Scripts.

**D8 — Rejected alternative (do not reopen, design doc §6).** Replacing `Subrace` with an
`Origin`/`Lineage` concept was rejected as disproportionate: `Subrace` is load-bearing across
21 modules and `character-creation-ux` spec:37 forbids ever offering an empty subrace choice.

## Risks / Trade-offs

- [Rename misses a call site] → The tasks.md grep sweep (`human_wealthy`, `human_laborer`,
  底層平民, 富裕平民, 農民與勞工, 中小貴族, 皇族與大貴族, 普通平民) must reach zero outside
  `.worktrees/` and `openspec/changes/archive/`; registry-key tests fail closed otherwise.
- [`human_commoner` looks like an unfinished rename] → Deliberate: the `StaticTier` with that
  key (the 1–5 physical band 「平民與非戰鬥者」) is an unrelated concept and MUST NOT be
  touched — `world/lore/races.py:137-138`, `world/lore/npc_tiers.py:41,43,45,46,48`
  (`static_tier_key`), `world/lore/tests/test_races.py:118`,
  `world/rules/tests/test_profession_config.py:283,289` (`default_tier`),
  `openspec/specs/entity-trait-scales/spec.md:142-143`. `web/static/webclient/js/tests/protocol.test.js:3132`
  also stays: a deliberate synthetic fixture with invented names (竈生民), decoupled from
  shipped data by design. Side effect of the rename: `human_commoner` currently names two
  different concepts in two registries; afterwards it means only the static tier.
- [Stale `lore:subraces:*` Scripts in a carried-over DB] → Accepted: the DB is rebuilt;
  `sync_all` pruning is a real gap but explicitly out of scope.

## Migration Plan

No runtime migration. Implementation order per tasks.md: code (`races.py`, `starting_kits.py`,
`player_presets.py`) → tests → fixtures → main-spec/docs/`world_info.md` → verification
commands + grep sweep. Rollback = revert the commit (nothing persists across it).
