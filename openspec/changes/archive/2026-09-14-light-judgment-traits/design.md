## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Facts are explicit persistent data
Use existing affinity_elements for elemental affiliation. Add a validated combat_traits collection to LivingEntity, initially accepting only undead; missing means empty. No duplicate dark flag or name/race/last-cast inference. The setter belongs in world/rules/traits.py, the pure reader in world/rules/target_facts.py. Skill/lore modules only declare or read. Imports and authored spawn descriptors reject unknown, duplicate or non-string values before persistence, then propagate the collection through real import, compiled quest spawning and wilderness/NPC construction. Preserve all age bounds. No DB model migration.

### D2 — Conditional damage is part of EffectPolicy
Add a frozen DamagePolicy: optional ANY-of target membership predicate, conditional attack multiplier, conditional defense bypass and max_hp_fraction. Validate finite bounded numeric fields and allowed fact namespaces at authoring time; no callbacks or untrusted request facts. One predicate matching both dark affinity and undead applies only once. Empty/default policy is exactly the ordinary potency formula.

On a hit: attack_part = round(adjusted_attack * roll_multiplier * coefficient * matched_multiplier); subtract zero defense when the bypass predicate matches, otherwise adjusted defense; add floor(max_hp * max_hp_fraction); then normal floor, freeform scaling, final floor and nonlethal projection. A miss never receives the percent-HP rider. Execution does not automatically imply a bonus multiplier.

### D3 — Light data remains in final integration
Arrow/strike choose 1.5 for dark OR undead, penitent 1.5 for undead only, execution bypass for dark OR undead without 1.5, capstone max_hp_fraction=0.10. Radiance receives no undeclared anti-undead modifier. Other schools can configure the same policies with other registered elemental facts.

### Alternatives and scope
Rejected new undead species and a second affinity store. Rejected a generic expression language. Keep the field and import/spawn extension narrow: one optional collection, no new bestiary subsystem or migration. Do not change unrelated NPC construction behavior.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
