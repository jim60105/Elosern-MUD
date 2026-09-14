## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — One immutable policy per effect ordinal
Add frozen EffectPolicy(coefficient=1.0) beside the existing typed effects, plus SkillDef.effect_policies, an immutable tuple normalized at construction to the same length as effects. Empty input means the ordinary identity policy, not a migration shim. Validate cardinality, finite positive numeric coefficients (reject bool), and supported effect kinds. Duplicate effect strings can have distinct policies because binding is by ordinal, never prefix. Extend _skill/_spell with named parameters; do not grow the elemental builder's positional row grammar.

### D2 — Preserve the dispatcher, bind trusted context
Step 5 supplies a frozen ResolvedEffect(policy, source_skill) in the reserved event_context key resolved_effect, overriding caller data without mutating the request dictionary. Each effect gets its own binding; no previous-effect leakage. ActionResolver.preflight synthesizes the identical binding wherever it dry-runs an effect handler, so a missing binding never rejects an ordinary cast that the resolver itself staged. The five-argument handler API remains unchanged. A handler invoked directly without the binding uses ordinary identity semantics. Only ActionResolver creates a trusted binding during a cast. No key-indexed shadow registry, arbitrary callbacks, expression interpreter or light-specific runtime module.

### D3 — Numerical stages
Damage: on a hit compute max(round(adjusted_attack * roll_multiplier * coefficient) - adjusted_defense, damage_floor), then existing freeform scaled_magnitude and final floor. Healing: insert coefficient inside round(adjusted_magic * heal_multiplier * coefficient), then existing base floor, equipment heal_gain flooring, freeform rounding and living-recipient HP clamp. No multiplication of an already defense-reduced result. Preserve miss=0, no revival, effective rather than disguised stats, nonlethal projection and EventLog ordering. Coefficient does not change MP, eligibility or mastery entitlement.

### Alternatives and scope
Rejected numeric effect-string suffixes because they duplicate the typed policy contract; rejected per-spell handlers because other schools must reuse this code. Identity policies preserve the ordinary semantics of unconfigured effects, not old data aliases. This slice implements coefficients only, not future placeholder policy fields.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
