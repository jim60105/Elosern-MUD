# Design: add-equipment-sexual-effects

## Context

Parent design §8 (line ~227: `pleasure_gain` folds as one final multiplier
into `compute_pleasure_gain()`, the sole pleasure funnel — no requirement
that it ride the combat evaluator). Exposure is an `OrderedLevelTrait` on
`entity.sexual` over `EXPOSURE_LEVELS = ("極低","低","中等","高","極高")`.
Two combat-modifier condition builders read it: `_build_context`
(`combat_modifiers.py:136`, trait object) and
`build_no_create_condition_context` (`combat_modifiers.py:104-121`, pure
storage reads through the module-local `_stored_sexual_level` reader +
`_StoredLevel` view; handler-free and write-free by hard contract). The
shipped 露出 ≥ 高 → defense −15 rule matches on that context field.
`compute_pleasure_gain()` (`sexual_act_effects.py:235`) is
`round(base × ratio × sensitivity × shame × crowd)` with a single call site
(`action.py:811`). `sexual_transitions.py` matches its rulebook against
stored state (the shipped `sexual.yaml` has exposure EVENT/field-change
rules, no exposure threshold conditions) and snapshots the stored trait.
P1 registered `pleasure_gain`/`exposure_bias` per item; the shipped
combat-modifier adjustment vocabulary carries neither key today.

## Goals / Non-Goals

**Goals:**

- `exposure_bias` becomes a live read-time overlay consumed by rule
  matching, resist scoring, and player-facing reads.
- `pleasure_gain` folds into the one pleasure funnel with a normative
  formula and an equipment-only, immutable source.
- Stored sexual identity (exposure trait, sensitivity, shame, virginity,
  eleven counters) stays byte-for-byte equipment-immune.

**Non-Goals:**

- Layered breakdown rendering (P6/P7), `equipment_worn` grace rules (P5),
  new items (P1 registered them all), transition rulebook changes, rule-
  table `pleasure_gain` adjustments (reserved data shape; no shipped rule
  emits it — when one does, its owning change extends the evaluator).

## Decisions

### D1 — Shared neutral stored-sexual reader; overlay at context-build time

`_stored_sexual_level` and `_StoredLevel` move OUT of `combat_modifiers.py`
into a neutral module (imports lore + Evennia attribute storage only);
`combat_modifiers` and `equipment_effects` both import it — the module graph
stays acyclic and the no-create path keeps its handler-free, write-free
contract byte-for-byte. `effective_exposure(entity)` =
`EXPOSURE_LEVELS[clamp(index(stored) + Σ worn exposure_bias, 0, 4)]`,
computed via that shared reader + the P1 rulebook; it never writes.
Bias-before-rule-matching is acyclic because bias is equipment-only (no
shipped rule-table adjustment targets exposure). Both builders then fill
`context["exposure"]` with the SAME immutable level view type (the shared
`_StoredLevel`-style object carrying `.value`, `.levels`, and ordinal
`gte`/`lte`/equality parity — the handler path stops passing the raw trait
into the context; a parity test locks all three comparison styles on both
paths). Alternative — persisting bias into the trait at toggle time:
rejected (write-back corruption, snapshot entanglement, breaks when the
item is lost).

### D2 — Overlay never leaks into transition semantics

`sexual_transitions` is explicitly STORED-classified: bias SHALL NOT alter
transition rule matching, SHALL NOT raise `field_changed: exposure`, and
SHALL NOT touch snapshots or mutations. Act-driven progression persists
exactly as shipped; equipping/unequipping never mutates stored exposure. An
allowlist test classifies every shipped consumer of stored
`sexual.exposure` as STORED (transitions, snapshot, persistence, imports)
or EFFECTIVE (both context builders, status read-model row, the accessor);
a new raw consumer outside the list fails the test and must be classified.

### D3 — Pleasure percent is equipment-only and parameter-passed

`equipment_pleasure_gain(entity)` is a pure accessor in
`world/rules/equipment_effects.py` (same fold pattern as P2's
`equipment_adjustments`; malformed storage → 0).
`compute_pleasure_gain(...)` gains `pleasure_percent: int = 0`; the single
caller passes the accessor's value. Normative formula (single final
rounding):
`max(round(base × ratio × sensitivity × shame × crowd × (1 +
pleasure_percent / 100)), 0)`. `pleasure_gain = 0` reproduces shipped
goldens exactly. Alternative — routing the percent through
`evaluate_combat_modifiers_no_create()`: REJECTED; P2 deliberately scoped
the evaluator's output to combat adjustment keys, and resist scoring,
overwhelm estimation, preview, and P2's heal path all consume that bundle —
adding a non-combat key would silently change a shipped contract those
consumers' tests never audited. A test locks the evaluator's output
key-set (the `pleasure_gain` key must NEVER appear in it).

### D4 — Status row and web payload show the effective value together

`status_query` renders the effective exposure in the existing row (row
contract unchanged, value overlay only), and the web status payload derives
from the same read-model, so both surfaces agree by construction; an
end-to-end contract test asserts one effective value in both surfaces and
an unchanged row/payload schema (no JS change). Per-source layer breakdown
(裝備 +1) lands with P6/P7.

## Risks / Trade-offs

- [Rule authors must know context exposure is effective] → D2's allowlist
  plus scenario tests document the semantics at the only two entry points.
- [Moving `_StoredLevel` may break test imports] → re-export from
  `combat_modifiers` if any test module imports it there; grep before
  moving.
- [Negative-percent chastity-style gear could zero pleasure] → the clamp is
  the contract; roster values are all ≥ 0, but the floor keeps future data
  safe.

## Open Questions

None.
