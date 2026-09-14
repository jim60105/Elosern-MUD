## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Actor peak without altering the divine effect
Add typed pleasure_peak using the ordinary audience policy (SELF for the emergency spell). One apply closure calls canonical apply_pleasure_gain(recipient,100) then (recipient,0). Existing divine_pleasure_max keeps its actor exclusion. Do not assign phases directly. From 未達/餘韻 two legal edges enter 進行中; from 接近 the first call enters and the zero call does not create an extension. An already locked actor cannot cast at all.

The grammar is the bare string `pleasure_peak`; suffixes are rejected. Binding
and magnitude remain typed policy data. The older divine prefix is not an alias.

### D2 — Narrow transition reactions, existing rule evaluator
Add world/rules/state_reactions.py and rulebook/state_reactions.yaml as another consumer of load_rules/evaluate_condition, not a new language or event bus. Dispatch once after a successful canonical _apply_climax_phase_set edge, including rulebook and direct-gain callers. A typed ownership trigger references a skill and existing prerequisite-satisfaction query; extend the shared condition vocabulary narrowly for this qualification. Only allowed output in this slice is apply/remove a declared marker via apply_buff; it cannot recursively change phase.

Qualified apotheosis ownership at entry into 進行中 grants a persistent cycle marker without casting apotheosis. Invalid/no-op edges do nothing. It survives 餘韻 and re-entry, removes at 未達, and does not retroactively appear when ownership is acquired mid-cycle. Removing qualification disables benefits immediately. No active phase writes on reads.

### D3 — Maximum state input, not universal power
StateMagnitude may reference an empowerment marker that selects its authored maximum. Kiss max coefficient is 4.0; milk's state-derived exposure contribution uses the maximum ordinal. Fixed coefficients 2.8/3.4/3.8 remain fixed. Conditions, resistance and action locks still run. Ordinary actions resume in 餘韻 while the marker remains. No grace double multiplier or custom lock timer.

All phase-triggered marker writes join the initiating action/clock/outer transaction. Expand declared/snapshot surfaces for every existing path that can now cause a reaction, including divine_pleasure_max, normal stimulus and sexual rule events; do not protect only the new effect. Refetch and late-failure tests establish lifecycle behavior.

### Alternatives and scope
Rejected a permanent capstone flag, last-cast history entitlement and direct state assignment. The generic phase/reaction/marker boundary supports future state-driven schools without light-key branches.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
