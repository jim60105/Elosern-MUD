# Proposal

## Why

Finish 霧鬃山貓 (`fog_mane_lynx`) as an executable contact ability for its two existing variants using the landed shared engine. The user requested 「把剩餘現有的其他魔物也完成設計，考量到他們現在的描述，為他們設計符合他們的技能」 and authorized 「現有的風味文字描述可適當修改以方便實作」.

## What Changes

- Author `mane_crosswind_pounce` (鬃風佯撲), ordered wind physical damage and enemy hit-qualified accuracy debuff, with the approved costs and timed modifier.
- Populate only this species' approved MP/SP pools and bind both variants to the sole active ability and existing `ambush_predator` profile. Preserve identities, physical axes, grades and `profile_required=True`.
- Apply the approved public ecology and private explanation edits. Update this species' keyed bestiary executable metadata and current delivery notes while retaining historical approvals.
- Use existing registry-derived all-variant checks, enemy-rider representative and shared synthetic mechanism suites unchanged. Add only the required new-rule correspondence case in the existing generic suite and status-display rows; add no species-specific battery or approval mirror.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`; no delta spec files belong to this change. The current `monster-species-registry`, `monster-resource-abilities`, `monster-individual-construction` and `monster-action-policy` contracts already cover authored complete profiles, kit/reference closure, timed enemy hit-riders, atomic construction, selection/fallback and reload. Skill identity, hit/audience and out-of-combat-selection contracts are consumed unchanged. No general registry obligation, validator rule or missing relationship check is revealed by this composition.

The old four capability deltas are removed, including replacements of deleted requirement headings and per-species additions. No main spec, requirement, scenario or species roster is reintroduced.

## Impact

Implementation touches `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml` and `docs/lore/bestiary.md`. Add display rows for `mane_misdirection` and `mane_misdirection_accuracy` because status metadata must cover every buff/rule at import. The sole test edit adds `test_rule_mane_misdirection_accuracy` to existing `world/rules/tests/test_combat_modifiers.py`, satisfying the existing one-test-per-rule contract using a synthetic actor and live-row observation without a magnitude mirror.

No species-specific or representative-smoke test work is required. Both variants reuse the enemy hit-rider signature; after the goat predecessor, `cliff_stepper` remains that group's sorted minimum because `trail_hunter` and `wood_stalker` sort later. The predecessor's smoke observes its declared modifier relationship; generic integrity/construction checks automatically include the lynx rows. Shared synthetic suites already own accuracy, hit qualification, lifetime and rollback semantics.

`.github/evennia-shards.json`, `tools/test_data_freeze.json`, `world/skills/registry/assembly.py`, `monster_behaviour.yaml`, author guides and player commands remain unchanged. Existing general authoring guidance already permits these declarations. This rewrite edits planning artifacts only; registries, rulebooks and tests remain unchanged until apply.

## Non-goals

No new engine, effect kind, environment predicate, species-specific resolver branch, utility planner, balance retuning, selector rename, player-surface change, live reset, migration or compatibility layer. No other species data, main specs, archives, exploration changes or other session files are edited.

## Batch:

```text
depends-on: rock-echo-goat-resource-skill
code-conflicts: ridge-burrow-hare-resource-skill, rock-echo-goat-resource-skill
```

Preserve the approved apply order crab, hare, goat, lynx. The remaining serial predecessors are scheduling dependencies for shared edits, not cumulative spec replacements or missing runtime APIs. All remaining pairs conflict on the six data/document paths plus `test_combat_modifiers.py` listed in Impact. There is no main-spec conflict or representative-smoke edit for the lynx change. The historical batch authority §9 remains unchanged; these artifacts supersede its obsolete spec/test-file conflict explanation after `generalize-content-identity-contracts` (merge `8f33f414`).

## Size and standalone delivery

One engineer-day at most, estimated 4 hours for authored data (2h), public/private prose and keyed status (1h) and focused acceptance on existing suites (1h). This planning assumption covers a complete single-species content delivery on existing machinery.

## Design authority and approval history

The original proposal was submitted with pending-approval wording. The user approved the whole five-change batch on 2026-10-10, recorded in `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §12, including shared §§2–3 and every §8 literal and quoted prose edit listed by §11. That record supersedes the original pending wording; values are approved, implementation remains pending. The 2026-10-09 shared-mechanism/crocodile approval remains unchanged. The earlier ruling explicitly requires `usable_out_of_combat=True` for every damage-carrying monster ability, including this one.

The user ordered this in-place delivery-shape rewrite on 2026-10-11 after the generalization cutover. Approval of content remains intact; the rewrite removes obsolete specification and cloned-test work without changing any approved literal or ecological limit. Historical full-batch critique dispositions remain in design.md. No implementation, sync or archive is authorized in this planning assignment.
