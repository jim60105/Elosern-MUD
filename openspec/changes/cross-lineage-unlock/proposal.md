## Why

`docs/lore/skill-trees/enhancement.md` documents three `ENHANCEMENT` passives — `blade_art_mastery`, `magic_circle_comprehension`, `precise_mana_control` — as **cross-lineage unlocks**: ownership that falls out of reaching a given depth in *other* lineage trees. No such mechanism exists. The three skills ship in `SKILL_REGISTRY` with live `combat_modifiers` rules behind them, but the only way to obtain any of them today is a character preset or an import, so their documented acquisition path is fiction and a player can never earn one.

The lore also names a second, larger use for the same idea (`docs/lore/skill-trees/cross-lineage-unlock.md` §4): opening a whole new lineage tree once two existing trees reach a depth — "water Lv.3 + wind Lv.3 opens the mist tree". Building a single-purpose "grant this passive" hook now would have to be torn out and rewritten when that lands. Because the engine already separates **ownership** from **usability** (`skill-lineage`: prerequisites gate use, not possession), both needs reduce to one action — *add a set of skill keys to the owned set* — so one general rule table covers both.

## What Changes

- **New rulebook table** `world/rules/rulebook/cross_lineage_unlock.yaml`: a list of rules, each with an `id`, a `requires` array of AND-ed condition clauses, and a `grants` list of skill keys. A clause samples registry nodes by `scope`, groups them by a declared dimension, and demands that `distinct_groups` separate groups each hold at least one node at `min_level` proficiency.
- **New loader/evaluator module** `world/rules/cross_lineage_unlock.py`, with a load-time validator that fails closed on the six constraints the lore page ratifies (unreachable thresholds, PASSIVE-only scopes, grant/condition cycles, unknown keys, empty grants, non-positive counts). A rule that could never fire is a data defect and must break the import, not silently do nothing.
- **Push-based evaluation** hooked into `grant_skill_practice_xp()` in `world/rules/progression.py`, immediately after `award_practice_xp()` — the sole writer of `db.skill_proficiency`, and therefore the only place a rule's condition can newly become true. Granted keys are appended to the entity's stored passive/active lists; newly granted skills reuse the existing `unlocks_out` sink so the player sees a line through the shipped delivery path.
- **Three shipped rules**, exactly as the lore page tabulates them: `blade_art_mastery` (sword line, any node Lv.3), `magic_circle_comprehension` (any one element tree, any node Lv.5), `precise_mana_control` (any two distinct element trees, each with a node at Lv.5).
- **Scope addressing without a registry schema change.** Element trees group by their existing `group` field. The martial "sword line" has no data dimension — every `MARTIAL_ARTS` entry is required by `skill-category-registry` to declare `group is None` — so a clause may instead name an explicit `keys` list. This change does **not** add a `line` field to `SkillDef`, which would reopen that capability's closed group vocabulary for no benefit to the three shipped rules.

**Non-goals.** No new lineage tree is authored — the mist example in the lore page is illustrative and stays unimplemented. No revocation path: grants are monotonic by design. No proficiency is ever granted, only ownership. No read-path derivation: `SkillHandler.owned_keys()` is untouched.

## Capabilities

### New Capabilities
- `cross-lineage-unlock`: A declarative rule table that grants skill ownership when an entity's proficiency across *other* lineage trees reaches declared depths — covering the table's shape and load-time validation, the push-based evaluation point, and the monotonic ownership-only grant semantics. The capability is specified as **mechanics**, proved by synthetic rules over synthetic skills; the three shipped rows are delivered content, pinned only by the requirement that the shipped table must load without violating any validation rule.

### Modified Capabilities
None. `skill-lineage` keeps every requirement it has: prerequisites still gate use, `cap(S)` still derives from consuming edges, and practice still accrues exactly as specified. This change adds a second, independent axis beside that one and writes into the same `db.skills` storage `skill-handler` already reads, so neither capability's stated behavior changes.

## Impact

- **New**: `world/rules/rulebook/cross_lineage_unlock.yaml`, `world/rules/cross_lineage_unlock.py`, `world/rules/tests/test_cross_lineage_unlock.py`.
- **Modified**: `world/rules/progression.py` — `grant_skill_practice_xp()` gains one evaluation call after the award; the booked-hourly settlement path gains the same call so the two practice entry points cannot diverge. `world/rules/tests/test_progression.py` gains the wiring assertions (also touched by `enhancement-catalog-alignment`; different test classes).
- **Read-only dependencies**: `SKILL_REGISTRY` (node sampling, `kind`/`category`/`group`), `proficiency_cap()` (reachability validation), `skill_proficiency_level()` (condition evaluation), `unlock_line()` (notification text).
- **Untouched**: `world/skills/handler.py`, `world/skills/registry.py`, `world/rules/combat_modifiers.yaml`. The three granted skills and their modifier rules already ship; this change only creates a path to owning them.
- `.github/evennia-shards.json` needs no edit — the new test module lives under `world/rules/tests/`, already covered by its shard's package label.

**No data-contract test is added by this change** — no rule-table echo, no key-set census, no threshold echo. Behavior is proved with synthetic rules over synthetic skills per `AGENTS.md`; the only assertion touching shipped content is that the rulebook imports cleanly.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
