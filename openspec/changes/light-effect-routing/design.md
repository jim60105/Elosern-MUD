## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Per-effect delivery within the selected pool
Extend EffectPolicy with EffectAudience.SELECTED, SELF, ALLIES, ENEMIES. SELECTED is the identity. ALLIES includes selected Relation.SELF/ALLY; ENEMIES selects Relation.ENEMY. Neither adds unselected bystanders. SELF explicitly binds the actor, mirroring self_heal, with presence/alive/range/capability validation. An inherently actor-bound prefix rejects contradictory audience configuration.

Preflight and final resolution share pure audience planning, final resolution re-reading relations after initiative. Derive subsets once and only when policies need them. An empty subset skips that effect without a roll; if every effect has no recipient, reject NO_VALID_TARGETS_IN_AREA without costs. A full-HP heal/empty cleanse with a recipient is still legal. Use actual delivered recipients for staged state/snapshot/event attribution; retain one ordinary practice claim per eligible actor/skill/target/tick, not per effect.

### D2 — No skill-level faction restriction
Keep TargetRequirement/validate_faction ANY and SELF_ONLY unchanged. Generic attacks can hit companions and generic heals can target foes. Clarify the main spec's blanket language: free candidate selection does not require every component of an explicitly routed skill to affect every candidate. The two mixed light compositions are data only: ENEMIES damage + ALLIES cleanse; ALLIES heal + ENEMIES damage. RoomActionContext still has no hostility model and treats other present entities as allies.

### Alternatives and scope
Rejected changing legacy FactionConstraint.ALLY/ENEMY because it would break friendly-fire reachability and cannot represent a mixed spell. Rejected handler-local filtering because damage/cleanse/UI would drift. No implicit party/room expansion. Existing explicit lists and all/enemies/allies shorthand build the pool. Update server-backed previews and documentation to agree with execution; no new UI interaction is required.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
