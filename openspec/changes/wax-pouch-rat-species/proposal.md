# Proposal

## Why

Deliver 蠟囊鼠 (`wax_pouch_rat`) and its ordinary default variant 藏穀型 (`wax_cache_forager`) from `docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §3, §4.3, §5, §6 and §8: a complete low-tier F profile, the self agility improvement `wax_pouch_slip` (滑蠟翻身), a validated AI binding, and its keyed bestiary section and ledger entry. Its kit has the same composition shape as the slime's self-only support kit, so it reuses that representative evidence instead of adding a battery.

## What Changes

- Registry rows: `MonsterSpecies("wax_pouch_rat", …)` with the approved public passages of design §4.3 verbatim, habitat tags `eastern_plains` and `western_hills_valleys`, author-private origin boundary/rationale; `MonsterVariant("wax_cache_forager", …)` low tier, ordinary, `profile_required=True`, complete literal low-band profile, grade F, kit `("wax_pouch_slip",)`, archetype `instinctive`.
- Skill `wax_pouch_slip`: self-only, no damage, positive SP cost, mounts a timed positive agility modifier on the caster under the shared lifetime/refresh rules; it changes combat modifiers, never location. Status display, narration and one modifier rule.
- AI binding: utility override and authored intelligence for `wax_cache_forager`; activation evidence re-fingerprinted.
- Bestiary section, overview row and ledger entry; review section in `docs/development/monster-content-expansion.md`.
- One `test_rule_<id>` correspondence case and a roster-free group-member class in the slime representative module that exercises a real rat cast. No new test module: the variant joins the self-support composition group whose representative (`mudbank_dweller`) remains the sorted minimum.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. Existing contracts in `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` cover this content; no new behaviour is specified.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_martial.py`, `world/rules/rulebook/{buffs,combat_modifiers,status_display,monster_behaviour}.yaml`, `docs/development/monster-ai-activation-evidence/{activation.json,README.md}`, `docs/development/monster-ai-manual-evidence/{selector-check.json,selector-check.md,README.md}`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `world/rules/tests/test_combat_modifiers.py`, regenerated `content/map-reference-context.json`.

No placement (owned by `weak-species-habitats` and `abandoned-transfer-station-encounter`). Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (prose) and `docs/development/monster-content-expansion.md` (profile role relations, intelligence rationale).

## Batch:

depends-on: mudfilm-slime-species

Batch 3 (alone).

Code conflicts: the same registry, skill, rulebook, narration, bestiary, ledger, review and activation-evidence files as `mudfilm-slime-species`, `sticky-palm-goblin-species`, `reservoir-warden-variant` and `ember-bristle-boar-species`; strict serial chain. `content/map-reference-context.json` is regenerated after rebase.
