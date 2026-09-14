## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Subject-scoped existing conditions
Add immutable SkillDef.cast_conditions, each containing ACTOR/EACH_TARGET and a validated existing rulebook condition. The consumer in world/rules/spell_conditions.py calls evaluate_condition with no-create state, not another condition interpreter. Optional InteractionPolicy declares distinct participants, target capability and resistance. Ordinary actor capability is always mandatory. Preflight and resolve run these after targeting/capability and before randomness, returning CAST_CONDITION_UNMET with bounded translated prose on failure. No MP/time/XP, events or lazy sexual attribute writes on such rejection; final resolution rechecks after initiative.

Contact requires distinct co-located present participants within ActionContext range. Engaged non-fled battlefield members are in range today; no position/anatomy model exists. Milk additionally requires target capability. The successful validated cast performs the ritual; request booleans never attest it. No new fluid resource or command.

### D2 — Typed state magnitudes and stimulus
Extend EffectPolicy with StateMagnitude(subject, field, base, per_ordinal, maximum). Initial fields are canonical arousal and effective_exposure; existing readers supply the ordinal. This substitutes the coefficient, not multiplies it again, and reads before this cast's stimulus. Future marker-max override extends this same object. Invalid field names/nonfinite/out-of-range curves fail authoring.

Add typed stimulus with ACTOR/TARGET/BOTH recipient scope and optional state-derived target bonus. Read the standard interval from the existing stimulus_applied rule and share the existing delta resolver/equipment gain policy; do not duplicate +8..+14. Roll each participant's gain at staging; write through apply_pleasure_gain only within PendingEffect. Include wetness, phase, extension/counters, traits and later reaction buffs in snapshots. BOTH deduplicates entity identity.

The effect strings are `stimulus:actor`, `stimulus:target`, and `stimulus:both`.
Numeric bonuses remain in a typed `stimulus_bonus: StateMagnitude | None`
policy field, never in the string. Other arguments fail parsing. Existing
sexual-act `pleasure:<act_key>` effects keep their separate act-specific formula.

### D3 — Reuse the one resistance gate
The resist gate accepts either SexualActDef.resistible or generic InteractionPolicy.resistible and never rolls twice. Do not insert elemental spells into SEXUAL_ACT_REGISTRY or duplicate lifetime-counter acquisition. Successful resistance produces the existing event, consumes MP/time, but performs no heal/cleanse/stimulus on either participant and no successful practice. Force-through produces the existing coercion EventEntry and battle/field consequences. Standard act behavior is unchanged.

Light binding: kiss requires both arousal >= 微興奮, heal 3.2+0.2*A (3.4 through 4.0), then BOTH stimulus; milk requires contact and mutual capability, heal 2.8+cleanse+TARGET stimulus with +2*caster exposure. These non-scalable state effects keep both spells outside freeform eligibility. Text/OOB/server policy paths all call the shared rules.

### Alternatives and scope
Rejected client ritual_complete flags, a separate sacred-act registry, per-skill gate branches and hardcoded intervals. The type vocabulary is deliberately small; unsupported future conditions require explicit validation and behavior, not a callback escape hatch.

## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
