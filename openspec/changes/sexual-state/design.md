## Context

This is roadmap item #7 (design doc §11), depending on change 6 (`buffs-rulebook`) for
`world/rules/rulebook/schema.py`'s shared condition grammar (`Rule`, `load_rules()`,
`evaluate_condition()`) — a handoff change 6's own design doc D-1/D-2 wrote explicitly for this
change to consume rather than reinvent — and on change 4 (`import-contract`) for
`world/lore/sexual_vocab.py`'s six frozen ordered-level tuples and the `entity.db.sexual` raw
baseline storage convention its `loader.py` already writes to. No code exists yet for this change's
scope: `world/rules/` currently holds `traits.py` (change 3), `rulebook/schema.py`,
`buffs.py`/`combat_modifiers.py` and their YAML tables (change 6) — nothing named `sexual_state.py`
or `rulebook/sexual.yaml`.

Two artifacts already point at this change before it exists. First, change 6's
`combat_modifiers.yaml` carries two rules — `high_arousal_agility_accuracy_penalty` and
`climax_in_progress_locks_actions` — that read `context["arousal"]`/`context["climax_phase"]` only
when `entity.sexual` is not the change-3 placeholder `None`; a dedicated test,
`test_combat_modifiers_self_arming.py::test_high_arousal_rule_fires_once_sexual_state_exists`,
guarded by `pytest.importorskip("world.rules.sexual_state")`, reports **skipped** until this module
exists and `entity.sexual` is real. Second, `tmp/story_settings/variable_rule.md` is the only
behavioral specification for how each field transitions — an update-guide written for a different,
prose-driven system, never expressed in `when`/`then` form, containing (documented below in D-8) one
direct self-contradiction and several race-specific asides that do not belong in a species-agnostic
baseline rule table.

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
- `SexualState`, mounted as `entity.sexual` (replacing change 3's `None` placeholder), with two
  distinct construction paths: from `entity.db.sexual` (change 4's raw imported baseline) for
  `PlayerCharacter`/`NPC`, and a monster-default baseline (普通 sensitivity, `shame` permanently
  clamped to 無) for `Monster` entities, which are never routed through change 4's JSON import
  pipeline.
- `rulebook/sexual.yaml`: every event/field-triggered transition transcribed faithfully from
  `variable_rule.md`, sharing change 6's `when` grammar unmodified, with a `then` vocabulary this
  change defines and owns.
- A rule-evaluation function, `apply_event(entity, event, **context)`, that mutates `SexualState`
  fields — the one structural difference from change 6's read-only `evaluate_combat_modifiers()`,
  per change 6's own D-1 framing ("sexual transitions ... mutate one named field").
- `decay_tick(entity, elapsed_seconds)` and `reset_daily_counters(entity)`, exposed as plain
  callables for change 11 (`world-clock`) to invoke at its own chosen point in the fixed settlement
  order — no ordering relative to trait regen or buff ticks is assumed or hardcoded here.
- A mechanical rule-ID-to-test-name correspondence check, mirroring change 6's D-7 discipline
  exactly, so a rule cannot be added to `sexual.yaml` without a matching `test_rule_<id>` function.
- A resolved, documented answer for every place `variable_rule.md` is ambiguous or
  self-contradictory (D-8), rather than a silent pick.

**Non-Goals:**
- No `ActionResolver`, targeting, or effect-resolution pipeline (change 8) — `apply_event()` is the
  seam change 8's step 5 ("effect resolution, driven by rulebook") is expected to call once a skill
  or command narrates a stimulus; this change does not decide which player commands fire which
  events.
- No combat resolution, to-hit formula, or damage math (change 9) — change 6's
  `evaluate_combat_modifiers()` already reads `entity.sexual.arousal`/`.climax_phase` today; this
  change only has to make that read live, not build anything in `combat_modifiers.py` itself.
- No world clock, scheduled events, or settlement ordering (change 11) — `decay_tick()`/
  `reset_daily_counters()` are plain callables invokable directly in a test with no clock present,
  exactly mirroring change 6's `tick_buffs(entity)` seam.
- No new buff definitions in `buffs.yaml` and no edit to `buffs.py`'s `_apply_rate_modifier()`. Hard
  requirement 8 asks this change to "define which sexual fields those three levers apply to" — this
  change documents the target-field naming convention a future buff would use (D-6) and reads
  `entity.buffs` for any such buff at decay/apply time, but authors no concrete buff instance. The
  race-specific behaviors `variable_rule.md` describes (elf rapid post-climax recovery, elf
  long-term arousal floor, magic-induced temporary sensitivity spikes) are exactly what such a
  future buff would model — building them is change 8's or a skill-effect's job, not this change's
  (see D-8, D-9).
- No SP/exhaustion coupling (`variable_rule.md`'s "climax consumes 20-30 SP" / "虛脫" status below a
  SP threshold) — that is a resource-deduction concern belonging to change 8's `ActionResolver`
  pipeline step 6, which reads `entity.traits`, not `entity.sexual`. Flagged as an integration point
  for change 8's author, not built here.
- No exhaustive per-monster-species sexual-baseline table. Design doc §6.4 says "most monsters" sit
  at the flat default this change builds; a bestiary field carrying per-species overrides would
  require an edit to change 2's `MonsterTier`/bestiary registries, which this change does not make.
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
is no numeric range underneath, only five or four discrete named rungs, and every consumer (this
change's own rules, change 6's `combat_modifiers.yaml`) needs to compare *by rung*, not by an
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

### D-2. `SexualState` mounts a second, private `TraitHandler` — distinct from `entity.traits` —
over the fixed fields and a dynamically-keyed `sensitivity` sub-collection.

```python
class SexualState:
    """Mounted as entity.sexual (typeclasses/entities.py), replacing change
    3's None placeholder. entity.db.sexual stays the raw imported baseline
    (change 4); this class is the live handler built from it, never confused
    with the bare name -- the exact convention corrected across changes 4/5
    that must not regress here (hard requirement 3)."""

    def __init__(self, entity):
        self._entity = entity
        self._traits = TraitHandler(entity, db_attribute_key="sexual_traits")
        self._decay_accumulator = entity.attributes.get(
            "sexual_decay_accumulator", default={}, category="sexual_state"
        )
        baseline = entity.db.sexual
        if baseline is not None:
            self._build_from_baseline(baseline)                  # character path
        elif isinstance(entity, Monster):
            self._build_from_baseline(build_monster_sexual_baseline())  # D-7
        else:
            self._build_from_baseline(_generic_default_baseline())      # e.g. a
                                                                          # hand-spawned
                                                                          # NPC never
                                                                          # routed through
                                                                          # change 4
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
directly as `entity.attributes` under the `sexual_state` category, next to the decay accumulator.

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
    for free (D-7) without a separate code path."""

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
than a second handler, or a bespoke dict on `entity.db`) means `sensitivity_up_on_frequent_stimulation`
(D-4's rule 25) is exactly as testable and exactly as bound-clampable-by-a-future-buff as any other
ordered-level field — no special-cased storage for the one field that happens to be dict-shaped.

**Alternative considered**: a plain `dict[str, str]` of raw level strings, converted to/from
`OrderedLevelTrait` only at comparison time. Rejected — this would mean `sensitivity` values are
*not* real `OrderedLevelTrait` instances at rest, so a future buff wanting to clamp
`sensitivity['乳房']`'s bounds (design doc's "magic 影響可暫時提升至敏感異常" — hard requirement 8's
"clamped bounds" lever) would have nothing to clamp; keeping every sensitivity entry a first-class
`OrderedLevelTrait` on the private handler gives that future buff the same clamp mechanism every
other field already has.

### D-4. `rulebook/sexual.yaml`: the transition table, transcribed from `variable_rule.md`, with a
`then` vocabulary this change owns.

Sharing change 6's `when` grammar unmodified — `event`, `field`+`equals`/`gte`, `field_changed`+
`direction` (this change never needs `buff_active` in its own `when` clauses, though nothing prevents
a future rule from using it) — and defining `then` as follows, since change 6's D-1 leaves `then`
entirely to the owning table:

| `then` key | Meaning |
|---|---|
| `field` | Target field name (required on every rule) |
| `delta` | Signed int (`"+1"`, `"-1"`) or an inclusive range (`"+1..+2"`), resolved via `random.randint` at apply time |
| `set` | Absolute value: a level name for ordered fields, `true`/`false` for `virgin` |
| `add` | A value appended to a `frozenset`-valued field (`experience_types` only) |
| `set_from` | Sources the absolute value from a context key supplied by the caller of `apply_event()` (used once — clothing-driven exposure) |
| `part_from_context` | Marks that `field: sensitivity` is further keyed by `context["part"]`, since `sensitivity` is dict-valued, not scalar |
| `irreversible` | Marks a `set` mutation as one-way; once applied, no later `then` clause (from any rule, ever) can move the field back |

The full table, grouped by field (every row transcribed from a specific `variable_rule.md` bullet,
cited inline):

```yaml
# world/rules/rulebook/sexual.yaml

# --- arousal (性狀態.性喚起) ---
- id: arousal_up_on_stimulus
  when: { event: stimulus_applied }
  then: { field: arousal, delta: "+1..+2" }        # 接受性刺激時提升1-2級

- id: arousal_up_on_sustained_stimulus
  when: { event: sustained_stimulus }
  then: { field: arousal, delta: "+1" }            # 持續刺激經過合理時長後再提升1級

- id: arousal_jump_on_extreme_stimulus
  when: { event: extreme_stimulus }
  then: { field: arousal, set: 極限 }               # 極端刺激可直接躍升至極限

- id: arousal_reset_after_climax
  when: { event: climax_ends }
  then: { field: arousal, set: 微興奮 }             # 高潮後短暫降至微興奮

# --- wetness (性狀態.私處.濕潤程度) ---
- id: wetness_follows_arousal_increase
  when: { field_changed: arousal, direction: up }
  then: { field: wetness, delta: "+1" }             # 性喚起每提升1級，濕潤程度至少提升1級

- id: wetness_up_on_direct_stimulus
  when: { event: direct_stimulus_applied }
  then: { field: wetness, delta: "+1..+2" }         # 接受直接刺激時快速提升

- id: wetness_max_on_climax
  when: { event: climax_reached }
  then: { field: wetness, set: 泛濫 }               # 高潮時達到泛濫

# --- climax_phase (性狀態.高潮狀態) — see D-5 for the cyclic-field guard ---
- id: climax_gate
  when: { field: arousal, equals: 極限 }
  then: { field: climax_phase, set: 接近 }          # 性喚起達至極限時轉為接近

- id: climax_progresses_on_continued_stimulus
  when: { field: climax_phase, equals: 接近, event: stimulus_applied }
  then: { field: climax_phase, set: 進行中 }         # 達臨界點時轉為進行中 -- D-8 ambiguity

- id: climax_ends_to_afterglow
  when: { event: climax_ends }
  then: { field: climax_phase, set: 餘韻 }          # 高潮結束後轉為餘韻

# --- climax_today (性狀態.今日高潮) ---
- id: climax_today_increments_on_climax
  when: { event: climax_reached }
  then: { field: climax_today, delta: "+1" }        # 每次達到高潮時+1

# --- virgin / experience_types (性狀態.處女 / 性狀態.性經驗類型) ---
- id: virginity_once
  when: { event: first_vaginal_penetration }
  then: { field: virgin, set: false, irreversible: true }   # D-8: resolved contradiction

- id: experience_vaginal_added
  when: { event: first_vaginal_penetration }
  then: { field: experience_types, add: 陰道性交 }

- id: experience_masturbation_added
  when: { event: first_masturbation_climax }
  then: { field: experience_types, add: 自慰 }

- id: experience_lesbian_added
  when: { event: penetrative_contact_with_female }
  then: { field: experience_types, add: 女女性愛 }

- id: experience_breast_service_added
  when: { event: breast_service_performed }
  then: { field: experience_types, add: 乳交 }

- id: experience_watched_added
  when: { event: sexual_activity_observed }
  then: { field: experience_types, add: 被觀看 }

- id: experience_exposure_added
  when: { event: deliberate_public_exposure }
  then: { field: experience_types, add: 露出 }

- id: experience_interspecies_added
  when: { event: sexual_activity_with_nonhuman }
  then: { field: experience_types, add: 異種性愛 }

# --- shame (性狀態.羞恥感) ---
- id: shame_up_on_exposure_increase
  when: { field_changed: exposure, direction: up }
  then: { field: shame, delta: "+1" }               # 暴露增加時提升

- id: shame_up_on_public_activity
  when: { event: public_sexual_activity }
  then: { field: shame, delta: "+1" }               # 公開場合性活動時提升

- id: shame_up_on_being_watched
  when: { event: watched }
  then: { field: shame, delta: "+1" }               # 被注視時提升

# --- exposure (性狀態.暴露程度) ---
- id: exposure_set_on_clothing_change
  when: { event: clothing_changed }
  then: { field: exposure, set_from: garment_exposure_level }  # 更換/故意調整服裝

- id: exposure_up_on_clothing_damage
  when: { event: clothing_damaged_in_combat }
  then: { field: exposure, delta: "+1" }            # 戰鬥中服裝破損可能增加暴露

# --- sensitivity (性狀態.乳房/私處.敏感度) ---
- id: sensitivity_up_on_frequent_stimulation
  when: { event: part_frequently_stimulated }
  then: { field: sensitivity, part_from_context: true, delta: "+1" }  # 頻繁刺激可逐步提升
```

25 rules, one `id` each, none omitted. `habituation` (羞恥感's diminishing-returns note) and every
race-specific aside are deliberately **not** rows in this table — see D-8/D-9.

### D-5. `apply_event()`: a fixed-point evaluation loop, because `field_changed` rules depend on
what an earlier rule in the same pass just did.

```python
def apply_event(entity, event: str, **event_context) -> list[str]:
    """Returns the list of rule IDs that fired. Mutates entity.sexual fields
    directly -- this is change 6's D-1 structural difference from
    evaluate_combat_modifiers() made concrete: sexual transitions write,
    combat modifiers only read."""
    fired: list[str] = []
    changed: dict[str, str] = {}          # field -> "up"/"down", this pass
    for _ in range(_MAX_PASSES):           # small, fixed cap -- these tables
        context = _build_context(entity, event, changed, **event_context)
        pass_changed: dict[str, str] = {}
        for rule in _RULES:
            if rule.id in fired and "field_changed" not in rule.when:
                continue    # event-triggered rules fire once per apply_event() call
            if evaluate_condition(rule.when, context):
                direction = _apply_then(entity, rule.then, context)
                if direction:
                    pass_changed[rule.then["field"]] = direction
                fired.append(rule.id)
        if not pass_changed:
            break
        changed = pass_changed
        event = None    # subsequent passes are field_changed-driven only,
                          # not a re-fire of the original event
    return fired
```

`_MAX_PASSES` is a small constant (5) — every cascade `variable_rule.md` describes is at most two
links deep (stimulus → arousal → wetness; arousal → climax_gate), so this is a defensive cap, not a
tuned parameter. A rule that already fired once for a given `event` does not re-fire on a later pass
of the *same* `apply_event()` call unless it is itself `field_changed`-triggered — this is what
prevents `arousal_up_on_stimulus` from re-applying its delta a second time once `wetness_follows_
arousal_increase` fires in pass 2.

**`context` construction** mirrors change 6's `_build_context()` shape exactly, extended with this
change's own fields:

```python
def _build_context(entity, event, changed, **event_context) -> dict:
    sexual = entity.sexual
    return {
        "event": event,
        "arousal": sexual._traits.arousal,
        "wetness": sexual._traits.wetness,
        "shame": sexual._traits.shame,
        "exposure": sexual._traits.exposure,
        "climax_phase": sexual._traits.climax_phase,
        "climax_today": sexual._traits.climax_today.value,
        "virgin": sexual.virgin,
        "experience_types": sexual.experience_types,
        "active_buffs": entity_active_buffs(entity),   # change 6's own helper, reused
        "_changed": changed,
        **event_context,
    }
```

Reusing `entity_active_buffs()` (change 6, `world/rules/buffs.py`) rather than reaching into
`entity.buffs` directly keeps this change importing change 6's public seam, not its internals — the
same discipline change 6's own `combat_modifiers.py` already applied to itself.

### D-6. `climax_phase` is a cyclic field, not a monotonic ladder — valid transitions are enforced by
the effect interpreter, not the `when` grammar.

`CLIMAX_PHASE_LEVELS = ("未達", "接近", "進行中", "餘韻")` is ordered for `gte`/`equals` comparison
purposes (combat_modifiers.yaml's `climax_phase, equals: 進行中` needs exactly this), but the *valid
transition graph* is a cycle (`未達→接近→進行中→餘韻→未達`), not "higher is always further along" —
`餘韻`'s ordinal is the highest in the tuple, yet the correct next transition from `餘韻` is back down
to `未達` (via decay) or, per `variable_rule.md`'s elf-specific note, directly back up to `接近`.
Change 6's `when` grammar has no way to express "AND climax_phase is currently X" as a second,
independent `field`-condition in the same block (a `when` dict's keys must be unique — one `field`
key per block, combined only with `equals`/`gte`, not stacked against a second field). Rather than
inventing a second condition kind in `schema.py` (forbidden — hard requirement 5), the guard lives
entirely in `_apply_then()`'s own dispatch for `climax_phase`, which `then` is opaque to `schema.py`
anyway and interpreted only here:

```python
_VALID_CLIMAX_TRANSITIONS = {
    "未達": {"接近"},
    "接近": {"進行中", "未達"},   # 未達: arousal can fall away before climax
    "進行中": {"餘韻"},
    "餘韻": {"未達", "接近"},      # 未達: normal afterglow decay;
                                    # 接近: elf-style rapid re-arousal (D-9) --
                                    # this change permits the transition edge;
                                    # nothing today drives it there but decay
}

def _apply_climax_phase_set(entity, target_level: str) -> str | None:
    current = entity.sexual._traits.climax_phase.level
    if target_level not in _VALID_CLIMAX_TRANSITIONS.get(current, set()):
        return None   # no-op: e.g. climax_gate re-firing while already 進行中
                        # does not silently regress the phase
    entity.sexual._traits.climax_phase.value = CLIMAX_PHASE_LEVELS.index(target_level)
    return "cycle"
```

This means `climax_gate` (arousal stays 極限 while some unrelated event also fires) cannot regress an
in-progress climax back to 接近, and `climax_progresses_on_continued_stimulus` cannot fire out of
turn from `未達` — both guarded by the same table, in one place, rather than duplicated per rule.

### D-7. Monster baselines: 普通 sensitivity comes free from D-3's lazy default; `shame` is the one
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
because its own range has collapsed to one point, not because some rule refuses to fire. Every other
field (`arousal`, `wetness`, `exposure`, `climax_phase`) keeps its full, unclamped range, since design
doc §6.4 only names `shame` for the clamp — a monster can still be aroused, wet, exposed, or
mid-climax; it simply cannot feel shame.

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

### D-8. Resolving `variable_rule.md`'s ambiguities and one direct self-contradiction.

**Self-contradiction (resolved): the virginity trigger.** §性狀態.處女 states the "唯一更新條件"
(sole update condition) is "首次**同種異性**陰道插入" (first *same-species, opposite-sex* vaginal
penetration), but §性狀態.性經驗類型's own 陰道性交 entry says simply "首次被插入後添加（同時處女變
false）" (added after first penetration — full stop — simultaneously flips virgin to false), with no
species/gender qualifier at all. These cannot both be the literal, exact trigger: either virginity
requires a same-species-opposite-sex partner specifically, or any first penetration counts and the
`性經驗類型` section's plainer wording is the accurate one. **Decision**: use the unqualified trigger
— `first_vaginal_penetration`, any partner — for three reasons: (1) design doc §6.4 itself gives the
worked example as `event: first_vaginal_penetration` with no species/gender qualifier, and this
change transcribes into that exact grammar; (2) `異種性愛` (interspecies) is its own, separate
`experience_types` entry triggered by a *different* event (`sexual_activity_with_nonhuman`), which
would be structurally redundant with a species-qualified virginity trigger — the vocabulary already
has a dedicated place for "this was with a non-human partner," so virginity does not need to encode
species a second time; (3) the narrower reading would leave virginity never flipping at all for an
interspecies or a same-sex first encounter, which contradicts `性經驗類型`'s own unconditional
"同時處女變 false." `virginity_once` and `experience_vaginal_added` therefore share the identical
`when: { event: first_vaginal_penetration }` clause.

**Ambiguity (resolved): what "達臨界點" (reaching the critical point) means for 接近→進行中.**
`variable_rule.md` never defines this numerically or behaviorally — no duration, no roll, no
secondary threshold. **Decision**: interpret it as "stimulus continues while already at 接近" —
`climax_progresses_on_continued_stimulus`'s `when: { field: climax_phase, equals: 接近, event:
stimulus_applied }`. This is the smallest reading consistent with the surrounding prose (which
otherwise only ever gates transitions on stimulus events or field thresholds, never on elapsed
real-time within a single event) and requires no new condition kind. Flagged explicitly here as an
assumption, not a fact `variable_rule.md` states.

**Ambiguity (resolved): "濕潤程度至少提升1級" — "at least" one level.** The word "至少" (at least)
suggests wetness could rise by more than one level per arousal increase under some circumstances
`variable_rule.md` never specifies. **Decision**: the baseline rule (`wetness_follows_arousal_
increase`) applies exactly `+1`; the "more than one" case is covered by the separate, faster
`wetness_up_on_direct_stimulus` rule (`+1..+2`) firing independently when direct stimulus is also
present. Two rules, not one rule with an unbounded delta, keeps each individually testable and
matches the text's own separation of "喚起提升時" (arousal rises) from "接受直接刺激時" (receiving
direct stimulus) as two distinct triggers.

**Explicitly out of scope, not an ambiguity to resolve but a scope boundary: every race-specific
aside.** `variable_rule.md` repeatedly qualifies a rule with "因精靈體質" / "精靈族天生" / "精靈族具備
多重高潮體質" (elf constitution / elves are innately.../elves have a multi-orgasm constitution) —
rapid post-climax arousal recovery, a floor that rarely drops below 微興奮, innately elevated
sensitivity, and rapid re-entry into climax from 餘韻. None of these become rows in `sexual.yaml`:
the table is species-agnostic by design (design doc §6.4 never scopes any field to one race), and
every one of these asides is expressible as a future buff modifying rate-of-change, clamped bounds,
or decay rate on a specific entity — exactly hard requirement 8's three levers, and exactly the
seam this change documents (Non-Goals) but does not fill with a concrete buff instance. Building an
"elf sensitivity" buff is change 8's or a skill-effect's job once a concrete skill/passive needs one;
authoring it here would mean editing `buffs.yaml` (change 6's file) for a mechanic no roadmap item
has asked this change to build.

**Explicitly out of scope: every purely descriptive field.** `身體感受`, `興奮要素`, `被注視感受`,
`乳房.整體狀態`, `私處.外觀`, and `最後性活動` are all free-text narrative fields with no ordered
levels, counters, or flags — they do not appear anywhere in design doc §6.4's field model. These are
prose-generation material for the Narrator (change 18) or `PersonaStore`-adjacent storage, not
`SexualState` fields; `basic_info.狀態` (a top-level 正常/性興奮/戰鬥中/... status enum in
`variable_rule.md`) is likewise not part of §6.4's model and is left unbuilt here — it looks like a
derived narrative label (combining combat state, rest state, and sexual state) rather than a new
mechanical field this change owns.

### D-9. Rule-ID-to-test correspondence — mirrors change 6's D-7 exactly, extended to `sexual.yaml`.

`world/rules/tests/test_sexual_rule_id_test_correspondence.py::test_every_sexual_rule_has_a_test`
walks `sexual.yaml`'s loaded `Rule.id` values (via `load_rules()`, the identical function change 6's
own correspondence check uses) and asserts a `test_rule_<id>` function exists in
`test_sexual_state.py` via `inspect.getmembers`. This makes "every rule has an ID and every ID has a
unit test" (design doc §10, hard requirement 4) a property CI checks the moment a 26th row is added
to `sexual.yaml` without a matching test, not a discipline that depends on reviewer attention — the
identical mechanism, not a parallel reimplementation, as change 6's own
`test_rule_id_test_correspondence.py`.

### D-10. Flipping change 6's self-arming test: the three things that must all be true.

`test_combat_modifiers_self_arming.py::test_high_arousal_rule_fires_once_sexual_state_exists` is
guarded by `pytest.importorskip("world.rules.sexual_state")` and asserts, against a *real*
`entity.sexual` at or above `高度` arousal, that `evaluate_combat_modifiers()` returns
`high_arousal_agility_accuracy_penalty`'s bundle. Three things this change delivers must all hold for
it to flip from skipped to passed:

1. `world.rules.sexual_state` must exist and import cleanly (trivially true once this change lands).
2. `entity.sexual` must be a live object, not `None` — requires the `typeclasses/entities.py` mount
   edit (D-2) replacing change 3's placeholder.
3. `entity.sexual.arousal >= "高度"` must evaluate correctly through Python's own `>=` operator with
   no special-casing on change 6's side — requires D-1's `OrderedLevelTrait.__ge__` contract to hold
   exactly as documented.

A verification task runs this specific test in isolation both before (skipped) and after
(passed) the full change lands, mirroring change 6's own task 6.5 discipline for the identical test
in its pre-change-7 state.

## Risks / Trade-offs

- **[Risk] 25 individual rule IDs, each requiring its own dedicated unit test plus the mechanical
  correspondence check, is a lot of granular test surface for a one-day change.** → Accepted; this is
  inherent to change 6's shared grammar having no OR-combinator across distinct event names (only
  implicit AND within one `when` block) — merging, say, the three `shame_up_on_*` rules into one
  would require inventing a second condition-combination kind in `schema.py`, which hard requirement
  5 forbids. If scope must shrink, the safest cut is deferring `sensitivity_up_on_frequent_
  stimulation` and its long-term/permanent-change framing (the one rule whose real-world trigger —
  "frequent" — is itself vague) rather than thinning the well-specified arousal/wetness/climax core.
- **[Risk] The fixed-point evaluation loop (D-5) could, in a pathological future rule addition, cycle
  without converging within `_MAX_PASSES`.** → Mitigation: the cap is a hard stop (rules simply stop
  firing after 5 passes, they do not raise), and a regression test constructs a rule table that would
  cycle forever without the cap and asserts `apply_event()` still returns within `_MAX_PASSES`
  iterations, never hangs.
- **[Risk] `_apply_then()`'s dispatch by `then.field`'s "kind" (ordered_level / counter / flag /
  append_only_set / cyclic) is Python logic outside the shared `when`/`then` grammar, which could
  drift from `sexual.yaml`'s actual field list if a 26th field is ever added without updating the
  kind registry.** → Mitigation: a regression test asserts every distinct `field` value appearing
  anywhere in `sexual.yaml` has a corresponding entry in the `FIELD_KINDS` registry, failing loudly
  (naming the unmapped field) rather than falling through to a default.
- **[Risk] The climax-phase cycle guard (D-6) is bespoke logic that a future rule author could
  bypass by adding a new `sexual.yaml` row with a `set` clause that ignores `_VALID_CLIMAX_
  TRANSITIONS`.** → Accepted: `_apply_climax_phase_set()` is the *only* code path that ever writes
  `climax_phase`'s value (no rule's `then` clause reaches the trait directly), so any new rule
  targeting `climax_phase` is automatically routed through the same guard; a test constructs a
  fabricated rule attempting `進行中 → 接近` directly and asserts it no-ops.
- **[Risk] Every race-specific behavior `variable_rule.md` describes (D-8) is deliberately left
  unbuilt, meaning the shipped baseline table under-models what the source document actually
  narrates for elf characters specifically.** → Accepted and documented explicitly; the buff-based
  seam (rate/bounds/decay levers, per hard requirement 8) is the correct future home, named in
  Non-Goals, not silently dropped.
- **[Risk] `OrderedLevelTrait`'s exact base-class API (`Trait.__init__`'s signature, min/max
  attribute names) is assumed, not confirmed against the installed Evennia 6.1.0 package.** →
  Flagged for implementer verification, consistent with changes 1–6's identical discipline for every
  other Evennia-contrib API assumption.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/sexual_state.py` does not exist yet. The only sequencing concerns are operational:

- This change must land after change 6 (needs `world/rules/rulebook/schema.py`'s `Rule`/
  `load_rules()`/`evaluate_condition()` importable) and change 4 (needs `world/lore/sexual_vocab.py`'s
  six tuples and the `entity.db.sexual` raw-baseline convention).
- Landing this change is what flips change 6's `test_combat_modifiers_self_arming.py` test from
  skipped to passed — no edit to that test file is made or required; the flip is a side effect of
  `world.rules.sexual_state` existing and `entity.sexual` being real.
- Change 8 (`action-resolver`) is expected to call `apply_event()` from its effect-resolution step
  and to author any sexual-magic buff instances; change 11 (`world-clock`) is expected to invoke
  `decay_tick()`/`reset_daily_counters()` at its own settlement-order position. Neither call exists
  yet — this change only guarantees the callables exist with the documented signatures.

## Open Questions

- **Should a future bestiary field (e.g. `MonsterTier.sexual_profile`) let specific monster species
  override the flat `build_monster_sexual_baseline()` default (D-7)?** Left to whoever next touches
  the bestiary — design doc §6.4 says "most monsters," implying some do not fit the flat default
  (e.g. a monster archetype whose narrative role specifically involves shame or exposure), but no
  roadmap item currently owns that extension, and this change does not guess at its shape.
  Note also that `experience_types`' `異種性愛` (interspecies) entry already implies interspecies sexual
  content is expected in this setting at least from the character side; a monster-side sexual profile
  richer than the flat default would plausibly matter for those encounters specifically.
- **Which concrete buff(s) will eventually model the race-specific behaviors named in D-8?** Left to
  change 8 or whichever skill-effect change introduces elf-specific passives — this change documents
  the target-field naming convention (`rate`/`bounds`/`decay` on a sexual-state field key) such a buff
  would use, but authors none.
- **Exact `TraitHandler`/`Trait` constructor keyword names** (`min`/`max`, `base` vs `value` at
  construction) are left to the implementer to confirm against the installed Evennia 6.1.0
  `evennia.contrib.rpg.traits` source, consistent with the verification discipline changes 1–6 already
  established.
