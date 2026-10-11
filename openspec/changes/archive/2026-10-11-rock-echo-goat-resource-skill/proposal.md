# Proposal

## Why

Finish 岩響山羊 (`rock_echo_goat`) as an executable contact ability for its two existing variants using the landed shared engine. The user requested 「把剩餘現有的其他魔物也完成設計，考量到他們現在的描述，為他們設計符合他們的技能」 and authorized 「現有的風味文字描述可適當修改以方便實作」.

## What Changes

- Author `rock_echo_ram` (岩響角撞), ordered earth physical damage and enemy hit-qualified agility debuff, with the approved costs and timed modifier.
- Populate only this species' approved MP/SP pools and bind both variants to the sole active ability and existing `ambush_predator` profile. Preserve identities, physical axes, grades and `profile_required=True`.
- Apply the approved public ecology and private explanation edits. Update this species' keyed bestiary executable metadata and current delivery notes while retaining historical approvals.
- Rebind the existing enemy-rider composition smoke to `cliff_stepper` and replace its accuracy-only consumer assumption with the representative's declared modifier relationship. Reuse generic all-variant checks and shared synthetic mechanism coverage; add no species-specific suite or approval mirror.
- Add required status-display metadata and one declaration-derived correspondence case for the new combat-modifier rule in the existing generic suite.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`; no delta spec files belong to this change. The current `monster-species-registry`, `monster-resource-abilities`, `monster-individual-construction` and `monster-action-policy` contracts already cover authored complete profiles, kit/reference closure, timed enemy hit-riders, atomic construction, selection/fallback and reload. Skill identity, hit/audience and out-of-combat-selection contracts are consumed unchanged. The existing representative smoke's accuracy assumption needs a test edit, not a new behavior contract or validator rule.

The old four capability deltas are removed, including replacements of deleted requirement headings and per-species additions. No main spec, requirement, scenario or species roster is reintroduced.

## Impact

Implementation touches `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml` and `docs/lore/bestiary.md`. Add display rows for `rock_echo_stagger` and `rock_echo_stagger_agility_flat` because status metadata must cover every buff/rule at import. Add one `test_rule_rock_echo_stagger_agility_flat` case in existing `world/rules/tests/test_combat_modifiers.py` to satisfy the current one-test-per-rule contract, using a synthetic actor and the live row without a magnitude mirror.

Rebind the existing `world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` representative declaration from `flock_leader` to `cliff_stepper`, the group's new sorted minimum. The smoke derives skill, buff, duration, costs and binding, but currently observes only `accuracy`; observe the live modifier row's axis/delta so the goat's `agility_flat` contribution is exercised. Keep existing modules/classes, shard ownership, freeze entries/reasons and traceability annotations; no `.github/evennia-shards.json` or `tools/test_data_freeze.json` edits are needed.

`world/skills/registry/assembly.py`, `monster_behaviour.yaml`, author guides and player commands remain unchanged. Existing general authoring guidance already permits these declarations. This rewrite edits planning artifacts only; registries, rulebooks and tests remain unchanged until apply.

## Non-goals

No new engine, effect kind, environment predicate, species-specific resolver branch, utility planner, balance retuning, selector rename, player-surface change, live reset, migration or compatibility layer. No other species data, main specs, archives, exploration changes or other session files are edited.

## Batch:

```text
depends-on: ridge-burrow-hare-resource-skill
code-conflicts: ridge-burrow-hare-resource-skill, fog-mane-lynx-resource-skill
```

Preserve the approved apply order crab, hare, goat, lynx. The remaining serial predecessors are scheduling dependencies for shared edits, not cumulative spec replacements or missing runtime APIs. All remaining pairs conflict on the six data/document paths plus `test_combat_modifiers.py` listed in Impact; the hare/goat representative-smoke edits are in different modules. There is no main-spec conflict. The historical batch authority §9 remains unchanged; these artifacts supersede its obsolete spec/test-file conflict explanation after `generalize-content-identity-contracts` (merge `8f33f414`).

## Size and standalone delivery

One engineer-day at most, estimated 6 hours for authored data (2h), public/private prose and keyed status (1h), the bounded representative/consumer edit (1h) and focused acceptance (2h). This planning assumption covers a complete single-species content delivery on existing machinery.

## Design authority and approval history

The original proposal was submitted with pending-approval wording. The user approved the whole five-change batch on 2026-10-10, recorded in `docs/superpowers/specs/2026-10-10-remaining-monster-resource-skills-design.md` §12, including shared §§2–3 and every §7 literal and quoted prose edit listed by §11. That record supersedes the original pending wording; values are approved, implementation remains pending. The 2026-10-09 shared-mechanism/crocodile approval remains unchanged. The earlier ruling explicitly requires `usable_out_of_combat=True` for every damage-carrying monster ability, including this one.

The user ordered this in-place delivery-shape rewrite on 2026-10-11 after the generalization cutover. Approval of content remains intact; the rewrite removes obsolete specification and cloned-test work without changing any approved literal or ecological limit. Historical full-batch critique dispositions remain in design.md. No implementation, sync or archive is authorized in this planning assignment.
