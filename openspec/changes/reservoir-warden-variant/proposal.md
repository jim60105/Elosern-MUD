# Proposal

## Why

Deliver the high-tier stronger crocodile variant 蓄潮型 (`reservoir_warden`) of the existing 吞潮鱷 (`tide_devouring_crocodile`) from `docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §3, §4.4, §5, §6 and §8: a complete standalone high-tier A profile, the existing contact drain `tide_devouring_bite` plus the new MP-funded self guard `reservoir_guard` (蓄潮護膜), a validated AI binding, the crocodile's affirmative current-section rewrite and its updated ledger entry. The kit forms a new composition shape (drain plus self support), so it carries its own representative smoke.

## What Changes

- Variant row `reservoir_warden`: species `tide_devouring_crocodile`, label 蓄潮型, the approved public variant description (design §4.4) as `description_zh`, tier `high`, `ordinary_variant=False`, `profile_required=True`, complete literal high-band profile with `magic_power=0`, grade A, kit `("tide_devouring_bite", "reservoir_guard")`, archetype `ambush_predator`. The crocodile's default `bank_lurker`, `bay_warden` and every other row are unchanged.
- Skill `reservoir_guard`: self-only water-element support, no damage, positive MP cost paid from the caster's current pool, mounting a timed defense improvement on the caster under the shared lifetime/refresh rules. `tide_devouring_bite` is reused unchanged.
- AI binding: utility override and authored intelligence for `reservoir_warden`; activation evidence re-fingerprinted.
- Crocodile public prose: the species' published ecology field and its current bestiary section rewritten into affirmative sentences with unchanged meaning; the variant's appearance and ecology passages and the local name 「閉灣者」 added to the section; ledger entry updated.
- New representative smoke for the drain-plus-self-support shape.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. `monster-resource-abilities` already specifies hit-qualified actual-loss transfer, hit-independent self effects, payment/rollback and representative evidence per shape; `monster-species-registry` already specifies standalone stronger variants and tier bands; `monster-behaviour-profile`/`monster-ai-rollout` cover binding and evidence.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_water.py`, `world/rules/rulebook/{buffs,combat_modifiers,status_display,monster_behaviour}.yaml`, activation and selector evidence files, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `world/rules/tests/test_combat_modifiers.py`, new `world/rules/tests/test_reservoir_warden_resource_skill.py`, `.github/evennia-shards.json`, `tools/test_data_freeze.json`, regenerated `content/map-reference-context.json`.

No placement: the variant enters no ecology pool; its boss site is `high-tier-boss-sites`. Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative rewrite fidelity to the approved crocodile meaning) and `docs/development/monster-content-expansion.md` (A-grade role relations, intelligence rationale, flee trade-off).

## Batch:

depends-on: sticky-palm-goblin-species
depends-on: owned-kit-decision-coverage

Batch 5, parallel with `weak-species-habitats` (disjoint files: this change edits species/skill/rulebook/bestiary files; that one edits placement/activity declarations).

Code conflicts: serial content chain files shared with the slime, rat, goblin and boar changes; `.github/evennia-shards.json` and `tools/test_data_freeze.json` are also edited by `ember-bristle-boar-species`; `content/map-reference-context.json` regenerated after rebase.
