## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Outcome reactions, not EventLog replay
Extend the prerequisite state_reactions consumer with hp_loss and negative_buff_added inputs, and one validated pleasure-gain output. Reuse existing event/skill_owned conditions. Carry stable source/recipient/action/tick identity and source tier; periodic effects persist tier at application. Nonspell sources explicitly use the first tier. Do not read a mutable last-spell field or target tier.

Run at actual committed HP-loss and guarded apply_buff boundaries, including skill damage, item HP-loss effects, rulebook damage and negative rate ticks. Enumerate actual sinks before editing. Trigger only on positive actual HP loss or newly created negative instance; not MP/SP costs, healing, misses, immunity/refused adds, zero loss or refresh. Two hits are two events; new damaging debuff and subsequent ticks are separate events. Deliver each once, not again by scanning EventLog. Reaction outputs cannot emit hp_loss or negative_buff_added, preventing loops.

Gain uses canonical pleasure writer so normal arousal/wetness/phase transitions follow. Every caller declares/captures indirect sexual/cycle/buff state, including subsequent phase markers. Preserve original damage projection and existing clock transaction ordering. A later error restores all downstream reactions as well as the triggering delta.

### D2 — Recovery adjustment stays separate
Use the existing combat-modifier engine for a recovery-only rule adjustment, snapshotting it into RecoveryRatePolicy at application. For the light passive the factor is 1+0.1*caster arousal ordinal, else 1. Do not add this to global heal_gain or direct sacramental coefficients; their explicit state formulas already account for the benefit. Equipment heal_gain still composes independently once. Numeric conferred recovery rules retain existing fractional scaling; a conferred skill does not create binary event-reaction entitlement.

Final data binding declares pain_to_pleasure gains 5/8/12/18/28/40 by source tier, and priestly_grace. Both are story/import passives outside lineage; generic tests use synthetic passives with alternate values. No title string, clergy class, new quest, equipment line or saintess_vessel implementation.

### Alternatives and scope
Rejected polling for HP differences, on-read gains and duplicate log scanners. Keep the closed reaction operations small; no callback registry or arbitrarily chained spells.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
