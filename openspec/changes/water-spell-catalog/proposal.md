## Why

The water skill tree (`docs/lore/skill-trees/water.md`, 14 nodes) is the node-data authority, but the registry still ships the dev-era 2026-08-12 ten-row water set (`water_bolt … sea_of_life`), half of it HP heals that contradict the tree's own seam note ("水屬性從來不治傷" — the healing-funnel-to-light convergence). Every behavior primitive this wave needed — the canonical MP writer, the transfer family, the divert shield, the marker rows — is now specified by the sibling changes; this change is the final **data-only** integration: it replaces the old rows wholesale, authors the 14-node tree as registry data over that vocabulary, and retires the duplicated water catalog-contract tests exactly as the archived light wave did. Per the ratified NON-GOAL this change adds **zero water catalog/data-contract tests**: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the water.md table. Verification is synthetic program-behavior tests only.

## What Changes

- **Batch declaration.** This change lands LAST; every prior water change is listed in `## Batch` below with machine-readable `depends-on:` lines and the code-conflict notes the supervisor queues from.
- Replace the ten dev-era water registry rows with the 14-node tree verbatim from the node table (keys, labels, targets, MP costs, prerequisites via `SkillPrerequisite(node, N)`, coefficients, 處決級/毀滅級 tiers, caps via the existing reverse-edge derivation — no stored cap field). Old keys are deleted without alias (zero users): five heal keys (`minor_heal`, `healing_spring`, `wellspring_of_life`, `tidal_revival`, `sea_of_life`) disappear entirely (healing is light's verb); `water_bolt`, `water_shield`, `abyssal_whirlpool`, `tsunami`, `abyssal_tide` are re-homed under the tree's node data.
- Re-home or remove the dev-era water buff keys: the inert `water_shield` bounds row was already deleted by `water-damage-redirect-shield` (`water_film` replaced it); `water_bind` is re-homed as 深海漩渦's bind row (real `actions_per_turn: 0` binding shipped by `water-mp-depletion-reaction`'s combat-modifier work).
- Author every node's effect composition over the wave's vocabulary: `damage:water:magic` coefficients, `buff_apply:` the 潮退 tier rows / `water_film` / bind / `mp_regen_lock` / `mana_reflux`, `mana_transfer:` drains/restores with `ManaTransferPolicy` shares and per-stack bonuses, `audience_condition` for 溺潮's max-zero damage rider, and 深海神格's take-and-give composite (enemy-audience drain-all + ally-audience restore, both from existing primitives).
- Retire the water catalog echo tests in-file: `WATER_SPELL_CATALOG` and `WaterSpellCatalogTests` in `world/skills/tests/test_spell_catalogs.py`, the water rows in `test_cost_tiers.py`'s tier table; the canonical ID `skill-registry::skill-registry-contains-the-full-水-element-spell-set` retires with its requirement (per-file freeze-list entries adjusted only as `tools.test_data_lint check` output decides).
- Docs sync under the narrative-vs-node-data authority rule: `water.md` stays the authority and is untouched; `magic-system.md` §3's water row gets checked for contradiction only (expected: none — it states the mana-tide identity this tree implements); `tests/test_command_docs.py` untouched (no command-surface change — water nodes cast through the existing generic cast command). New behavior test modules register in `.github/evennia-shards.json` in this change (it owns the last shard edit of the wave).

This design.md additionally carries the wave-wide **interface-ownership matrix, batch order and shared verification contract** (light's pattern) for the whole water wave.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-registry`: the duplicated ten-row 水-element data-contract requirement is REMOVED and replaced by one behavioral requirement — water spell progression composes executable mana-tide behavior (drain/restore/DoT/shield/suffocation/lock/redirect/composite) through the shared mechanics, with the old set deleted without alias.

## Impact

`world/skills/registry.py` (water set block); `world/rules/rulebook/buffs.yaml` (`water_bind` re-home confirmation); `world/skills/tests/test_spell_catalogs.py`, `world/rules/tests/test_cost_tiers.py` (echo-test retirement); new synthetic behavior module(s) → `.github/evennia-shards.json`; `tools/traceability` ledger hygiene at the separately authorized main-sync. `openspec list --json` returned an empty change set at authoring time — no serialization gate against active changes (unlike Phase B); the water wave's internal ordering is declared below. One engineer-day.

## Batch

- depends-on: water-mp-depletion-reaction
  (code conflicts: `world/rules/rulebook/buffs.yaml`, `.github/evennia-shards.json`, `world/rules/action.py` step-6)
- depends-on: water-mana-transfer
  (code conflicts: `world/skills/effects.py` policy block already frozen by that change — this change only authors data; `.github/evennia-shards.json`)
- depends-on: water-damage-redirect-shield
  (code conflicts: `world/rules/rulebook/buffs.yaml` water rows — this change rebinds `buff_apply:water_shield`→`water_film` in the registry only; `.github/evennia-shards.json`)

Planning artifacts only this turn; no apply/archive/sync/merge.
