# Proposal

## Why

Deliver 膠掌小鬼 (`sticky_palm_goblin`) and its ordinary default variant 懸巢型 (`hanging_nest_forager`) from `docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §3, §4.2, §5, §6 and §8: a complete low-tier F profile, the elementless physical grab `sticky_palm_grab` (黏掌抓扯) with a brief agility penalty only on a landed hit, a validated AI binding, and its keyed bestiary section and ledger entry. The kit has the shipped enemy hit-rider composition shape, so it reuses that group's representative evidence.

## What Changes

- Registry rows: `MonsterSpecies("sticky_palm_goblin", …)` with design §4.2 public passages verbatim, habitat tag `western_hills_valleys`, author-private origin boundary/rationale (ordinary monster species; animal signalling and learned object use only); `MonsterVariant("hanging_nest_forager", …)` low tier, ordinary, `profile_required=True`, complete low-band profile, grade F, kit `("sticky_palm_grab",)`, archetype `instinctive` (legacy mode: the kit deals damage, so the legacy body can select it and keeps its flee priority for retreat-oriented foraging).
- Skill `sticky_palm_grab`: single enemy, `damage:none:physical`, then a hit-dependent timed negative agility modifier on the struck enemy; positive SP cost; status display, narration and one modifier rule. Movement and flee stay governed by their ordinary gates.
- Activation evidence re-fingerprinted (the new buff and rule enter the tuning fingerprint); the activated set is unchanged.
- Bestiary section, overview row and ledger entry; review section.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. Existing contracts (`monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities` enemy hit-rider and representative evidence, `monster-behaviour-profile`, `monster-ai-rollout`) cover this content.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_martial.py`, `world/rules/rulebook/{buffs,combat_modifiers,status_display}.yaml`, `docs/development/monster-ai-activation-evidence/{activation.json,README.md}`, `docs/development/monster-ai-manual-evidence/{selector-check.json,selector-check.md,README.md}`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `world/rules/tests/test_combat_modifiers.py`, regenerated `content/map-reference-context.json`. `monster_behaviour.yaml` is unchanged.

No placement. The registry and depiction stay distinct from beastfolk; language, writing, trade and settlements are outside the actor model (design §4.2). Human-reviewed documents: `docs/development/bestiary-editorial-review.md` and `docs/development/monster-content-expansion.md`.

## Batch:

depends-on: wax-pouch-rat-species

Batch 4 (alone).

Code conflicts: same serial content chain files as the slime, rat, crocodile-variant and boar changes; `content/map-reference-context.json` regenerated after rebase.
