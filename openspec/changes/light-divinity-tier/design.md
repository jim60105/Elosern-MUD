## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Extend the cost classifier, not ownership
Add 神格 single/direct 180..220 and area/strong 200..260. Preserve the existing two-pass algorithm: all tiers ascending in the TargetSpec-matching column, then the opposite column. SINGLE 180 is 神格; AREA 180 remains 主宰; AREA 200/240/260 are 神格. Invalid elemental costs remain errors. No new SkillDef.tier, numeric cast gate, race gate or requires_divine_arts flag.

CostTier.min_level becomes int | None so 神格 is (None, None), not a fabricated global-level interval. Follow LSP references to arithmetic/label consumers. No changes to non-light costs. The table is display classification only, and normal resource and prerequisite checks retain authority.

### Alternatives and scope
Rejected allowing arbitrary out-of-band costs or key-special-casing the capstone. Rejected overlapping-row first-match without the existing matching-column pass. The small shared classifier is sufficient for every future elemental capstone.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
