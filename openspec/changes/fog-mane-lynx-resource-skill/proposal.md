# Proposal

## Why

Finish 霧鬃山貓 (`fog_mane_lynx`) as an executable contact ability for its two existing variants using the already-landed shared mechanism. The user requested 「把剩餘現有的其他魔物也完成設計，考量到他們現在的描述，為他們設計符合他們的技能」 and authorized 「現有的風味文字描述可適當修改以方便實作」.

## What Changes

- Author `mane_crosswind_pounce` (鬃風佯撲), physical damage plus a timed buff mount, in the existing monster declaration slice.
- Replace only this species' literal MP/SP zero pools and assign its ordered kit and existing `ambush_predator` profile; retain physical axes, zero magic power, identities and grades.
- **BREAKING** Replace this species' narrative-only executable deferral and its previous zero-pool pins in existing capability requirements; adapt prose to separate ecological environment conditions from environment-independent combat.
- Require both variants' real construction/session, hit/miss, exhaustion/fallback, expiry, rollback and reload evidence, without a measured balance claim.

## Capabilities

### New Capabilities

None. Reuse the main capabilities instead of creating a species-specific duplicate.

### Modified Capabilities

- `monster-resource-abilities`: Exact ability, payment, ecology and end-to-end behavior.
- `monster-species-registry`: Explicit pools, kit and per-species deferral cutover while preserving approval gates.
- `monster-individual-construction`: Construct and persist the two complete approved configurations.
- `monster-action-policy`: Existing first-owned selection, fallback and unchanged flee behavior for this kit.

## Impact

world/lore/monster_species.py; world/skills/registry/data_monster_abilities.py; world/rules/rulebook/buffs.yaml; world/rules/rulebook/combat_modifiers.yaml; .github/evennia-shards.json; tools/test_data_freeze.json; docs/lore/bestiary.md; docs/lore/monster-creation-guidelines.md; docs/development/adding-spells.md. Existing construction/policy code is reused, with focused tests rather than a second execution path. `world/skills/registry/assembly.py` already includes MONSTER_ABILITIES_ROWS and needs no edit; preserve its ordered slice as a serialization/review boundary. `monster_behaviour.yaml` is read-only here because the selected archetype already exists.

## Non-goals

No implementation in this proposal phase; no new engine, artificial races, species-specific resolver branches, planner redesign, new combat formulas, cost classifications or payment order, human-reference/grade recalibration, live resets, migrations or compatibility layers. No crocodile changes, selector renames, weather engine, command-surface changes or command-doc edits. Unrelated exploration changes are excluded.

## Batch:

```text
depends-on: rock-echo-goat-resource-skill
code-conflicts: sway-whistle-sparrow-resource-skill, tide-lamp-crab-resource-skill, ridge-burrow-hare-resource-skill, rock-echo-goat-resource-skill
```

The archived prerequisite names above are already delivered. The new serial chain is sparrow, crab, hare, goat, lynx; preceding new changes must land first because full MODIFIED registry blocks include cumulative approved pools and completed deferrals. All pairs share the files listed in Impact and the registry/ability main-spec blocks. No concurrent apply. No apply/archive/sync in this planning assignment. The whole-set matrix is in `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §9.

## Size and standalone delivery

At most one engineer-day, estimated 7 hours: declarations and profile pins (1h), buff/modifier content (1h), construction/policy/data contracts (1h), two-variant session/expiry/rollback/reload acceptance (2h), ecology/author guides and focused gates (2h). This is a complete single-species delivery on existing machinery, independently usable after its listed predecessor; no partial kit or deferred runtime task is counted as done. The estimate is a planning assumption.

## Design authority and approval

`docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §8 is proposed and pending user approval. The already-approved 2026-10-09 document remains unchanged; only its five-species deferral is proposed to be superseded for this species. Pool literals, costs, coefficient, buff magnitude/duration, profile and prose changes all require approval before apply.
