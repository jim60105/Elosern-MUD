## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — A rate variant in the existing buff engine
Introduce frozen RecoveryRatePolicy in the buff-definition owner, with hp target, nonnegative base amount, optional recipient-state percent-per-ordinal and caster heal_gain snapshot. A rate uses either fixed delta OR recovery profile; reject contradictory/unknown/nonfinite data. Keep existing duration, tick_interval and stacking fields. Reuse no-create StoredLevel/effective_exposure and living HP clamping. No second scheduler, buff class per spell, expression DSL or global activation of inert bounds.

Application captures source identity and heal_gain in persistent buff cache. Tick re-reads recipient effective exposure, not caster state. A later reaction change adds the same profile's optional recovery multiplier, identity 1 when absent. Source deletion/logout/equipment changes do not break ticks. Fixed item regeneration and damaging rates keep their existing semantics. Recovery-profile tick_interval must be a multiple of the existing global settlement quantum (currently 10 seconds), validated at definition load: the quantum is derived as the gcd over all buff/decay intervals, and a non-multiple would silently requantize every settlement. Ward's interval is 10, matching the existing quantum.

### D2 — Precise timing and refresh
Light binding uses base 12 HP, +10% per recipient exposure ordinal; floor after the product with captured heal_gain and optional recovery multiplier, clamp nonnegative and to living HP gap. Ticks occur at elapsed 10/20/30, never application time, final tick before expiry. Large and split elapsed advances agree within the clock's max_settlement_quanta budget: the existing clock drops quanta beyond that cap, and a truncated advance legitimately produces fewer ticks through no fault of the profile; behavioral tests stay within the cap and additionally assert that a beyond-cap advance never fabricates ticks. Recast replaces source snapshots and resets both remaining duration and tick accumulator for exactly three new ticks; no stacking. Removal stops future ticks; refetch preserves remainder without replay. A dead recipient stays dead.

### D3 — Timed defense through the existing modifier table
Use a refresh marker and a combat_modifiers.yaml buff_active rule, not bounds. Light blessing later binds defense +18 for 60 seconds. Verify actual damage changes, additive composition with equipment and expiration, using synthetic markers. This change's reusable behavior tests do not require shipping any new light definition prematurely.

### D4 — Remove test-name coupling
Remove the main requirement and mechanical checker for exactly one test_buff_<key> per buff. Replace it with coverage of distinct observable rate/refresh/expiry/immunity behavior. Retain useful existing tests; do not generate new key-specific tests or data-freeze entries. Status display remains fail-closed. This is the minimum gate change needed for behavior-only testing, not a coverage exemption.

### Alternatives and scope
Rejected snapshotting recipient exposure (would defeat the stated live exposure benefit), retaining live caster references, and scheduling wall-clock callbacks. Do not change unrelated bounds/control semantics.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
