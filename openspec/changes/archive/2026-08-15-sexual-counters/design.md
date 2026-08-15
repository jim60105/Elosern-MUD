## Context

`SexualState._traits` is a `TraitHandler` already holding one lifetime-shaped counter,
`climax_today` (`trait_type="counter", min=0`, reset daily by `reset_daily_counters()`), mutated
through exactly one method, `record_climax()` (`self._traits.climax_today.base += 1`). The
`sexual-transition-rulebook` spec already pins the discipline this proposal extends to eleven more
fields: no rule and no effect handler may reach `SexualState._traits` (or any other
leading-underscore attribute) directly — every mutation goes through a named public method, and a
structural test already inspects `sexual_transitions.py` for violations of exactly this rule.

This is proposal `B2` from the
[Sexual Act System overview](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md)
and the [Sexual Pleasure Model](../../../docs/superpowers/specs/2026-08-15-sexual-pleasure-model-design.md)
§2. It depends on `pleasure-gauge` (`B1`) only because both proposals edit `sexual_state.py`
sequentially — there is no functional dependency between `pleasure` and any of these eleven counters.

## Goals / Non-Goals

**Goals:**
- Give every counter the design doc's table names exactly one field, one read property, and one
  mutator, matching `climax_today`/`record_climax()`'s existing shape precisely.
- Keep every counter unbounded and lifetime (never reset), since they exist to answer "how many times
  has this ever happened", not "how many times today."

**Non-Goals:**
- Wiring any counter to a trigger. This proposal adds no `sexual.yaml` rule, no effect handler, no
  upkeep call. `climax-settlement` (`B3`) and `sexual-act-effects` (`B5`) each wire a subset later,
  against the stable API this proposal ships.
- Role-scoped grants (an act incrementing one counter for its actor and a different one for its
  targets). That is a property of how a *caller* uses these mutators, decided entirely by the
  proposal that owns the caller (`B3`'s upkeep code, `B5`'s effect handlers) — nothing about the
  mutator's own shape needs to know about roles.
- A generic "increment by N" mutator. Every design-doc trigger is a discrete per-occurrence event;
  every mutator increments by exactly `1`, matching `record_climax()`.

## Decisions

### D-1: Field naming avoids two real collisions

Two of the eleven design-doc names collide with names `SexualState` already uses for something else,
and the delta spec and implementation must use distinct storage keys to avoid silently shadowing
existing, unrelated state:

- **露出次數** ("exposure count", an act-occurrence tally) would collide with `exposure`, the
  existing `OrderedLevelTrait` field (a *state level*, not a counter). Stored as `exposure_act_count`
  / `record_exposure_act()`.
- **高潮次數** ("climax count", a lifetime tally) would collide conceptually with `climax_today`
  (a *daily-reset* tally, unrelated, already shipped, untouched by this proposal) and with its
  existing mutator `record_climax()`. Stored as `climax_count` / `record_climax_count()` — a
  genuinely new, separate field and method; `record_climax()` and `climax_today` are not modified,
  renamed, or aliased by this proposal. Both mutators will typically be called together when a
  climax actually settles, but that pairing is `B3`'s wiring decision, made in a later proposal, not
  a coupling built into either mutator here.

The full field/property/mutator table:

| Axis | Design-doc name | Field key | Mutator |
|---|---|---|---|
| 獨處 | 自慰次數 | `masturbation_count` | `record_masturbation()` |
| | 玩具使用次數 | `toy_use_count` | `record_toy_use()` |
| 羞恥 | 露出次數 | `exposure_act_count` | `record_exposure_act()` |
| | 被觀看次數 | `watched_count` | `record_watched()` |
| 關係 | 雙人行為次數 | `duo_act_count` | `record_duo_act()` |
| | 多人行為次數 | `group_act_count` | `record_group_act()` |
| 戰鬥 | 對敵行為次數 | `hostile_act_count` | `record_hostile_act()` |
| | 忍耐次數 | `restraint_count` | `record_restraint()` |
| 異種 | 異種行為次數 | `interspecies_act_count` | `record_interspecies_act()` |
| 高潮 | 高潮次數 | `climax_count` | `record_climax_count()` |
| | 連續高潮次數 | `climax_extension_count` | `record_climax_extension()` |

### D-2: Shape is identical to climax_today, times eleven

Each field: `self._traits.add(<key>, trait_type="counter", base=0, min=0)` — no `max` (unbounded,
matching `climax_today`, unlike `pleasure`'s bounded `max=100`). Each mutator:
`self._traits.<key>.base += 1`. Each read property: `return int(self._traits.<key>.value)`. None is
touched by `reset_daily_counters()` — that function's body stays exactly as shipped, still naming
only `climax_today`.

Construction: all eleven are added unconditionally in `_build_from_baseline()`, always starting at
`base=0` — no baseline field feeds any of them (`CHARACTER_SCHEMA_V1`'s import contract carries no
behaviour-history data, and none is added by this proposal). This means every entity, imported or
freshly constructed, Monster or not, starts with all eleven counters at `0`.

### D-3: Why the delta spec groups requirements by shared shape, not one per counter

Eleven requirement blocks that differ only in a field name would be pure repetition with no added
reader value — the `spec-test-traceability` discipline wants a requirement wherever behaviour is
distinct, not wherever a name changes. The delta spec instead states the shared contract once
(one field, one mutator, always increments by exactly `1`, never resets, no other write path) and
enumerates the eleven fields as an exhaustive table inside that requirement, with one representative
scenario plus one structural, table-driven scenario proving all eleven exist and are independent.
This mirrors how the shipped `sexual-transition-rulebook` spec already states
"`FIELD_KINDS`... SHALL equal exactly the set of `then.field` values" once, structurally, rather than
one requirement per field.

## Risks / Trade-offs

[Risk] Building the counter surface with no consumer yet means it is untested by real call sites
until `B3`/`B5` land, so a mutator's shape could turn out to be a poor fit for what those proposals
actually need (e.g. needing a bulk grant rather than a single increment). → Mitigation: the shape is
already fully determined by the design doc's own per-trigger table ("incremented when X happens" —
always a discrete event, never a bulk operation), and it exactly mirrors an already-proven shape
(`climax_today`/`record_climax()`), so the risk of a shape mismatch is low. If a future proposal does
need bulk semantics, adding a second mutator later is a small, additive, non-breaking change.

[Risk] None identified for rollback: purely additive fields with no migration and no interaction with
existing persisted state.

## Migration Plan

None required — purely additive, zero released users.

## Open Questions

None.
