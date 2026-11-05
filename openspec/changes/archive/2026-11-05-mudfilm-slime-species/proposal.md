# Proposal

## Why

Deliver 泥膜史萊姆 (`mudfilm_slime`) and its ordinary default variant 濕岸型 (`mudbank_dweller`) from `docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §3, §4.1, §5, §6 and §8: a complete low-tier F profile, the self film guard `mudfilm_guard` (泥膜收束), a validated AI binding, and its keyed bestiary section and editorial ledger entry. It is the first kit whose only active carries no damage effect and costs SP only, so it also carries the first representative smoke for that composition shape and the kit-contract test correction that shape needs.

## What Changes

- Registry rows: `MonsterSpecies("mudfilm_slime", …)` with the approved public description, appearance and ecology (verbatim from design §4.1), habitat tags `eastern_plains` and `western_hills_valleys`, and author-private origin boundary/rationale; `MonsterVariant("mudbank_dweller", …)` low tier, ordinary, `profile_required=True`, complete literal profile inside the low band, grade F, kit `("mudfilm_guard",)`, archetype `instinctive`.
- Skill `mudfilm_guard`: self-only, no damage, positive SP cost, mounts a timed defense improvement on the caster through the existing buff lifetime/refresh rules; status display, narration and one combat-modifier rule.
- AI binding: utility decision override and authored intelligence for `mudbank_dweller` (required by `owned-kit-decision-coverage`), with the activation evidence re-fingerprinted.
- Bestiary: new current section with its `bestiary` index, overview row and header approval note; editorial ledger entry.
- Tests: correct the kit-contract assertion that every active kit skill resolves a magic tier (only elemental MP skills do); add the representative smoke for the new support-only composition shape; add the one-test-per-rule correspondence case.
- Roster-free wording for the species module docstring and authoring comments that currently state "six"/"twelve".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by existing contracts: `monster-species-registry` (complete profiles, bands, ownership, narratives), `monster-individual-construction` (kit validation, literal construction, reload), `monster-resource-abilities` (identity eligibility, cost-tier gate, hit-independent self effects, lifetime/refresh, representative evidence per composition shape, keyed bestiary), `monster-behaviour-profile` (explicit intelligence, mode binding, and the support-kit utility rule added by `owned-kit-decision-coverage`) and `monster-ai-rollout` (expansion evidence, re-fingerprinting). No new behaviour is specified.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_martial.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/rulebook/monster_behaviour.yaml`, `docs/development/monster-ai-activation-evidence/{activation.json,README.md}`, `docs/development/monster-ai-manual-evidence/{selector-check.json,selector-check.md,README.md}`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, new `docs/development/monster-content-expansion.md`, `world/skills/tests/test_skill_registry/test_registry_contract.py`, `world/rules/tests/test_combat_modifiers.py`, new `world/rules/tests/test_mudfilm_slime_resource_skill.py`, `.github/evennia-shards.json`, `tools/test_data_freeze.json`, regenerated `content/map-reference-context.json`.

No placement: the species is not placed anywhere until `weak-species-habitats`; registry completion grants no automatic coverage.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing and ecology/capability consistency of the public prose) and the new `docs/development/monster-content-expansion.md` (profile literals versus the slow defensive role, intelligence rationale). Tests never compare prose, counts or magnitudes.

## Batch:

depends-on: owned-kit-decision-coverage
depends-on: affirmative-monster-prose-guidelines

Batch 2, parallel with `site-member-activity-bindings` (disjoint files).

Code conflicts:
- `wax-pouch-rat-species`, `sticky-palm-goblin-species`, `reservoir-warden-variant` and `ember-bristle-boar-species` append to the same registry, skill, rulebook, narration, bestiary, ledger and review files, and every buff/rule/mode addition moves the AI tuning fingerprint recorded in the activation evidence. They form a strict serial chain after this change.
- `.github/evennia-shards.json`, `tools/test_data_freeze.json` and `content/map-reference-context.json` are shared; regenerate the reference context after rebase.
