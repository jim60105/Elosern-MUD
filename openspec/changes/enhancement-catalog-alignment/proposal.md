## Why

Two pieces of the `ENHANCEMENT` catalog ship as data that does nothing, and the lore pages now say so explicitly.

**`growth_rate` has no consumer.** `reincarnation_boon_elosia` declares `growth_rate:practice:100` and `parse_effect` turns it into a `GrowthRateEffect` — but nothing in `world/rules/` ever reads it. `_practice_growth_factors()` multiplies race learning × element affinity × `growth_rate_multiplier(entity)`, and that last factor reads only the `conferred_growth_rate` *buff* granted by 統御術. A character who directly owns the boon gets no acceleration at all. The stated ×100 is also not a balanced value: at `skill_proficiency_xp_per_level: 50` and `skill_practice_xp_per_use: 1.0`, one use would award two whole proficiency levels and five uses would cap a canopy node — and it stacks multiplicatively with the elf ×10.0 learning multiplier for a net ×1000. `docs/lore/skill-trees/innate-gift.md` retires that number and replaces it with a **scoped ×5**, on the reasoning that elves are breadth (×10 everywhere) and reincarnators are depth (×5 in one named tree).

**Two PASSIVE skills carry a cost nobody charges.** `flight` declares `cost={"mp": 22}` and `flash_step` declares `cost={"sp": 12}`, both left over from when they were `ACTIVE` with no working cast path. `skill-registry` already reclassified them to `PASSIVE`, and a PASSIVE skill has no cast action to deduct anything, so the two dicts are inert. The character presenter only enriches ACTIVE rows with cost, so the numbers are not even displayed — they are pure drift waiting to mislead a future reader.

## What Changes

- **`growth_rate` gains a required lineage scope.** The grammar becomes `growth_rate:<stat>:<multiplier>:<scope>`, where `<scope>` is a key of `ELEMENT_REGISTRY`. `GrowthRateEffect` gains a `scope` field. **BREAKING**: the three-segment form `growth_rate:practice:100` no longer parses and fails registry load, which is what forces the shipped row to be re-authored rather than silently keeping the old meaning.
- **`growth_rate` gains its consumer.** `_practice_growth_factors()` gains a fourth factor: the product of the multipliers of every `GrowthRateEffect` on a skill the entity *owns* whose `scope` matches the element of the skill being practised. A non-elemental skill, or an elemental skill of another element, takes `1.0`. This composite is shared by both practice entry points, so the per-use grant and the booked-hourly settlement cannot diverge.
- **`reincarnation_boon_elosia` is re-authored** to `growth_rate:practice:5:wind` — ×5, scoped to the wind tree, matching the rebalanced lore. Wind is 伊洛希雅's authored identity element (her kit leads with `wind_mastery` and she carries `flight`).
- **`flight` and `flash_step` drop their inert `cost` dicts**, joining every other PASSIVE in the branch at an empty cost.

**Non-goals.** No change to `conferred_growth_rate` (the 統御術 buff path) — it keeps its own unscoped semantics and its existing consumer. No new scope vocabulary beyond element keys: no shipped boon needs a martial or divine scope, and inventing one now would be unused generality. No change to the other two reincarnation boons.

## Capabilities

### Modified Capabilities
- `skill-effect-model`: the `growth_rate` prefix's grammar changes from `growth_rate:<stat>:<multiplier>` to `growth_rate:<stat>:<multiplier>:<scope>`, with the scope validated against `ELEMENT_REGISTRY` at parse and the three-segment form failing closed.
- `skill-lineage`: the practice-XP accrual formula gains an owned-skill growth factor beside the existing conferred-buff factor.
- `skill-registry`: `reincarnation_boon_elosia`'s effect string moves from `growth_rate:practice:100` to `growth_rate:practice:5:wind`; `flight` and `flash_step` are pinned to an empty `cost`.

## Impact

- **Modified**: `world/skills/effects.py` (`GrowthRateEffect` gains `scope`; the `growth_rate` parse branch validates four segments), `world/rules/progression.py` (`_practice_growth_factors()` gains the owned-skill factor), `world/skills/registry.py` (三 rows: the 伊洛希雅 boon's effect string, `flight` and `flash_step` cost removal).
- **Test updates**: `world/rules/tests/test_progression.py` (the new growth factor; also touched by `cross-lineage-unlock`, different test classes), `world/skills/tests/test_effects.py` (the `growth_rate` parse assertion), `world/skills/tests/test_skill_registry.py` (the boon effects assertion and the `flight` cost assertion inside `test_rehomed_acquired_passives_keep_their_mechanics`).
- **Untouched**: `world/rules/buffs.py` — `growth_rate_multiplier()`, `grant_conferred_growth_rate()` and the `conferred_growth_rate` buff definition keep their current unscoped behavior; this change adds a second, independent factor beside that one.

**No data-contract test is added by this change.** The new behavior is proved with synthetic skills carrying synthetic scoped `growth_rate` effects; the existing shipped-content assertions that this change invalidates are updated in place, not multiplied.

**Code conflict**: `world/rules/progression.py` is also edited by `cross-lineage-unlock`, which adds an evaluation call inside `grant_skill_practice_xp()`. This change edits `_practice_growth_factors()` — a different function in the same file. Whichever merges second rebases; there is no requirement overlap.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
