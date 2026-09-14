## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Bounded event-derived evidence
Add world/rules/action_evidence.py: an allowlisted recent-action-evidence mapping with expiry in world-clock seconds and stable actor identity. Initial event kind is forced_interaction. One deterministic EventLog planner stages evidence on the perpetrator when a sexual_resist entry has resisted is False AND auto_comply is False. Direct resolver calls, NPC turns and both settlement modes share it. No affinity inference, prose scan, unbounded log search or second coercion penalty scanner.

Light duration is 60 world seconds, active while now < expires_at. Repeated incidents use max(old expiry, event time + duration), never increase the strike count. Queries are read-only even for expired records. Failed action/clock/outer transactions restore the attribute and caches. An incident against a non-NPC still qualifies even if affinity penalties are inapplicable. Blasphemy is explicitly narrative-only in amended lore.

### D2 — One configured extra strike
Extend DamagePolicy with repeat_when (closed recent-evidence predicate) and extra_strikes limited to one. Matching targets get two independently staged d100 checks with identical policy, even if strike one misses. No recursive repeats. Project HP sequentially before final defeat/knockout events, preserve both roll entries, and charge one cast's resources/time/practice. Both strikes and evidence are within the same rollback.

### Alternatives and scope
Rejected permanent criminal flags, narrative classification and repeated whole-action invocation (would double debit resources). A bounded expiry map is sufficient and reusable by later retaliation spells; new incident kinds require a new typed producer, not arbitrary caller strings.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
