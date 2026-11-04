# Proposal

## Why

Deliver the high-tier species 焙鬃野豬 (`ember_bristle_boar`) and its ordinary default variant 焙窩型 (`warm_den_boar`) from `docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §3, §4.5, §5, §6 and §8: a complete high-tier B profile, the fire-element physical strikes `ember_tusk_charge` (熱鬃衝撞, one enemy) and `ember_bristle_sweep` (熱鬃橫掃, all eligible enemies, one payment), an AI binding that can select both, and its keyed bestiary section and ledger entry. Two damage-only actives form a new composition shape with its own representative smoke.

## What Changes

- Registry rows: `MonsterSpecies("ember_bristle_boar", …)` with design §4.5 public passages verbatim, habitat tag `western_hills_valleys`, author-private rationale; `MonsterVariant("warm_den_boar", …)` high tier, ordinary, `profile_required=True`, complete high-band profile with `magic_power=0`, grade B, kit `("ember_tusk_charge", "ember_bristle_sweep")`, archetype `pack_hunter`.
- Skills: both `damage:fire:physical` (physical school reads `atk_phys`; the fire element follows the normal elemental rules), each with positive MP and SP costs; the sweep targets `TargetSpec.AREA` with an enemies audience and ordinary per-recipient hit/defense resolution, paid once per cast.
- AI: `pack_hunter` (legacy): highest expected damage, prefers the area strike when more than one enemy stands, retains an inclusive flee threshold so the boar can flee through a legal route. No rulebook edit, no buff, so the AI tuning fingerprint and activation evidence are unchanged.
- Bestiary: new `## 高階魔物` heading with the boar's current section, overview row, ledger entry; review section.
- New representative smoke for the two-strike shape.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. Existing contracts cover physical-school elemental damage, area resolution with independent per-recipient outcomes and single payment, identity eligibility, cost tiers, legacy area preference and representative evidence.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_fire.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, new `world/rules/tests/test_ember_bristle_boar_resource_skill.py`, `.github/evennia-shards.json`, `tools/test_data_freeze.json`, regenerated `content/map-reference-context.json`.

No placement (owned by `high-tier-boss-sites`). No terrain fire, burning, universal fire immunity or raised `magic_power` (design §5). Human-reviewed documents: `docs/development/bestiary-editorial-review.md` and `docs/development/monster-content-expansion.md` (B-grade role relations, archetype rationale).

## Batch:

depends-on: reservoir-warden-variant

Batch 6, parallel with `abandoned-transfer-station-encounter` (disjoint files).

Code conflicts: serial content chain files; `.github/evennia-shards.json` and `tools/test_data_freeze.json` shared with `reservoir-warden-variant`; `content/map-reference-context.json` regenerated after rebase.
