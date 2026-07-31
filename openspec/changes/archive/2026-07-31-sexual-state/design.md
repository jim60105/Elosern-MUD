## Context

This is roadmap item #7 (design doc §11), depending on change 6 (`buffs-rulebook`) for
`world/rules/rulebook/schema.py`'s shared condition grammar (`Rule`, `load_rules()`,
`evaluate_condition()`) — a handoff change 6's own design doc D-1/D-2 wrote explicitly for a future
sexual rule table to consume rather than reinvent — and on change 4 (`import-contract`) for
`world/lore/sexual_vocab.py`'s six frozen ordered-level tuples and the `entity.db.sexual` raw
baseline storage convention its `loader.py` already writes to. No code exists yet for this change's
scope: `world/rules/` currently holds `traits.py` (change 3), `rulebook/schema.py`,
`buffs.py`/`combat_modifiers.py` and their YAML tables (change 6) — nothing named `sexual_state.py`.

**This change was split from a larger scope during review.** The first pass through this design also
transcribed `tmp/story_settings/variable_rule.md` into `rulebook/sexual.yaml` (~25 transition rules)
and their per-rule tests. That combined scope was flagged as too large for a one-working-day change,
and the coordinator split it: this change (7) builds the trait type, the handler, both baseline
construction paths, the climax-phase cycle guard, and the decay/reset callables — everything a rule
table needs to attach to, but no rule table itself. A follow-on change, **`sexual-transition-rules`
(7b, depending on this one)**, owns `rulebook/sexual.yaml`, `apply_event()`, and the per-rule tests.
**D-7 below — the `variable_rule.md` ambiguity and self-contradiction analysis — is preserved
verbatim from that first pass specifically for 7b's author to start from; it does not describe
anything this change builds.**

Two artifacts already point at this change before it exists. First, change 6's
`combat_modifiers.yaml` carries two rules — `high_arousal_agility_accuracy_penalty` and
`climax_in_progress_locks_actions` — that read `context["arousal"]`/`context["climax_phase"]` only
when `entity.sexual` is not the change-3 placeholder `None`; a dedicated test,
`test_combat_modifiers_self_arming.py::test_high_arousal_rule_fires_once_sexual_state_exists`,
guarded by `pytest.importorskip("world.rules.sexual_state")`, reports **skipped** until this module
exists and `entity.sexual` is real. **Neither of these needs a single transition rule to exist** —
only a live, correctly-comparable `entity.sexual.arousal`/`.climax_phase` — which is exactly why this
narrower scope is sufficient to flip that test on its own, ahead of change 7b. Second,
`tmp/story_settings/variable_rule.md` is the only behavioral specification for how each field
transitions; this change does not transcribe it (7b does), but D-7 carries forward the analysis of
where it is ambiguous or self-contradictory, since that analysis was already done and should not be
redone from scratch.

Design doc §6.4 gives the field model exactly: six ordered levels (`arousal`, `wetness`, `shame`,
`exposure`, `climax_phase`, and a `sensitivity` dict keyed by body part), a daily counter
(`climax_today`), and two flags (`virgin`, one-way; `experience_types`, append-only). Design doc §4
states plainly that Evennia 6.1.0 ships no ordered/enum trait type — confirmed during change 1's
contrib-matrix verification — so the `Trait` subclass here is authored from scratch, with
`CounterTrait`'s numeric-bucket-to-label `descs` mapping as the closest built-in precedent, not
something to subclass directly.

## Goals / Non-Goals

**Goals:**
- `world/rules/sexual_state.py::OrderedLevelTrait` — a from-scratch `Trait` subclass storing an
  ordinal index into one of change 4's six frozen vocabulary tuples, with rich comparison
  (`__eq__`/`__ge__`/`__gt__`/etc.) that accepts a raw Chinese level string, another
  `OrderedLevelTrait`, or a bare ordinal — registered at `world.rules.sexual_state.OrderedLevelTrait`
  in `settings.TRAIT_CLASS_PATHS`.
- `SexualState`, mounted as `entity.sexual` (replacing change 3's `None` placeholder), with three
  distinct construction paths: from `entity.db.sexual` (change 4's raw imported baseline) for
  `PlayerCharacter`/`NPC`; a monster-default baseline (普通 sensitivity, `shame` permanently clamped
  to 無) for `Monster` entities, which are never routed through change 4's JSON import pipeline; and
  a generic floor-level default for any other entity constructed with no raw baseline at all.
- A clean, public property/method surface on `SexualState` (`.arousal`, `.wetness`, `.shame`,
  `.exposure`, `.climax_phase`, `.climax_today`, `.virgin`, `.experience_types`, `.sensitivity`) —
  this is the exact seam change 7b's future rule table and change 9's combat-modifier read both
  attach to; nothing outside this change should ever need to reach into `SexualState`'s internal
  `TraitHandler` directly.
- `_apply_climax_phase_set()` — the sole permitted write path for `climax_phase`, enforcing that it
  moves only along its valid cycle (未達→接近→進行中→餘韻→未達, plus 餘韻→接近), not treated as a
  plain intensity ladder.
- `decay_tick(entity, elapsed_seconds)` and `reset_daily_counters(entity)`, exposed as plain
  callables for change 11 (`world-clock`) to invoke at its own chosen point in the fixed settlement
  order — no ordering relative to trait regen or buff ticks is assumed or hardcoded here.
- A preserved, documented answer for every place `tmp/story_settings/variable_rule.md` is ambiguous
  or self-contradictory (D-7), carried forward specifically for change 7b's author rather than
  re-derived by them from scratch.

**Non-Goals:**
- **No `rulebook/sexual.yaml`, no transition rules, no `apply_event()`, and no per-rule tests** —
  change 7b's entire scope. This change builds the target surface a rule table attaches to; it
  authors no rule.
- No `ActionResolver`, targeting, or effect-resolution pipeline (change 8) — change 7b's future
  `apply_event()` is the seam change 8's step 5 ("effect resolution, driven by rulebook") is expected
  to call; this change does not decide which player commands fire which events, because no events
  exist here at all.
- No combat resolution, to-hit formula, or damage math (change 9) — change 6's
  `evaluate_combat_modifiers()` already reads `entity.sexual.arousal`/`.climax_phase` today; this
  change only has to make that read live, not build anything in `combat_modifiers.py` itself.
- No world clock, scheduled events, or settlement ordering (change 11) — `decay_tick()`/
  `reset_daily_counters()` are plain callables invokable directly in a test with no clock present,
  exactly mirroring change 6's `tick_buffs(entity)` seam.
- No new buff definitions in `buffs.yaml` and no edit to `buffs.py`'s `_apply_rate_modifier()`. Hard
  requirement 8 asks this change to "define which sexual fields those three levers apply to" — this
  change documents the target-field naming convention a future buff would use and reads
  `entity.buffs` for any such buff at decay/apply time, but authors no concrete buff instance. The
  race-specific behaviors `variable_rule.md` describes (elf rapid post-climax recovery, elf
  long-term arousal floor, magic-induced temporary sensitivity spikes, elf rapid re-entry into
  climax from 餘韻) are exactly what such a future buff would model — building them belongs to
  change 6's `buffs.yaml` (a future addition to it, authored whenever a concrete skill/passive needs
  one), not to this change or to change 7b's rule table (see D-7).
- No SP/exhaustion coupling (`variable_rule.md`'s "climax consumes 20-30 SP" / "虛脫" status below a
  SP threshold) — that is a resource-deduction concern belonging to change 8's `ActionResolver`
  pipeline step 6, which reads `entity.traits`, not `entity.sexual`. Flagged as an integration point
  for change 8's author, not built here.
- No exhaustive per-monster-species sexual-baseline table. Design doc §6.4 says "most monsters" sit
  at the flat default this change builds; a bestiary field carrying per-species overrides would
  require an edit to change 2's `MonsterTier`/bestiary registries, which this change does not make.
- No narrative-only fields. `variable_rule.md`'s `身體感受`, `興奮要素`, `被注視感受`, `最後性活動`,
  `乳房.整體狀態`, `私處.外觀`, and the top-level `基本資訊.狀態` enum are all free-text or derived
  narrative material with no ordered level, counter, or flag shape — they do not appear in design
  doc §6.4's field model at all, and belong to the Narrator (change 18) and `PersonaStore`, not
  `SexualState` (see D-7).
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with
  zero users.

## Decisions

### D-1. `OrderedLevelTrait`: an ordinal-backed `Trait` subclass with a comparison contract that
satisfies change 6's `evaluate_condition()` for free.

**What `CounterTrait` gave and what it didn't.** `CounterTrait`'s `descs` mapping (numeric bucket →
label, e.g. `0-25: "weak"`) is the closest built-in precedent design doc §4 names — it proves Evennia
already has a pattern for "a stored number that displays as a human label." What it does not give is
a *bijective*, *comparable* enum: `descs` buckets a continuous numeric range into coarse labels for
*display*, but the six vocabularies here (`AROUSAL_LEVELS` etc.) are the entire value space — there
is no numeric range underneath, only five or four discrete named rungs, and every consumer (change
7b's future rules, change 6's `combat_modifiers.yaml`) needs to compare *by rung*, not by an
underlying number a label happens to be drawn over.

**Decision**: `OrderedLevelTrait` stores a plain integer ordinal (0-indexed into whichever tuple it
was constructed against) as its `base`/`value`, mirroring `CounterTrait`'s bounded-integer storage
exactly — min `0`, max `len(levels) - 1` — but adds:

```python
# world/rules/sexual_state.py
class OrderedLevelTrait(Trait):
    """From-scratch ordered/enum Trait -- Evennia 6.1.0 ships none (design doc
    S4, confirmed change 1). Storage is a plain integer ordinal into a fixed
    tuple of Chinese level names (world.lore.sexual_vocab), bounded exactly
    like CounterTrait's own min/max clamp. What CounterTrait's `descs` does
    NOT give -- comparability by rung, not by an underlying numeric range --
    is this class's entire reason to exist as a new subclass rather than a
    CounterTrait instance with a `descs` table bolted on.
    """
    trait_type = "ordered_level"

    def __init__(self, *args, levels: tuple[str, ...], **kwargs):
        # `levels` is one of change 4's frozen tuples, passed at
        # TraitHandler.add()-time, never redefined here.
        self.levels = levels
        super().__init__(*args, **kwargs)  # base=0, min=0, max=len(levels)-1

    @property
    def level(self) -> str:
        """The current Chinese label -- the only thing narration/persona
        prompts or a `look`-style status display should ever read."""
        return self.levels[self.value]

    def _ordinal_of(self, other) -> int:
        if isinstance(other, OrderedLevelTrait):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)   # raises ValueError on a typo'd
                                                 # level name -- loud, not silent
        return int(other)                      # bare ordinal

    def __eq__(self, other):
        return self.value == self._ordinal_of(other)

    def __ge__(self, other):
        return self.value >= self._ordinal_of(other)

    def __gt__(self, other):
        return self.value > self._ordinal_of(other)

    def __le__(self, other):
        return self.value <= self._ordinal_of(other)

    def __lt__(self, other):
        return self.value < self._ordinal_of(other)
```

**Why this satisfies change 6's contract with zero code on change 6's side.** Change 6's design doc
D-2 states `evaluate_condition()`'s `gte` "calls context's own comparison helper if one is given, or
falls back to Python `>=`," and explicitly leaves it to "change 7 ... to hand `evaluate_condition()`
a context where `context["arousal"]` is already an orderable value, not a bare Chinese string." By
putting `context["arousal"] = entity.sexual.arousal` (the live `OrderedLevelTrait` instance, not
`.level`), `evaluate_condition({"field": "arousal", "gte": "高度"}, context)` reduces to Python
evaluating `context["arousal"] >= "高度"`, which resolves through `OrderedLevelTrait.__ge__` exactly
as documented. This is the concrete fulfillment of the risk change 6's design doc flagged as
"[Risk] change 7 might get wrong by passing the raw Chinese string through unordered" — it is not
wrong, because the object handed into the context *is* the comparable value, never the bare string.
Change 6's own `combat_modifiers.py::_build_context()` is exactly this call site, and needs no edit
to benefit from it.

**Registration**: added to `settings.TRAIT_CLASS_PATHS` (wherever change 1's project skeleton put
it, likely `server/conf/settings.py`) as `world.rules.sexual_state.OrderedLevelTrait` — the identical
mechanism design doc §4 names for the contrib's own `RageTrait` example (`world.traits.RageTrait`).
Flagged for implementer verification against the installed Evennia 6.1.0
`evennia.contrib.rpg.traits` source (exact `Trait.__init__` signature, `min`/`max` keyword names),
consistent with changes 1–6's established verify-before-trusting discipline.

**Alternative considered**: subclassing `CounterTrait` directly and layering ordinal→label lookup on
top via its own `descs`. Rejected — `CounterTrait`'s `descs` is a *display* concern layered over a
numeric value that can otherwise move by arbitrary deltas; treating a 5-rung enum as "a counter that
happens to have a `descs` table" would let a delta land between two labeled buckets with an undefined
label, and would give every ordered-level field an unbounded-looking numeric identity (`value: 3`)
where the domain model wants exactly one of five named states, never a sixth. A purpose-built
subclass with `levels` as its defining parameter states this domain constraint directly instead of
gluing a display convention onto a numeric-range primitive that does not otherwise fit.

### D-2. `SexualState` mounts a second, private `TraitHandler` — distinct from `entity.traits` — and
exposes every field through a clean public property surface.

```python
class SexualState:
    """Mounted as entity.sexual (typeclasses/entities.py), replacing change
    3's None placeholder. entity.db.sexual stays the raw imported baseline
    (change 4); this class is the live handler built from it, never confused
    with the bare name -- the exact convention corrected across changes 4/5
    that must not regress here (hard requirement 3).

    Public surface -- the ONLY thing change 7b's future rule table and
    change 9's combat-modifier read are expected to touch. Nothing outside
    this class should ever reach into `self._traits` directly."""

    def __init__(self, entity):
        self._entity = entity
        self._traits = TraitHandler(entity, db_attribute_key="sexual_traits")
        baseline = entity.db.sexual
        if baseline is not None:
            self._build_from_baseline(baseline)                  # character path
        elif isinstance(entity, Monster):
            self._build_from_baseline(build_monster_sexual_baseline())
            self._traits.shame.min = self._traits.shame.max = 0   # D-5's clamp
        else:
            self._build_from_baseline(_generic_default_baseline())  # e.g. a
                                                                       # hand-spawned
                                                                       # NPC never
                                                                       # routed through
                                                                       # change 4

    # --- public field surface ---
    @property
    def arousal(self) -> OrderedLevelTrait: return self._traits.arousal

    @property
    def wetness(self) -> OrderedLevelTrait: return self._traits.wetness

    @property
    def shame(self) -> OrderedLevelTrait: return self._traits.shame

    @property
    def exposure(self) -> OrderedLevelTrait: return self._traits.exposure

    @property
    def climax_phase(self) -> OrderedLevelTrait: return self._traits.climax_phase

    @property
    def climax_today(self) -> int: return self._traits.climax_today.value

    def record_climax(self) -> None:
        """Increment climax_today by one. The only legal write path for this
        counter — change 7b's rule table has no other way to satisfy
        variable_rule.md's 「每次達到高潮時+1」 without reaching into
        self._traits, which consumers are forbidden from touching."""
        self._traits.climax_today.value += 1

    @property
    def sensitivity(self) -> "_SensitivityProxy": return self._sensitivity  # D-3

    @property
    def virgin(self) -> bool: return self._entity.attributes.get(
        "virgin", default=True, category="sexual_state")

    @virgin.setter
    def virgin(self, value: bool) -> None:
        if self.virgin is False:
            return    # irreversible through the public SexualState API -- once
                       # false, later setter calls are no-ops, never exceptions
        self._entity.attributes.add("virgin", bool(value), category="sexual_state")

    @property
    def experience_types(self) -> frozenset[str]: return self._entity.attributes.get(
        "experience_types", default=frozenset(), category="sexual_state")

    def add_experience_type(self, key: str) -> None:
        """The only mutator for experience_types -- always a union, never a
        replacement or a removal."""
        self._entity.attributes.add(
            "experience_types", self.experience_types | {key}, category="sexual_state")
```

`self._traits` is a **second** `TraitHandler` instance bound to its own attribute
(`entity.db.sexual_traits`), never the same handler as `entity.traits` — the eight combat/vital
trait keys (D-7 of change 3) and the five ordered sexual fields are different domains that happen to
share the same underlying contrib mechanism; keeping them on separate handlers means a future
`entity.traits.hp` regen bug can never accidentally touch `entity.sexual.arousal`'s storage, and vice
versa. `arousal`/`wetness`/`shame`/`exposure`/`climax_phase` are added at construction as
`ordered_level` traits, each with its own `levels` tuple from `world.lore.sexual_vocab`;
`sensitivity` is not one key but a lazily-populated sub-collection (D-3); `climax_today` is a plain
`CounterTrait` (min 0, no max); `virgin` (`bool`) and `experience_types` (`frozenset[str]`) are
**not** `TraitHandler` entries at all — they have no ordinal, gauge, or counter shape, and are stored
directly as `entity.attributes` under the `sexual_state` category. Their one-way/append-only
guarantees apply to `SexualState`'s sanctioned public mutators, the only route deterministic rule
code may use; Evennia's low-level public attribute handler is outside this API contract.

**Why the public property surface matters for the split.** Since change 7b is a separate change with
its own author, `SexualState`'s public contract (`.arousal`, `.wetness`, ..., `.virgin`,
`add_experience_type()`) is the entire interface that author needs to read — they should never need
to know `self._traits` exists, what `TraitHandler` is mounted underneath, or which attribute category
backs `virgin`. Every property above returns exactly what change 6's `combat_modifiers.py` already
expects (`sexual.arousal`, `sexual.climax_phase` — bare attributes, not `.level`), so no code in
`combat_modifiers.py` needs to change once this handler exists.

**Alternative considered**: reusing `entity.traits` (the same `TraitHandler` instance change 3
mounts) for the ordered-level fields too, since it is already present on every `LivingEntity`.
Rejected — `entity.traits`' eight keys are combat-facing base values with a documented,
skill-multiplier-free boundary (change 3 D-7); mixing five unrelated ordered-level keys into that
same namespace risks a future combat-facing consumer iterating `entity.traits.all()` and tripping
over `arousal`, or a future sexual-state consumer accidentally reading `entity.traits.hp` through
the wrong handler. Two handlers, two attribute keys, is the same isolation discipline change 6's D-4
already used when it mounted `entity.buffs` as its own handler rather than folding buff state into
`entity.traits`.

### D-3. `sensitivity` is a lazy dict-of-parts wrapper over the same private `TraitHandler`, not a
bespoke dict.

Design doc §6.4 types `sensitivity` as `dict[part, 普通 → 高 → 極高 → 敏感異常]` — an open,
narratively-driven key set (body-part names are never enumerated anywhere in `variable_rule.md` or
the design doc). `SexualState.sensitivity` is a thin proxy, not a plain Python `dict`:

```python
class _SensitivityProxy:
    """entity.sexual.sensitivity['乳房'] -- lazily creates an OrderedLevelTrait
    at SENSITIVITY_LEVELS[0] (普通) the first time an unseen part is read,
    since neither variable_rule.md nor the design doc enumerates the full
    set of body parts up front. Explicitly imported parts (from
    entity.db.sexual['sensitivity'], change 4's raw baseline) are seeded at
    construction; any part accessed afterward that was never seeded defaults
    to 普通 -- this is the one mechanism that gives monsters '普通 sensitivity'
    for free (D-5) without a separate code path."""

    def __init__(self, traits: TraitHandler, entity):
        self._traits = traits
        self._entity = entity

    def __getitem__(self, part: str) -> OrderedLevelTrait:
        key = f"sensitivity__{part}"
        if key not in self._traits.all():
            self._traits.add(key, trait_type="ordered_level", levels=SENSITIVITY_LEVELS)
        return getattr(self._traits, key)

    def __setitem__(self, part: str, level: str) -> None:
        self[part].value = self[part]._ordinal_of(level)

    def items(self):
        return {
            key.removeprefix("sensitivity__"): trait
            for key, trait in self._traits.all().items()
            if key.startswith("sensitivity__")
        }.items()
```

Storing sensitivity keys as `sensitivity__<part>` entries on the same private `TraitHandler` (rather
than a second handler, or a bespoke dict on `entity.db`) means a future rule targeting `sensitivity`
(change 7b's `sensitivity_up_on_frequent_stimulation`, per D-7's carried-forward analysis) is exactly
as testable and exactly as bound-clampable-by-a-future-buff as any other ordered-level field — no
special-cased storage for the one field that happens to be dict-shaped.

**Alternative considered**: a plain `dict[str, str]` of raw level strings, converted to/from
`OrderedLevelTrait` only at comparison time. Rejected — this would mean `sensitivity` values are
*not* real `OrderedLevelTrait` instances at rest, so a future buff wanting to clamp
`sensitivity['乳房']`'s bounds (design doc's "magic 影響可暫時提升至敏感異常" — hard requirement 8's
"clamped bounds" lever) would have nothing to clamp; keeping every sensitivity entry a first-class
`OrderedLevelTrait` on the private handler gives that future buff the same clamp mechanism every
other field already has.

### D-4. `climax_phase` is a cyclic field, not a monotonic ladder — valid transitions are enforced by
one guarded function, not the condition grammar.

`CLIMAX_PHASE_LEVELS = ("未達", "接近", "進行中", "餘韻")` is ordered for `gte`/`equals` comparison
purposes (combat_modifiers.yaml's `climax_phase, equals: 進行中` needs exactly this), but the *valid
transition graph* is a cycle (`未達→接近→進行中→餘韻→未達`), not "higher is always further along" —
`餘韻`'s ordinal is the highest in the tuple, yet the correct next transition from `餘韻` is back down
to `未達` (via decay) or, per `variable_rule.md`'s elf-specific note (D-7), directly back up to
`接近`. This change's `decay_tick()` is the first real caller of this guard (afterglow decay,
`餘韻→未達`); change 7b's future rules are expected to route every `climax_phase` mutation through
the same function rather than writing the trait directly, since `then` is opaque to `schema.py`
anyway and any such interpretation belongs to this module:

```python
_VALID_CLIMAX_TRANSITIONS = {
    "未達": {"接近"},
    "接近": {"進行中", "未達"},   # 未達: arousal can fall away before climax
    "進行中": {"餘韻"},
    "餘韻": {"未達", "接近"},      # 未達: normal afterglow decay;
                                    # 接近: elf-style rapid re-arousal (D-7) --
                                    # this change permits the transition edge;
                                    # nothing in this change's own scope drives
                                    # it there except decay, which only ever
                                    # targets 未達
}

def _apply_climax_phase_set(entity, target_level: str) -> str | None:
    current = entity.sexual.climax_phase.level
    if target_level not in _VALID_CLIMAX_TRANSITIONS.get(current, set()):
        return None   # no-op: e.g. an attempt to set 進行中 -> 接近 directly
                        # does not silently regress the phase
    entity.sexual._traits.climax_phase.value = CLIMAX_PHASE_LEVELS.index(target_level)
    return "cycle"
```

This is the single enforcement point for every future `climax_phase` writer, including change 7b's
rule table once it exists — no per-caller special-casing is duplicated.

### D-5. Monster baselines: 普通 sensitivity comes free from D-3's lazy default; `shame` is the one
field this change clamps explicitly.

```python
def build_monster_sexual_baseline() -> dict:
    """Design doc S6.4: 'most monsters at 普通 sensitivity with shame clamped
    to 無.' Flat default -- no MonsterTier-keyed variation exists in change
    2's bestiary today, and adding one would require a change-2 edit this
    change does not make (Non-Goals)."""
    return {
        "arousal": AROUSAL_LEVELS[0], "wetness": WETNESS_LEVELS[0],
        "shame": SHAME_LEVELS[0], "exposure": EXPOSURE_LEVELS[0],
        "climax_phase": CLIMAX_PHASE_LEVELS[0],
        "sensitivity": {}, "virgin": True, "experience_types": frozenset(),
    }
```

"普通 sensitivity" needs no monster-specific code at all — D-3's `_SensitivityProxy` already defaults
every unseen body part to `SENSITIVITY_LEVELS[0]` (普通) for *any* entity, character or monster
alike, since neither `variable_rule.md` nor the design doc enumerates body parts up front. The one
piece that genuinely is monster-specific is the `shame` clamp: `SexualState.__init__`, when building
from the monster-default baseline (only that path, never the character path), sets `shame`'s bounds
to `(0, 0)` via the private `TraitHandler`'s own min/max-setting API (exact call shape flagged for
implementer verification, consistent with changes 1–6) — `shame` is permanently pinned at `無`
because its own range has collapsed to one point, not because some rule refuses to fire (there are no
rules in this change's scope). A test asserts that even a direct attempt to raise a monster's `shame`
(bypassing any future rule entirely, e.g. by attempting `entity.sexual._traits.shame.value += 1` in a
test) leaves it clamped at `0`. Every other field (`arousal`, `wetness`, `exposure`, `climax_phase`)
keeps its full, unclamped range — a monster can still be aroused, wet, exposed, or mid-climax; it
simply cannot feel shame.

**Construction dispatch, generalized beyond "Monster vs. everything else":**

```python
if baseline is not None:                       # entity.db.sexual populated
    self._build_from_baseline(baseline)         # change 4's import path
elif isinstance(entity, Monster):
    self._build_from_baseline(build_monster_sexual_baseline())
    self._traits.shame.min = self._traits.shame.max = 0   # the one clamp
else:
    self._build_from_baseline(_generic_default_baseline())  # e.g. a
                                                              # hand-spawned NPC
                                                              # never routed
                                                              # through change 4;
                                                              # floor for every
                                                              # field, no clamp
```

Dispatching on "is `entity.db.sexual` populated," not strictly "is this a `Monster`," matters because
nothing prevents a future change from spawning an `NPC` outside the import pipeline (a prototype-spawned
generic NPC, per design doc §7.2's `spawner.spawn()`); such an entity should default sensibly rather
than crash on a missing baseline, but it is not a monster and must not get the shame clamp.

### D-6. `decay_tick()`/`reset_daily_counters()`: plain callables, decay expressed as small
per-field configuration rather than a rule table.

Decay is clock-triggered, not condition-triggered — the same reasoning that keeps change 6's
`buffs.yaml` out of a `when`/`then` shape applies here: "a long time with no stimulus" is not an
event `apply_event()` receives, it is the absence of one, measured by elapsed clock time. **Decision**:
a small `DECAY_CONFIG` mapping, not a YAML rule table, read by one plain callable:

```python
DECAY_CONFIG = {
    "arousal": {"interval_seconds": 1800, "floor": "平靜"},   # variable_rule.md:
    "wetness": {"interval_seconds": 900, "floor": "乾燥"},     # "長期無刺激可能降低
    "shame": {"interval_seconds": 1800, "floor": "無"},        # 1級" / "未受刺激時
    "climax_phase": {"interval_seconds": 300,                  # 逐漸降低" / "獨自
                      "floor": "未達", "only_from": "餘韻"},   # 在私密場所時緩慢
                                                                 # 降低" -- see D-7
                                                                 # for the race-
                                                                 # specific asides
                                                                 # this table
                                                                 # deliberately
                                                                 # excludes
}

def decay_tick(entity, elapsed_seconds: int) -> None:
    """Invokable directly in a test, no WorldClock present -- mirrors change
    6's tick_buffs(entity) seam exactly. Accumulates elapsed_seconds per
    configured field in entity.attributes (category "sexual_state"); when a
    field's accumulator crosses its configured interval, decrements that
    field by one level toward its floor, resetting the accumulator.
    climax_phase's decrement (afterglow, 餘韻 -> 未達 only) routes through
    _apply_climax_phase_set() (D-4) -- this function never writes
    climax_phase's value directly."""
    ...

def reset_daily_counters(entity) -> None:
    """Sets climax_today to 0. No other field changes. Change 11 is expected
    to call this once per in-game day rollover, per design doc S6.5's
    'daily resets (climax_today)' settlement step -- this function invents
    no ordering relative to any other settlement step."""
    entity.sexual._traits.climax_today.value = 0
```

`sensitivity` and `exposure` have no natural decay per `variable_rule.md` (sensitivity only rises,
via stimulation or a future magic buff; exposure only changes via clothing events) and are therefore
absent from `DECAY_CONFIG` — not an oversight, a direct transcription of the source's own asymmetry.

**Buff-lever seam, documented but not filled.** Hard requirement 8 asks this change to "define which
sexual fields those three levers apply to" without authoring a buff. `decay_tick()` is the one
function where a future buff's `decay` lever would apply (skipping or slowing a field's interval
accumulation) and where a future buff's `bounds` lever would apply (a temporarily raised floor, e.g.
elf sensitivity rarely dropping below 微興奮). Neither is implemented here: `decay_tick()` documents,
in its own docstring, the target-field naming convention such a buff would need
(`field key` = one of `DECAY_CONFIG`'s keys, or a `sensitivity__<part>` key), but reads no buff state
today, since no concrete buff exists yet in `buffs.yaml` targeting a sexual field. See D-7 for exactly
which `variable_rule.md` behaviors this seam is for.

### D-7. `variable_rule.md`'s ambiguities and self-contradiction — **carried forward for change 7b's
author**, not re-derived by them from scratch.

This section is preserved from the original, larger-scoped pass through this design specifically
because the coordinator asked that this analysis not be lost in the scope split. **Nothing in this
section describes something this change (7) builds** — it exists here as the starting point for
whoever writes change 7b's `design.md` and `rulebook/sexual.yaml`.

**Self-contradiction (resolved): the virginity trigger.** §性狀態.處女 states the "唯一更新條件"
(sole update condition) is "首次**同種異性**陰道插入" (first *same-species, opposite-sex*
penetration), but §性狀態.性經驗類型's own 陰道性交 entry says simply "首次被插入後添加（同時處女變
false）" (added after first penetration — full stop — simultaneously flips virgin to false), with no
species/gender qualifier at all. These cannot both be the literal, exact trigger: either virginity
requires a same-species-opposite-sex partner specifically, or any first penetration counts and the
`性經驗類型` section's plainer wording is the accurate one. **Recommended resolution, carried
forward**: use the unqualified trigger — `first_vaginal_penetration`, any partner — for three
reasons: (1) design doc §6.4 itself gives the worked example as `event: first_vaginal_penetration`
with no species/gender qualifier; (2) `異種性愛` (interspecies) is its own, separate
`experience_types` entry triggered by a *different* event (`sexual_activity_with_nonhuman`), which
would be structurally redundant with a species-qualified virginity trigger — the vocabulary already
has a dedicated place for "this was with a non-human partner," so virginity does not need to encode
species a second time; (3) the narrower reading would leave virginity never flipping at all for an
interspecies or a same-sex first encounter, which contradicts `性經驗類型`'s own unconditional "同時
處女變 false." Change 7b's `virginity_once` and `experience_vaginal_added` rules should therefore
share the identical `when: { event: first_vaginal_penetration }` clause. This change's own
`SexualState.virgin` setter (D-2) is deliberately event-agnostic — it just enforces one-way
irreversibility — so this resolution costs 7b nothing structural, only the choice of which single
event name to wire both rules to.

**Ambiguity (resolved): what "達臨界點" (reaching the critical point) means for 接近→進行中.**
`variable_rule.md` never defines this numerically or behaviorally — no duration, no roll, no
secondary threshold. **Recommended resolution, carried forward**: interpret it as "stimulus continues
while already at 接近" — a rule with `when: { field: climax_phase, equals: 接近, event:
stimulus_applied }`. This is the smallest reading consistent with the surrounding prose (which
otherwise only ever gates transitions on stimulus events or field thresholds, never on elapsed
real-time within a single event) and requires no new condition kind. Flagged explicitly as an
assumption, not a fact `variable_rule.md` states.

**Ambiguity (resolved): "濕潤程度至少提升1級" — "at least" one level.** The word "至少" (at least)
suggests wetness could rise by more than one level per arousal increase under some circumstances
`variable_rule.md` never specifies. **Recommended resolution, carried forward**: a baseline rule
(arousal rising → wetness `+1`) plus a separate, faster rule (direct stimulus → wetness `+1..+2`)
firing independently when direct stimulus is also present. Two rules, not one rule with an unbounded
delta, keeps each individually testable and matches the text's own separation of "喚起提升時" (arousal
rises) from "接受直接刺激時" (receiving direct stimulus) as two distinct triggers.

**Explicitly out of scope for both this change and change 7b's rule table: every race-specific
aside.** `variable_rule.md` repeatedly qualifies a rule with "因精靈體質" / "精靈族天生" / "精靈族具備
多重高潮體質" (elf constitution / elves are innately.../elves have a multi-orgasm constitution) —
rapid post-climax arousal recovery, a floor that rarely drops below 微興奮, innately elevated
sensitivity, and rapid re-entry into climax from 餘韻. **None of these should become rows in change
7b's `sexual.yaml`**: the table should stay species-agnostic (design doc §6.4 never scopes any field
to one race), and every one of these asides is expressible as a future buff modifying rate-of-change,
clamped bounds, or decay rate on a specific entity — exactly hard requirement 8's three levers, and
exactly the seam this change documents (D-6, Non-Goals) but does not fill. Building an "elf
sensitivity" or "elf rapid recovery" buff is **change 6's `buffs.yaml`'s** job (a future addition to
it), authored whenever a concrete skill/passive needs one — not this change's, and not change 7b's
rule table's, even though 7b's rules are the eventual trigger for such a buff's effect.

**Explicitly out of scope for both this change and change 7b: every purely descriptive field.**
`身體感受`, `興奮要素`, `被注視感受`, `乳房.整體狀態`, `私處.外觀`, and `最後性活動` are all free-text
narrative fields with no ordered levels, counters, or flags — they do not appear anywhere in design
doc §6.4's field model. These are prose-generation material for the Narrator (change 18) or
`PersonaStore`-adjacent storage, not `SexualState` fields; `basic_info.狀態` (a top-level
正常/性興奮/戰鬥中/... status enum in `variable_rule.md`) is likewise not part of §6.4's model and
should not be built by 7b either — it looks like a derived narrative label (combining combat state,
rest state, and sexual state) rather than a new mechanical field anyone in this design's chain owns.

### D-8. Flipping change 6's self-arming test: the three things that must all be true, none of which
require a transition rule.

`test_combat_modifiers_self_arming.py::test_high_arousal_rule_fires_once_sexual_state_exists` is
guarded by `pytest.importorskip("world.rules.sexual_state")` and asserts, against a *real*
`entity.sexual` at or above `高度` arousal, that `evaluate_combat_modifiers()` returns
`high_arousal_agility_accuracy_penalty`'s bundle. Three things this change delivers must all hold for
it to flip from skipped to passed — **notably, none of them is "a transition rule fired"**:

1. `world.rules.sexual_state` must exist and import cleanly (trivially true once this change lands).
2. `entity.sexual` must be a live object, not `None` — requires the `typeclasses/entities.py` mount
   edit (D-2) replacing change 3's placeholder.
3. `entity.sexual.arousal >= "高度"` must evaluate correctly through Python's own `>=` operator with
   no special-casing on change 6's side — requires D-1's `OrderedLevelTrait.__ge__` contract to hold
   exactly as documented. The test constructs the entity with `arousal` set directly (via the
   trait's own `.value` setter, not via any rule), since no rule exists in this change's scope to
   drive it there narratively.

A verification task runs this specific test in isolation both before (skipped) and after
(passed) the full change lands, mirroring change 6's own task 6.5 discipline for the identical test
in its pre-change-7 state.

## Risks / Trade-offs

- **[Risk] Splitting the rule table into change 7b means this change ships a handler with no
  behavior a player can actually trigger yet** — `entity.sexual` exists and decays on its own, but
  nothing narrates a stimulus into it until 7b lands. → Accepted: this is the direct, intended
  consequence of the scope split, and the self-arming test flip (D-8) — the concrete, checkable
  proof this change's slice is complete — needs none of that behavior to exist.
- **[Risk] `_apply_climax_phase_set()` (D-4) is bespoke logic outside the shared `when`/`then`
  grammar; change 7b's author could bypass it by writing a rule whose `then` clause reaches
  `entity.sexual._traits.climax_phase` directly instead of routing through this function.** →
  Mitigation: this design and D-7 state explicitly that 7b's rules must route every `climax_phase`
  mutation through `_apply_climax_phase_set()`; a test in this change fabricates a direct out-of-cycle
  attempt (e.g. `進行中 → 接近`) and asserts it no-ops, proving the guard itself is correct
  independent of who calls it.
- **[Risk] The public property surface (D-2) could still be bypassed by a future consumer reaching
  into `entity.sexual._traits` directly, since Python has no true private attributes.** → Accepted;
  the same convention-over-enforcement trade-off change 6 already accepted for `entity.buffs`'s
  internal storage — the leading underscore and this design's explicit documentation are the
  guardrail, not a language-level lock.
- **[Risk] Every race-specific behavior `variable_rule.md` describes (D-7) is deliberately left
  unbuilt by both this change and change 7b, meaning the eventual shipped rule table will
  under-model what the source document actually narrates for elf characters specifically.** →
  Accepted and documented explicitly; the buff-based seam (rate/bounds/decay levers, per hard
  requirement 8) is the correct future home, named in Non-Goals and D-7, not silently dropped.
- **[Risk] `OrderedLevelTrait`'s exact base-class API (`Trait.__init__`'s signature, min/max
  attribute names) is assumed, not confirmed against the installed Evennia 6.1.0 package.** →
  Flagged for implementer verification, consistent with changes 1–6's identical discipline for every
  other Evennia-contrib API assumption.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/sexual_state.py` does not exist yet. The only sequencing concerns are operational:

- This change must land after change 6 (needs `world/rules/rulebook/schema.py` importable for the
  self-arming test, and `entity_active_buffs()` as a documented future seam) and change 4 (needs
  `world/lore/sexual_vocab.py`'s six tuples and the `entity.db.sexual` raw-baseline convention).
- Landing this change is what flips change 6's `test_combat_modifiers_self_arming.py` test from
  skipped to passed — no edit to that test file is made or required; the flip is a side effect of
  `world.rules.sexual_state` existing and `entity.sexual` being real.
- **Change 7b (`sexual-transition-rules`) depends on this change** — it consumes `SexualState`'s
  public property surface and `_apply_climax_phase_set()` as its target, and inherits D-7's
  `variable_rule.md` analysis as its own starting point rather than re-deriving it.
- Change 8 (`action-resolver`) is expected to call change 7b's future `apply_event()` and to author
  any sexual-magic buff instances; change 11 (`world-clock`) is expected to invoke
  `decay_tick()`/`reset_daily_counters()` at its own settlement-order position. Neither call exists
  yet — this change only guarantees the callables exist with the documented signatures.

## Open Questions

- **Should a future bestiary field (e.g. `MonsterTier.sexual_profile`) let specific monster species
  override the flat `build_monster_sexual_baseline()` default (D-5)?** Left to whoever next touches
  the bestiary — design doc §6.4 says "most monsters," implying some do not fit the flat default
  (e.g. a monster archetype whose narrative role specifically involves shame or exposure), but no
  roadmap item currently owns that extension, and this change does not guess at its shape. Note also
  that `experience_types`' `異種性愛` (interspecies) entry already implies interspecies sexual content
  is expected in this setting at least from the character side; a monster-side sexual profile richer
  than the flat default would plausibly matter for those encounters specifically.
- **Which concrete buff(s) will eventually model the race-specific behaviors named in D-7?** Left to
  whichever skill-effect change introduces elf-specific passives, authored into change 6's
  `buffs.yaml` — this change documents the target-field naming convention (`rate`/`bounds`/`decay` on
  a sexual-state field key) such a buff would use, but authors none.
- **Exact `TraitHandler`/`Trait` constructor keyword names** (`min`/`max`, `base` vs `value` at
  construction) are left to the implementer to confirm against the installed Evennia 6.1.0
  `evennia.contrib.rpg.traits` source, consistent with the verification discipline changes 1–6 already
  established.
