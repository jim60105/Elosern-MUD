## Context

`SexualState.arousal` is one of five `OrderedLevelTrait` fields (`world/rules/sexual_state.py`), a
project-authored `Trait` subclass wrapping a bounded ordinal into a fixed vocabulary tuple
(`AROUSAL_LEVELS = ("平靜", "微興奮", "中等", "高度", "極限")`, from `world/lore/sexual_vocab.py`).
It is read by three files this proposal must not touch: `world/rules/rulebook/combat_modifiers.yaml`
(`high_arousal_agility_accuracy_penalty`, `{field: arousal, gte: 高度}`), `world/rules/overwhelm.py`
(reads effective stats generically, unaffected either way), and
`world/rules/rulebook/status_display.yaml` (displays the level name).

It is written by exactly four rules in `world/rules/rulebook/sexual.yaml`, all `then.field: arousal`,
and read (for `field_changed` conditions) by one more: `wetness_follows_arousal`
(`{field_changed: arousal, direction: up}`).

This is proposal `B1` from the
[Sexual Act System overview](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md)
(D-3) and the [Sexual Pleasure Model](../../../docs/superpowers/specs/2026-08-15-sexual-pleasure-model-design.md)
§1. Both source documents are the design authority; this document works out the Evennia-API-level
mechanics they leave at the architecture level.

## Goals / Non-Goals

**Goals:**
- Make `pleasure` (`0..100`) the single authoritative arousal quantity, fine-grained enough for a
  gain formula (act base magnitude × sensitivity multiplier × shame multiplier × participant-count
  multiplier — the forthcoming `B5`'s concern, not this proposal's).
- Keep `arousal` fully backward-*readable*: every comparison a reader already performs
  (`>=`, `==`, `.level`) continues to return the same answers it would have under the old five-level
  representation, for the same conceptual arousal state.
- Touch no file this proposal does not need to: `combat_modifiers.yaml`, `overwhelm.py`,
  `status_display.yaml` stay untouched, and (per D-1) `sexual_pleasure.yaml`'s multiplier tables are
  created now but consumed only by the later `B5` proposal.

**Non-Goals:**
- The gain formula itself (sensitivity/shame/participant-count multiplication). That is `B5`'s
  responsibility; this proposal only creates the data tables `B5` will read.
- Any change to `world/imports/schema.py` or the `CHARACTER_SCHEMA_V1` baseline shape. An imported
  character's `entity.db.sexual["arousal"]` stays a level string (`"微興奮"`, etc.) exactly as today
  — see D-2 for how construction adapts that string into an initial `pleasure` value without
  changing the import contract.
- Extension/climax-settlement mechanics. Those belong to the later `climax-settlement` proposal
  (`B3`), which depends on this one.

## Decisions

### D-1: `sexual_pleasure.yaml` is a plain validated config table, not a `Rule` table

`world/rules/rulebook/schema.py::load_rules()` parses a YAML list of `{id, when, then}` entries
matched by `evaluate_condition()`. A five-band range lookup (`pleasure 0..100 → one of five levels`)
does not fit that shape — `evaluate_condition()` has no "between" primitive, only `equals`/`gte` — and
forcing it in would mean inventing a range condition primitive for exactly one consumer.

Every other plain configuration table in `world/rules/rulebook/` (`combat.yaml`, `overwhelm.yaml`,
`affinity.yaml`) is instead loaded by a small dedicated Python function and, where the shape has
real structure to validate (as `affinity.yaml`'s seven-stage ladder does via `AffinityConfig` in
`world/rules/affinity_config.py`), wrapped in a frozen dataclass with explicit field validation that
fails closed on malformed data. `sexual_pleasure.yaml` follows that precedent exactly: a
`PleasureConfig` frozen dataclass in `world/rules/sexual_state.py`, loaded once at import time into a
module-level singleton, `PLEASURE_CONFIG` — matching `sexual_transitions.py`'s own existing
`_RULES = _load_rules()` eager-load pattern. `sexual_state.py` owns the loader; `PLEASURE_CONFIG` is
then imported by every band-lookup consumer, which is **not** only `sexual_state.py` itself — the
`bounded_counter` `_apply_then()` branch in `sexual_transitions.py` (D-4) and the no-create read
paths in `combat_modifiers.py`/`status_query.py` (D-7) both need it too. Every consumer imports the
same frozen, already-loaded data object; none of them materializes any entity's `SexualState` or
`TraitHandler` by doing so — reading a shared, process-wide config table is unrelated to the
"no-create" discipline those two files' own callers require (D-7 explains this in detail). The loader
validates:

- `pleasure_bands`: exactly five entries, one per `AROUSAL_LEVELS` member in order, each
  `{level, floor, ceiling}` with `floor`/`ceiling` integers, contiguous (`entry[i].ceiling + 1 ==
  entry[i+1].floor`), starting at `floor == 0` and ending at `ceiling == 100`.
- `sensitivity_multipliers`: exactly the four `SENSITIVITY_LEVELS` keys, each a positive float.
- `shame_multipliers`: exactly the five `SHAME_LEVELS` keys, each a positive float.

```yaml
pleasure_bands:
  - {level: 平靜,   floor: 0,  ceiling: 14}
  - {level: 微興奮, floor: 15, ceiling: 34}
  - {level: 中等,   floor: 35, ceiling: 59}
  - {level: 高度,   floor: 60, ceiling: 84}
  - {level: 極限,   floor: 85, ceiling: 100}

sensitivity_multipliers:
  普通: 1.0
  高: 1.4
  極高: 1.8
  敏感異常: 2.5

shame_multipliers:
  無: 1.0
  輕微: 0.9
  中等: 0.8
  強烈: 0.65
  成癮: 1.6
```

`participant_count_multiplier` (the pleasure model's third multiplier table) is **deliberately not
created by this proposal**. The design doc gives exact numbers for sensitivity and shame but only
says the participant table should be "a mild bonus... declared in the same table" — no numbers.
Inventing a business value now that `B5` (the proposal that actually consumes it, and is written
later) has no say in would risk a mismatch. `B5` adds that section to this same file when it lands;
this is not a violation of `pleasure-gauge`'s file ownership, since ownership in the overview's
batch table governs *concurrent* edits within one parallel batch, not a permanent lock — `B1` (batch
1) and `B5` (batch 4) never run concurrently.

### D-2: `pleasure` is a `CounterTrait`, matching the `climax_today`/`magic_level` precedent exactly

`entity.sexual._traits` is a `TraitHandler`. Two fields already use `trait_type="counter"`
(Evennia's `CounterTrait`, bounded by `min`/`max`, value = `(current + mod) * mult` with `mod=0`,
`mult=1.0` by default so `value == base` in every case this codebase uses): `climax_today`
(`SexualState`, `min=0`, no `max`) and `magic_level` (`world/rules/traits.py`, `min=0,
max=magic_cap`). `magic_level` is the closer precedent — a *bounded* counter, exactly `pleasure`'s
shape.

`pleasure` is added as `trait_type="counter", base=0, min=0, max=100`. `CounterTrait.base`'s own
setter enforces the `[min, max]` clamp on every assignment
(`CounterTrait` at `.../evennia/contrib/rpg/traits/traits.py` line 1379 — confirmed empirically:
`base += 14` from `95` stores `100`, never `109`), so no manual clamping code is written anywhere in
this codebase — the same "the gauge's own floor/ceiling does the work" discipline the shipped
`sp_cost_on_climax` requirement already relies on for `GaugeTrait`. All mutation and reads go
through `.base`, mirroring `record_climax()`'s existing `self._traits.climax_today.base += 1` —
never `.current`. That rule carries one invariant worth pinning: `CounterTrait.value` is
`(current + mod) * mult`, and `current` falls back to `base` only while no `"current"` key is
stored — so a single stray write to `.current` would freeze `.value` at that value and make every
later `.base` write invisible. Nothing in this codebase writes `.current` on any sexual trait today
(`grep` clean), and a regression test pins the invariant (no `"current"` key appears in raw
`pleasure` storage after rule mutations and decay, and `value == base` throughout).

**Construction from an imported baseline (`entity.db.sexual`).** The import contract is untouched
(Non-Goals): `entity.db.sexual["arousal"]` is still a level string. `_build_from_baseline()` reads
that string as before but, instead of writing it into an `arousal` `OrderedLevelTrait` (which no
longer exists as a writable slot — `_ORDERED_FIELDS` drops its `"arousal"` entry), resolves it to the
matching band's **floor** and constructs `pleasure` at that value:

```python
baseline_level = baseline.get("arousal", AROUSAL_LEVELS[0])
pleasure_floor = PLEASURE_CONFIG.floor_for_level(baseline_level)
self._traits.add("pleasure", trait_type="counter", base=pleasure_floor, min=0, max=100)
```

This preserves the shipped `sexual-state-handler` scenario "A fully-specified baseline is used
verbatim" (`entity.db.sexual = {"arousal": "微興奮", ...}` → `entity.sexual.arousal.level ==
"微興奮"`) **verbatim, with no requirement text change**: landing `pleasure` at band-floor (15 for
`微興奮`) guarantees the derived `arousal.level` reads back `"微興奮"`. The floor choice is arbitrary
among the band's valid values but must be *some* deterministic, documented choice, and floor is the
simplest (it is also what monster construction and the no-baseline default already effectively use,
since `AROUSAL_LEVELS[0]`'s floor is `0`).

A Monster's `build_monster_sexual_baseline()` and `_generic_default_baseline()` both still specify
`"arousal": AROUSAL_LEVELS[0]`, so both resolve to `pleasure = 0` — unchanged observable starting
state.

### D-3: The derived `arousal` view

```python
@property
def arousal(self) -> "_DerivedArousal":
    ordinal = PLEASURE_CONFIG.ordinal_for(self.pleasure.value)
    return _DerivedArousal(ordinal, AROUSAL_LEVELS)
```

`_DerivedArousal` is a small read-only class exposing exactly the surface `_snapshot()` in
`sexual_transitions.py` and every existing reader need: `.value` (int ordinal), `.levels` (the
`AROUSAL_LEVELS` tuple), `.level` (the string), and the five comparison dunders (`__eq__`, `__ge__`,
`__gt__`, `__le__`, `__lt__`), each resolving the other operand exactly as
`OrderedLevelTrait._ordinal_of` already does (trait/string/int). It has **no `.value` setter** —
direct assignment (`entity.sexual.arousal.value = ...`) now raises `AttributeError`, which is the
intended, loud failure mode for the twenty call sites this proposal migrates (see tasks.md) rather
than a silent no-op.

`_snapshot()` in `sexual_transitions.py` needs no change: it already only reads `.value` and
`.levels` off whatever `entity.sexual.arousal` returns.

### D-4: The `bounded_counter` `FIELD_KINDS` kind, and why it reports `"arousal"` as its changed field

`FIELD_KINDS["pleasure"] = "bounded_counter"` (new kind), `FIELD_KINDS["arousal"]` is removed. Its
`_apply_then()` branch:

```python
elif kind == "bounded_counter":
    trait = entity.sexual.pleasure
    before_arousal_ordinal = PLEASURE_CONFIG.ordinal_for(trait.value)   # live, pre-mutation
    if "delta" in then:
        trait.base += _resolve_delta(then["delta"], rng)
    else:
        trait.base = then["set"]
    after_arousal_ordinal = PLEASURE_CONFIG.ordinal_for(trait.value)    # live, post-mutation
    direction = _direction(before_arousal_ordinal, after_arousal_ordinal)
    field = "arousal"   # see below — deliberately not "pleasure"
```

**This is the one subtlety in the whole proposal that is easy to get wrong.** `wetness_follows_arousal`
(`{field_changed: arousal, direction: up}`, untouched by this proposal) is checked against
`context["_changed"].get("arousal")`. `_changed` is populated by the caller
(`apply_event()`'s per-pass loop) from `_apply_then()`'s returned `(field, direction)` tuple, keyed
literally by the returned `field` string. If the `bounded_counter` branch returned `"pleasure"` (the
rule's own `then.field`, matching every other kind's convention), `wetness_follows_arousal` would
never fire again — a silent, hard-to-notice regression, since nothing raises an error; wetness would
simply stop tracking arousal.

The fix is that `bounded_counter` is **the only `FIELD_KINDS` entry whose reported changed-field name
differs from its `then.field` key**: it writes `pleasure` but reports `arousal`, because what
`field_changed` listeners have always cared about is the *observable level* stepping, not the raw
number moving. The reported direction is computed from the arousal **ordinal** before/after (not
from the raw pleasure delta), so a pleasure change that stays within one band correctly reports no
change at all — matching design doc §1.4's own stated intent ("wetness tracks the visible arousal
step, not every point of the gauge") exactly.

The before/after ordinals are read **live**, immediately around the mutation — `PLEASURE_CONFIG.
ordinal_for(trait.value)` called once before and once after — rather than taking the "before" value
from `context["arousal"]` (the pass-start snapshot already available in scope). Reading the pass-start
snapshot would also work *today*, because `sexual.yaml`'s four `pleasure`-targeting rules are keyed to
mutually exclusive trigger events, so at most one can mutate `pleasure` within a single pass — but
that makes correctness depend on an invariant about the rule *table's contents* that this function has
no way to enforce or even observe. Reading live matches every other `_apply_then()` kind's own
convention (`ordered_level`'s branch, for comparison, reads `trait.value` live before and after its
own mutation) and removes the dependency on that external invariant entirely, at zero extra cost.

`_validate_rule_effect()`'s `bounded_counter` branch mirrors `ordered_level`'s: `{"field", "delta"}`
when `delta` is present, else `{"field", "set"}`; `set` must be an `int` in `[0, 100]` (raising
otherwise, matching every other kind's fail-closed-at-load-time discipline); `delta` reuses the
existing `_parse_delta`/`_resolve_delta` machinery unchanged (fixed or ascending range, signed
integers).

### D-5: Decay crosses exactly one band per configured interval

`decay_tick()`'s existing loop (`world/rules/sexual_state.py`) does, for each `DECAY_CONFIG` entry
save `climax_phase`: `floor = trait._ordinal_of(config["floor"]); trait.value = max(floor,
trait.value - 1)`. For `arousal` this directly wrote the (until now mutable) `OrderedLevelTrait`.
That write target no longer exists.

`DECAY_CONFIG`'s key is renamed `"arousal"` → `"pleasure"` (the field actually being decayed), and
gains a **third branch** in `decay_tick()`'s dispatch, alongside the existing `climax_phase` special
case and the unchanged generic branch (still used by `wetness`/`shame`, both still plain
`OrderedLevelTrait`s):

```python
if field == "climax_phase":
    _apply_climax_phase_set(entity, config["floor"])
elif field == "pleasure":
    current_band_floor = PLEASURE_CONFIG.floor_for(trait.value)
    trait.base = max(0, current_band_floor - 1)
else:
    floor = trait._ordinal_of(config["floor"])
    trait.value = max(floor, trait.value - 1)
```

(`decay_tick()` is a module-level function in `sexual_state.py`, same as `PLEASURE_CONFIG`'s own
module — no import needed for this call site, unlike the `sexual_transitions.py` one above.)

The rename has one collateral consumer inside `world/rules/clock.py` (a file the overview assigns to
the later `climax-settlement` proposal, but which B1 must leave working): `_has_settlement_work()`
iterates `DECAY_CONFIG` to decide whether a settlement quantum has work, reading
`getattr(sexual, field).level` — a property `CounterTrait` does not expose. B1 teaches it a
counter-aware branch: when the trait has no `.level`, the pleasure field counts as "not at rest"
whenever `trait.value != PLEASURE_CONFIG.floor_for_level(config["floor"])` (the `平靜` band floor,
`0`), and as at rest otherwise — mirroring the old arousal predicate `level != "平靜"`.

`current_band_floor - 1` lands one point below the current band's floor, guaranteeing the pleasure
value crosses into the next-lower band regardless of where within the current band it started —
reproducing "at most one level of decay" as an *observable arousal-level* effect, exactly matching
the shipped `sexual-state-handler` decay requirement's stated behaviour (that requirement's SHALL
text is field-name-agnostic — "at most one level of decay to each configured field" — and never names
`arousal` specifically, so no requirement text needs to change; see the `ADDED Requirements` in this
proposal's delta spec for the new pleasure-specific scenario). At the lowest band (`平靜`, floor 0),
`max(0, 0 - 1)` clamps at `0` — a no-op, matching the old code's `max(floor, value - 1)` clamp at the
vocabulary's own floor.

`DECAY_CONFIG["pleasure"]["floor"]` becomes unused for this branch (the band table supplies the
floor instead) and is kept only as `0` for documentation symmetry with the other entries; it is not
read by the new branch.

### D-6: Existing direct-write test call sites are migrated, not left to fail

Twenty-one call sites across nine test files write `entity.sexual.arousal.value = "<level>"` (or,
once, an integer ordinal) to arm a threshold condition for the test that follows. The full-suite
run additionally surfaces one `setattr(entity.sexual.arousal, "value", ...)` prime in
`test_action_pipeline_atomicity.py` and two before/after ordinal *read* assertions
(`test_sexual_event_self_arming.py`, `test_divine_mystery_gate.py`) whose deltas stay within one
band and therefore no longer move the derived ordinal. Since D-3 makes `.arousal` read-only, every
one of these must become `entity.sexual.pleasure.base = <band-floor-for-that-level>` instead (the
read sites become `pleasure` reads). The floor values, from D-1's table:
`平靜→0, 微興奮→15, 中等→35, 高度→60, 極限→85`. This is a mechanical, one-line-per-site
migration; tasks.md enumerates every file. None of these files are otherwise touched by this
proposal's production code, and none of the fixes conflict with `exposure-combat-modifier`'s (already
proposed) sole edit to `test_combat_modifiers.py`, which only *adds* new test methods rather than
editing the arousal-setting lines this proposal touches.

### D-7: The two no-create raw-storage readers must be taught to resolve pleasure, or they silently go stale

**Found by review, not by the original draft of this document — treated as blocking, not optional.**
Two existing production functions read `entity.sexual`'s persisted state **without materializing the
`SexualState` handler**, by reaching directly into the raw `TraitHandler` storage Attribute
(`entity.attributes.get("sexual_traits", ..., category="traits")`) and, when that is absent or
lacks the field, falling back to the frozen import-time baseline
(`entity.attributes.get("sexual", default=None)`):

- `world/rules/combat_modifiers.py::_stored_sexual_level()`, feeding
  `build_no_create_condition_context()`, which feeds `evaluate_combat_modifiers_no_create()` —
  consumed by `world/rules/action_preview.py` for skill-cast preflight/preview.
- `world/rules/status_query.py::_sexual_level()`, feeding `_sexual_condition_context()`, which feeds
  `build_status_read_model()` — the player-facing status panel, governed by the shipped
  `webclient-status-presentation` spec's "Sexual threshold appears only while matched" scenario
  ("the actor's canonical arousal state crosses the configured combat-modifier threshold → status
  contains the matched rule ID... and the entry disappears after canonical state no longer matches")
  and its "Unmaterialized sexual baseline remains unmaterialized" requirement (building status must
  **not** create or repair traits or materialize an uninitialized sexual baseline).

Both functions are hardcoded to look up the literal field name `"arousal"` inside the raw traits
mapping, expecting the `OrderedLevelTrait` shape (`raw.get("value")` a string ordinal or index,
`raw.get("levels")` the vocabulary tuple). Once this proposal lands, a materialized entity's raw
traits mapping no longer has an `"arousal"` key at all — `_build_from_baseline()` now creates
`"pleasure"` instead (D-2). Both functions would then fall through to the *baseline* branch, which
for an imported character still has a literal `"arousal"` string (the import contract is unchanged,
Non-Goals) — but that string is the character's **import-time snapshot**, frozen forever, never
updated as `pleasure` changes at runtime. For a non-imported entity with no baseline at all, the
fallback finds nothing and the field is silently omitted from the context entirely.

**Concretely, this means:** once any entity's `SexualState` has been materialized at all (which
happens the first time *anything* touches `entity.sexual` — extremely common), the skill-cast preview
panel and the player's own status display would both freeze the arousal-driven condition at whatever
level the character was imported at (or show nothing, for a character with no import baseline),
forever — never reflecting a single point of runtime `pleasure` change, and never matching what
`evaluate_combat_modifiers()` (the *live*, handler-based path, unaffected by this bug) reports for the
same entity in the same moment. This is a real, silent regression to two shipped, tested,
player-facing features, and it is not caught by anything in `pleasure-gauge/tasks.md`'s original
task list — neither file appeared anywhere in this proposal's original scope.

**The fix** teaches both functions a `field == "arousal"`-specific branch: look up `"pleasure"` (not
`"arousal"`) in the raw traits mapping, read its stored `base` (an int — a `CounterTrait`'s raw
`_data` has no `"value"` key at all; `.value` is a computed property, never persisted, confirmed
against Evennia's `CounterTrait.default_keys` and the base `Trait.__init__`/`validate_input` storage
contract), and convert it to an ordinal via `PLEASURE_CONFIG.ordinal_for(...)`, returning the same
`_StoredLevel`/`_LevelRef` wrapper type each file already uses for `climax_phase`. Two defensive
guards keep malformed storage from mis-resolving: the stored value is clamped into `[0, 100]` before
the ordinal lookup (harmless normally — `CounterTrait.base`'s own setter already clamps writes — but
it turns a corrupted out-of-range `base` into a determinable level instead of a
`PleasureConfigError`), and a `bool` base is rejected the same way every other strict parser in
these two modules rejects booleans (Python treats `True` as `int` 1). The outer
context key produced stays `"arousal"` (unchanged — `combat_modifiers.yaml`'s conditions still read
`field: arousal`); only the *inner* raw-storage field name and value-parsing logic changes for this
one field. The baseline-fallback branch (used only when the trait handler was never materialized at
all) is untouched — it still reads the baseline dict's `"arousal"` string exactly as before, which is
correct precisely because it only ever applies *before* materialization, matching "Unmaterialized
sexual baseline remains unmaterialized"'s own scope.

```python
def _stored_sexual_level(entity: Any, field: str) -> Any:
    """Read one stored sexual level without materializing the handler."""
    traits = entity.attributes.get("sexual_traits", default=None, category="traits")
    if field == "arousal":
        if isinstance(traits, Mapping) and "pleasure" in traits:
            raw = traits["pleasure"]
            base = raw.get("base") if isinstance(raw, Mapping) else None
            if isinstance(base, int) and not isinstance(base, bool):
                # Defensive: base writes are clamped by CounterTrait, so an
                # out-of-range stored value implies corrupted storage.
                base = min(100, max(0, base))
                return _StoredLevel(
                    PLEASURE_CONFIG.ordinal_for(base), AROUSAL_LEVELS
                )
            return None
        # traits materialized but pleasure not yet present, or traits absent entirely —
        # fall through to the baseline branch below, unchanged from today
    elif isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        # ... existing ordered_level-shaped parsing, unchanged, still used for climax_phase ...

    baseline = entity.attributes.get("sexual", default=None)
    if isinstance(baseline, Mapping) and isinstance(baseline.get(field), str):
        return baseline[field]
    return None
```

`status_query.py::_sexual_level()` gets the identical `field == "arousal"` branch (its surrounding
function is otherwise structured identically — the two files independently duplicate this logic
today, and this proposal preserves that existing duplication rather than introducing a new shared
module, which would expand this proposal's footprint beyond what fixing the actual bug requires).
Both files gain one new import: `PLEASURE_CONFIG` from `world.rules.sexual_state` — a plain,
already-loaded, process-wide frozen data object, not a call that creates or touches any entity's
state, so it does not compromise either function's no-create contract (see D-1's closing paragraph).

No circular import: `sexual_state.py` imports nothing from `combat_modifiers.py` or `status_query.py`
today, so this is a one-directional dependency addition.

## Risks / Trade-offs

[Risk] D-7 (the no-create raw-storage readers) was found only by an independent review reading
`combat_modifiers.py`/`status_query.py` and the shipped `webclient-status-presentation` spec directly,
not by this document's original drafting process, which stopped at "no edit to `combat_modifiers.yaml`,
`overwhelm.py`, `status_display.yaml`" (D-3's stated file list) without checking whether any *reader*
outside that list depended on the literal storage key name `"arousal"` rather than on
`SexualState.arousal`'s public surface. → Mitigation: D-7's fix is now first-class scope (tasks.md),
with dedicated delta-spec coverage against both `combat-modifier-table` and
`webclient-status-presentation`, and regression tests asserting the preview and status paths report
*live*, pleasure-driven arousal state on a materialized entity — not the frozen import-time baseline.

[Risk] The D-4 changed-field aliasing (`bounded_counter` reports `"arousal"`, not `"pleasure"`) is
non-obvious and is the single highest-value place for an implementation mistake to hide, because the
failure mode is silent (no exception; `wetness_follows_arousal` simply stops firing). → Mitigation:
tasks.md pins an explicit regression test asserting `wetness_follows_arousal` still fires from a
pleasure-driven arousal-level increase, and design.md documents the mechanism at the level of literal
code shape (not just prose) so an implementer cannot miss it.

[Risk] Band-floor construction (D-2) means an imported baseline's exact intra-band nuance is lost —
two characters both imported at `"微興奮"` always start at the identical `pleasure = 15`, never at
say `20` or `30`, even though both are equally valid `"微興奮"` readings. → Mitigation: accepted.
`CHARACTER_SCHEMA_V1` never carried more precision than the level string to begin with, so no
information is actually lost relative to the shipped import contract; this is a strictly additive
capability (finer runtime resolution), not a regression in import fidelity.

[Risk] Twenty test call sites are a real, if mechanical, migration cost concentrated in this one
proposal. → Mitigation: none needed beyond doing the work — deferring it would only move the failure
from "this proposal's test suite" to "whichever later proposal happens to run these tests next",
which is strictly worse for traceability. tasks.md treats this as first-class scope, not cleanup.

## Migration Plan

None required for persisted game state — this project has zero released users (`AGENTS.md`) and no
production database to migrate. The only "migration" is source-level: the twenty test call sites
(D-6) and the four rewritten rules (unchanged ids). Both are covered by tasks.md and are ordinary
code changes landed and tested in the same commit as the rest of this proposal, not a phased rollout.

## Open Questions

None outstanding. (An earlier draft of this document claimed "none" before D-7 was found by review —
that gap is now closed with a fully-specified fix, not deferred.) Every mechanism (band table shape,
construction, the changed-field alias, decay, and the two no-create readers) is fully specified above;
nothing is deferred to implementation-time judgment except the ordinary "how many lines does this
take" of the twenty-site test migration.

**Noted, not acted on:** `SexualState.__init__`'s short-circuit guard
(`required = {*_ORDERED_FIELDS, "climax_today"}; if required.issubset(self._traits.all()): return`)
is not extended to include `pleasure` or (in the sibling `sexual-counters` proposal) any of its eleven
new counters. This is harmless today — `_build_from_baseline()` adds every field, old and new, in one
atomic call, so first access always builds the complete set together and the guard's "already built"
sentinel stays accurate — but it is an unexamined coupling: a future proposal that ever constructs
fields conditionally or partially could silently reintroduce a real bug here. No action needed for
`pleasure-gauge` or `sexual-counters`; flagged for whichever future proposal first has reason to touch
this guard.
