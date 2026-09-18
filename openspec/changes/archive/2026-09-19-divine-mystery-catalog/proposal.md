## Why

`SKILL_REGISTRY` still ships the dev-era divine-mystery block: four deliberately inert placeholders
(時間加速, 空間扭曲, 物質轉換, 生命延續) with no prerequisites, no depth and no mechanical effect, plus
two orphan single nodes (`status_disguise`, `dominion_art`). The redesigned lore
(`docs/lore/skill-trees/divine-mystery.md`) replaces that shape entirely: three shallow chains over the
one layer no element verb touches — 代行 — converging on a three-parent capstone, with the two orphans
promoted to chain roots. Every engine primitive those nodes need lands in the four preceding changes;
this change is the data that consumes them, and the last one in the wave.

## What Changes

- Replace the dev-era divine-mystery registry block with the authored twelve-node tree: the 統御 chain
  (`dominion_art` root, `dominion_recall` leaf, `shared_dominion`, `sovereign_investiture`), the 傳承
  chain (`mentors_covenant`, `chorus_of_ages`, `undying_tutelage`), the 帷幕 chain (`status_disguise`
  root, `bestowed_veil` leaf, `unveiling_eye`, `true_name_sight`) and the three-parent capstone
  `crown_apotheosis`.
- Retire the four placeholder skills wholesale, with no aliases. No preset, import record or lore
  registry claims them.
- Keep `status_disguise` and `dominion_art` as **roots** with no prerequisites, so the three presets
  that already own them stay valid with no seeding.
- Author every node at zero cost, `requires_divine_arts=True`, `usable_out_of_combat=True`, with its
  scale in `EffectPolicy.coefficient` and its party nodes at `TargetSpec.AREA` +
  `EffectAudience.ALLIES`. No node declares a `damage:` or `heal:` effect — the family takes no element
  verb and claims no 離經額度.
- Retire `DivineMysteryRegistryTests`, the dev-era data-echo suite that enumerates the placeholder rows,
  and replace its coverage with behavioral contracts over synthetic compositions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `divine-mystery`: REMOVED the "unmechanized mysteries are explicitly declared" requirement (its four
  declared entries no longer exist) and ADDED two replacements — the family-wide verb boundary that any
  present and future divine node must satisfy, and a behavioral progression contract covering the
  conferral ladder, the ally audience and the multi-parent convergence.

## Impact

`world/skills/registry.py` (the divine-mystery block swap; the 情慾秘術 divine line and
`divine_sexual_arts` are untouched); `world/skills/tests/test_skill_registry.py` (retire
`DivineMysteryRegistryTests` and the placeholder key lists); `world/rules/tests/test_divine_mystery_gate.py`
(its category-derived fixtures now resolve to the new nodes); a new behavior test module plus
`.github/evennia-shards.json`. `docs/lore/skill-trees/divine-mystery.md` §7 is updated to record that the
engine work has landed. `tools/test_data_freeze.json` is touched only if retiring the echo suite leaves
a stale entry.

## Batch

- depends-on: divine-mystery-digestion-cadence
- depends-on: conferral-grant-store
- depends-on: conferral-revocation
- depends-on: divine-veil-cast-path
- depends-on: divine-veil-reveal
  (This change authors data only. Every effect prefix, scale source, audience and cadence it declares
  is shipped by those five changes; a primitive found missing at implementation time is a defect in its
  owning change, fixed there, never bolted onto the catalog. It is the sole author of the
  divine-mystery registry block, so it conflicts with nothing else in the wave once they have merged.)
