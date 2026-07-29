## Context

This is roadmap item #6 (design doc §11), depending on change 3 (`entity-traits`, which provides
`LivingEntity`, the `buffs` placeholder seam attribute, `entity.traits`/`TraitHandler`, and D-7's
boundary reserving `StaticTrait`'s `mod` component for `BuffHandler`). No code exists yet for this
change's scope — `world/rules/` currently holds no `buffs.py`, `combat_modifiers.py`, or `rulebook/`
directory; `world/rules/traits.py` is the only module change 3 added there.

Two artifacts already name this change before it exists:

1. **Design doc §6.4 states the combat-coupling table's exact shape** and requires it live in
   `rulebook/combat_modifiers.yaml`, "in the same table as poison and paralysis," with explicit
   language that this must have "no special-case branches." That table cannot be authored responsibly
   without first deciding whether it is a bespoke format or an instance of a shared engine — and design
   doc §6.4 also shows `rulebook/sexual.yaml` (change 7's future table) using a visibly similar
   `when`/`then` shape. Getting the relationship between these two tables wrong here forces change 7 to
   either duplicate this change's condition-matching logic or retrofit its own table onto whatever this
   change happens to have built.
2. **Change 5's design.md D-6 explicitly named this change as the owner of a specific, described
   mechanic**: Elosia's card narrates a partial magic-growth-rate conferral onto Violet ("魔法成長百倍增
   幅" scaled down), which change 5 declined to fold into its own `ConferredSkillGrant` (typed
   specifically around combat-stat `trait_keys`/multiplicative `scale`) because design doc §6.4 assigns
   "rate of change" to buffs, not skills. This design must give that mechanic a concrete, buildable shape
   — not merely acknowledge the deferral a second time.

The five sample character cards in `tmp/story_settings/character/` (gitignored, never committed, not
shippable per design doc §1's age gate) are read here only to confirm what shape of conferral Violet's
card actually narrates; none of their numeric or narrative content is authoritative.

## Goals / Non-Goals

**Goals:**
- Mount `evennia.contrib.rpg.buffs.BuffHandler` (§4: "use directly," duration/tick/stacking already
  implemented) as `entity.buffs` on `LivingEntity`, replacing change 3's placeholder — the same
  handler-mount replacement change 5 already performed for `entity.skills`/`entity.equipment`.
- A resolved, justified answer to the three-consumer problem (sexual transitions, combat modifiers, buff
  effects) — see D-1 through D-4 below — that gives change 7 a concrete engine to import rather than
  reinvent, and gives change 9 a concrete query function to call.
- `world/rules/rulebook/schema.py`: the shared condition grammar, YAML loader, and `evaluate()` function,
  with the rule-ID-to-test-name discipline design doc §10 requires built into the structure, not left to
  reviewer diligence.
- `world/rules/rulebook/combat_modifiers.yaml` + `world/rules/combat_modifiers.py`: a seed table (poison,
  paralysis, fear, plus the two arousal/climax-phase rows design doc §6.4 shows verbatim) and the pure
  query function change 9 will call.
- `world/rules/rulebook/buffs.yaml` + `world/rules/buffs.py`: the setting's buff definitions — each
  configuring some subset of rate-of-change, clamped bounds, and decay rate (§6.4's exhaustive list of
  what a buff may modify) — plus the `TraitHandler`-facing glue and the conferred-growth-rate mechanism
  (D-5/D-6).
- A concrete, buildable, and tested design for a rate-of-change modifier conferred from one entity to
  another (Elosia → Violet), inherited from change 5's D-6.

**Non-Goals:**
- No `SexualState` state machine, no ordered-level `Trait` subclass, no `rulebook/sexual.yaml` content —
  change 7's job entirely. This change only builds the condition engine change 7 is expected to import,
  and documents the exact shape of the duck-typed context `combat_modifiers.py` reads so change 7 knows
  what to wire its own fields into.
- No `ActionResolver`, targeting, or effect-resolution pipeline (change 8) — this change exposes a plain
  buff-presence query (`entity.buffs.get(key)` / a thin `blocks_action(entity)` helper) for step 4 of
  design doc §6.1's pipeline to call, and a plain `grant_conferred_growth_rate(...)` write function for
  change 8's cast-time resolution to call, but does not itself decide when an action is forbidden or wire
  any skill's cast path to it.
- No combat resolution, to-hit formula, or damage math (change 9) — `evaluate_combat_modifiers()` returns
  a data bundle; applying it to a to-hit roll or a damage formula is change 9's job.
- No world clock, scheduled events, or settlement ordering (change 11) — this change exposes buff-tick
  as a plain callable (`tick_buffs(entity)`, thin wrapper over the contrib's own tick mechanism) for
  change 11 to invoke at the point in its fixed settlement order (§6.5: regen → buffs → sexual decay →
  ...) that change 11 decides; this change does not invent, assume, or hardcode any ordering relative to
  regen or sexual decay.
- No progression, XP, or leveling system reading `growth_rate_multiplier()`'s output for real — change
  11b (`character-progression`, depends on changes 5/6/11) owns "how magic_level actually increases over
  time" and is this function's consumer. This change builds the query function and proves it returns the
  right number given buff state; wiring it into an XP-gain event is change 11b's job, not this change's
  (see Open Questions for the sequencing note this leaves).
- No exhaustive status-effect catalogue. A representative seed set (poison, paralysis, fear, conferred
  growth rate) exercises every modifier category (rate, bounds, decay, marker-only) at least once; this
  is not a catalogue of every status effect the finished game will ever need.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/` currently contains only change 3's `traits.py`.

## Decisions

### D-1. The central problem: one shared condition grammar, not one universal rule schema — and buffs
are a fourth, structurally different thing, not a third row in the same table.

The task names three consumers and asks whether one schema serves all three. Laying out each
consumer's actual `when`/`then` shape, from design doc §6.4 directly:

| Consumer | `when` (condition) | `then` (effect) | Owner |
|---|---|---|---|
| Sexual transitions | `event: stimulus_applied` / `field_changed: arousal, direction: up` | `field: arousal, delta: "+1..+2"` — mutates **one named `SexualState` field**, plus a one-way `irreversible` flag | change 7 |
| Combat modifiers | `field: arousal, gte: 高度` / `buff_active: poisoned` (this change's addition, see below) | `agility: "-20%", accuracy: -15, actions_per_turn: 0` — an **ad hoc bundle of independently-named adjustment fields**, none of which is a `SexualState` field or a bare trait key | this change |
| Buff effects | *(not condition-triggered at all — applied explicitly by a skill effect, a combat event, or a cast)* | rate of change / clamped bounds / decay rate, on a **named target field**, for the buff's own duration | this change (definitions), contrib (lifecycle) |

**The `when` clauses are structurally identical across the first two rows** — every condition either
names an event, names a field with a threshold/equality comparator, names a field-changed direction, or
(new, needed for combat modifiers) names a buff key's presence. One evaluator can match all of these
without knowing which table it is running against. **The `then` clauses are not identical** — sexual
transitions always mutate exactly one field by a delta or an absolute set; combat modifiers produce a
transient, multi-key adjustment bundle that is never written back to any field at all (change 9 reads it
and discards it after one resolution step, the same "derived, never stored" discipline change 5's D-5
already established for `effective_value()`). Forcing these into one `then` schema would mean either
sexual transitions gain unused adjustment-bundle fields, or combat modifiers gain an unused
delta/irreversible-flag shape — both directions invent structure nobody needs.

**Decision**: `world/rules/rulebook/schema.py` defines and exports exactly the shared `when` grammar
(`Condition`, `evaluate_condition()`) plus the generic rule-loading/ID-discipline machinery
(`Rule` as `{id, when, then}` where `then` is an opaque `dict` this module never interprets), and this
change's own `combat_modifiers.py` supplies the interpretation of `then` for its own table. Change 7 is
expected to import `Condition`/`evaluate_condition()`/the loader for `sexual.yaml`, and supply its own
`then`-interpretation for field deltas — exactly the same "shared matcher, table-owns-its-effect-
vocabulary" split, not a shared `then` schema. This is recorded in `schema.py`'s own module docstring as
the explicit handoff, mirroring change 4's D-6 handoff of `sexual_vocab.py` to change 7 and change 5's
D-2 handoff of `TargetSpec`/`SkillKind` to change 8.

**Buffs are not a third row of the same when/then table at all.** A buff does not fire because a
condition became true; it is applied because something explicit says so — a skill's effect resolution,
a combat event, a cast. That is precisely the apply/tick/expire lifecycle `evennia.contrib.rpg.buffs`
already implements (§4: "use directly"). Modeling poison as a `when: {hp_below: X}` rule firing every
tick would duplicate a lifecycle the contrib already owns, and — worse — would give this project two
different mechanisms for "a timed thing that happens to an entity" (the contrib's `BaseBuff.duration`/
tick scheduling, and a from-scratch condition-rule replaying itself every tick). **Decision**: `buffs.yaml`
is a named-parameter table (buff key → its rate/bounds/decay configuration and contrib-facing tunables:
duration, tick interval, stacking), not a `when`/`then` rule table, and does not run through
`schema.py`'s `evaluate()` at all. `combat_modifiers.yaml` is the bridge between the two: its `when`
clause can name `buff_active: <key>` as a condition alongside `field`/`event` conditions, which is how
"poison and paralysis sit in the same table as arousal thresholds, with no special-case branch" (design
doc D8) is achieved — one evaluator, two condition *kinds*, zero `if is_sexual_debuff` anywhere in
`combat_modifiers.py`.

**Alternative considered**: one universal schema where `then` is a fully generic
`dict[str, str | float | bool]` interpreted identically everywhere (sexual transitions read `then.field`/
`then.delta`; combat modifiers read every other key as an adjustment). Rejected — this technically
"works" but produces a schema whose keys mean different things depending on which table is loading it
(`then.field` is meaningful for sexual transitions and meaningless noise for combat modifiers), which is
exactly the kind of implicit, table-dependent interpretation this project's own `record_type`
discriminator decision (change 4, D-1) argued against for a structurally similar problem. Keeping `then`
opaque to `schema.py` and letting each table's own Python module interpret it keeps the failure mode
explicit: a malformed `combat_modifiers.yaml` entry fails inside `combat_modifiers.py`'s own parser with
a message about combat-modifier fields, never inside a shared function that has to guess which table
called it.

### D-2. `world/rules/rulebook/schema.py`: the shared condition grammar and rule-ID discipline.

```python
# world/rules/rulebook/schema.py
"""Shared declarative-rule primitives for every YAML table under world/rules/rulebook/.
Owns the `when` condition grammar and the load/evaluate machinery only. `then`
(the effect) is deliberately left as an opaque dict -- each table's own module
(combat_modifiers.py, and change 7's future sexual_state.py) interprets its own
`then` vocabulary. See design.md D-1 for why `then` is not shared.

Change 7 (sexual-state) is expected to import Condition/evaluate_condition/
load_rules for rulebook/sexual.yaml rather than reimplementing condition
matching a second time."""

@dataclass(frozen=True)
class Rule:
    id: str
    when: dict
    then: dict            # opaque here; interpreted by the owning table's module

def load_rules(path: Path) -> list[Rule]:
    """Loads a YAML list of {id, when, then} mappings. Raises if any `id` is
    missing or duplicated within the file -- design doc S10's one-test-per-ID
    discipline is meaningless if IDs are not even required to be unique."""
    ...

def evaluate_condition(when: dict, context: Mapping[str, Any]) -> bool:
    """The one shared matcher. Recognizes exactly these condition keys,
    combined with implicit AND when more than one is present in the same
    `when` block:
      event: <name>                  -- context["event"] == name
      field: <key>, equals: <value>  -- context[key] == value
      field: <key>, gte: <value>     -- context[key] >= value (ordered-level
                                         or numeric; ordered-level comparison
                                         resolves via the vocabulary the
                                         caller's context supplies, e.g.
                                         world.lore.sexual_vocab tuples --
                                         this module has no opinion on what
                                         "greater than" means for a given
                                         field, it only calls context's own
                                         comparison helper if one is given,
                                         or falls back to Python `>=`)
      field_changed: <key>, direction: up|down
                                      -- context["_changed"] contains key
                                         with matching direction
      buff_active: <key>             -- context["active_buffs"] contains key
    Unknown condition keys raise -- a silently-ignored typo in a `when` block
    is worse than a loud failure at rule-load time.
    """
    ...
```

`context` is a plain `Mapping[str, Any]`, never `entity` itself and never a hardcoded reference to
`entity.sexual` or `entity.buffs` — the caller (this change's `combat_modifiers.py`, or change 7's future
`sexual_state.py`) is responsible for building the context dict from whatever live handlers exist at the
time it runs. This decoupling is what lets `combat_modifiers.yaml`'s arousal-threshold rows be authored
and unit-tested today, against a fake context, even though `entity.sexual` does not exist until change 7
lands (D-3).

`gte` accepts an ordered-level comparison, since design doc §6.4's own combat-modifier example
(`field: arousal, gte: 高度`) compares against an enum level, not a number — `evaluate_condition()` does
not hardcode `world.lore.sexual_vocab`'s ladder (that would create the exact `rules/` → `lore/` →
`imports/`-adjacent coupling this project has avoided elsewhere); instead the context supplies already-
comparable values (an `IntEnum`-like ordinal, or anything supporting `>=`) and this module only calls
Python's own `>=`. Change 7 is responsible for handing `evaluate_condition()` a context where
`context["arousal"]` is already an orderable value, not a bare Chinese string.

Every `Rule.id` is required and must be unique per file (`load_rules()` raises `DuplicateRuleIdError` /
`MissingRuleIdError` otherwise) — this is what makes the one-test-per-ID discipline (D-3, D-4) mechanically
enforceable rather than a naming convention someone can forget.

### D-3. `combat_modifiers.yaml` + `combat_modifiers.py`: the seed table, sharing one evaluator across
buff-presence and sexual-field conditions, self-arming once `entity.sexual` exists.

```yaml
# world/rules/rulebook/combat_modifiers.yaml
- id: poison_agility_penalty
  when: { buff_active: poisoned }
  then: { agility: "-10%" }

- id: paralysis_locks_actions
  when: { buff_active: paralysis }
  then: { actions_per_turn: 0 }

- id: fear_agility_and_accuracy_penalty
  when: { buff_active: fear }
  then: { agility: "-15%", accuracy: -10 }

- id: high_arousal_agility_accuracy_penalty
  when: { field: arousal, gte: 高度 }
  then: { agility: "-20%", accuracy: -15 }

- id: climax_in_progress_locks_actions
  when: { field: climax_phase, equals: 進行中 }
  then: { actions_per_turn: 0 }
```

The last two rows are design doc §6.4's own combat-coupling examples, transcribed with the `id` field
this change's discipline requires (the design doc's illustrative YAML omits IDs; this change's actual
table does not). `poison_agility_penalty` and `fear_agility_and_accuracy_penalty`'s specific percentages
are this change's own invented placeholder numbers — sourced from no `world_info.md` table, flagged
explicitly (Risks) for change 9/16's eventual balance pass, the same discipline change 5's D-4 already
used for its own placeholder `body_enhancement_basic` multiplier.

```python
# world/rules/combat_modifiers.py
"""Pure query function change 9 (dice-combat) calls at combat-resolution time.
Builds one context dict from whatever live handlers the entity actually has,
then runs every rule in combat_modifiers.yaml through the shared evaluator --
no branch anywhere distinguishes a buff-presence row from a sexual-field row.
"""

_RULES = load_rules(Path(__file__).parent / "rulebook" / "combat_modifiers.yaml")

def _build_context(entity) -> dict:
    context = {"active_buffs": set(entity.buffs.all().keys())}  # exact BuffHandler
                                                                  # accessor name
                                                                  # flagged for
                                                                  # implementer
                                                                  # verification,
                                                                  # per this
                                                                  # project's
                                                                  # established
                                                                  # discipline
    sexual = getattr(entity, "sexual", None)   # duck-typed: entity.sexual is a
    if sexual is not None:                      # change-3 placeholder (None) until
        context["arousal"] = sexual.arousal      # change 7 lands; this function
        context["climax_phase"] = sexual.climax_phase  # degrades gracefully, not by
                                                          # raising, when it is absent
    return context

def evaluate_combat_modifiers(entity) -> dict:
    """Returns a merged adjustment bundle, e.g. {"agility": "-28%", "accuracy": -25,
    "actions_per_turn": 0} -- change 9 interprets these against its own to-hit/
    damage formula. This function never writes to entity.traits or anywhere else;
    it is a pure read, exactly mirroring change 5's effective_value() discipline."""
    context = _build_context(entity)
    result: dict = {}
    for rule in _RULES:
        if evaluate_condition(rule.when, context):
            result = _merge_adjustments(result, rule.then)
    return result
```

**Why this degrades instead of failing today.** `entity.sexual` is `None` on every `LivingEntity` until
change 7 lands (change 3's D-10 placeholder). `_build_context()` only adds `arousal`/`climax_phase` keys
when `entity.sexual` is a real object, so the two sexual-field rules simply never match today (their
`when` clause references a context key that is absent, which `evaluate_condition()` treats as
"condition not satisfied," not an error) — mirroring change 4's D-5 pluggable-degradation pattern, not
inventing a new one. A self-arming test (D-7) proves this transitions to genuinely evaluating the moment
`entity.sexual` is real, the same "no-op today, tripwire tomorrow" shape change 3's D-9 and change 4's
D-5 already established.

**Alternative considered**: block this change on change 7 landing first, so `entity.sexual` is always
real. Rejected — design doc §11 places changes 6, 7, 8 in a strict sequence (6 → 7 → 8 → 9) specifically
so 6 lands *before* 7; reversing that to satisfy this table would contradict the roadmap's own stated
ordering and delay `combat_modifiers.yaml`'s existence for no structural reason, since the table's
buff-presence rows are fully real and testable today regardless.

### D-4. `buffs.yaml` + `buffs.py`: buff definitions, each configuring a subset of rate / bounds / decay,
mounted through `BuffHandler`/`BaseBuff` per §4's "use directly."

```yaml
# world/rules/rulebook/buffs.yaml
- key: poisoned
  duration: 300          # seconds; contrib's own duration/expiry mechanism
  tick_interval: 10
  stacking: refresh       # re-applying resets duration rather than stacking instances
  modifiers:
    rate: { target: hp, delta: -5 }   # -5 hp per tick -- rate of change

- key: paralysis
  duration: 30
  stacking: refresh
  modifiers: {}            # marker-only: no rate/bounds/decay of its own; read by
                             # combat_modifiers.yaml's buff_active condition and by
                             # change 8's future action-forbidding check

- key: fear
  duration: 60
  stacking: refresh
  modifiers: {}            # marker-only, same reasoning as paralysis

- key: conferred_growth_rate
  duration: null           # permanent -- a conferral is a standing fact, not a timed
                             # debuff (see D-5/D-6); null duration is this change's own
                             # convention for "does not expire on its own"
  stacking: unique_per_source  # judgment call: an entity could in principle receive
                                 # conferrals from two different sources; each is its
                                 # own instance keyed by source_key, not merged
  modifiers:
    rate: { target: magic_level_growth, scale_from_source: true }  # see D-5
```

`modifiers` names at most three keys — `rate`, `bounds`, `decay` — never anything resembling a combat
stat multiplier (`atk_phys`/`agility`/`defense` scaling stays change 5's `SkillHandler.effective_value()`
territory, per design doc §5.1's "third, independent layer" and this change's own Non-Goals). A
marker-only buff (`paralysis`, `fear`) has an empty `modifiers` mapping — its entire mechanical purpose is
being *present*, read by `combat_modifiers.yaml`'s `buff_active` condition and, later, by change 8's
action-forbidding check — not modifying any field's rate, bound, or decay directly.

```python
# world/rules/buffs.py
"""BuffHandler mount and the setting's BaseBuff subclass(es), driven entirely by
buffs.yaml -- per design doc S4, duration/tick/stacking are the contrib's job and
are not reimplemented here."""

class RulebookBuff(BaseBuff):
    """One concrete BaseBuff subclass, parameterized entirely by its buffs.yaml
    definition (looked up by self.key at apply time) rather than one Python
    subclass per buff -- there is no behavioral difference between "poisoned"
    and "fear" that Python code needs to express; the difference is entirely
    data (duration, tick_interval, modifiers). A hand-authored subclass per buff
    would duplicate this class four times over for zero behavioral gain.

    Flagged for implementer verification: the exact BaseBuff hook names
    (at_apply/at_tick/at_remove, or whatever Evennia 6.1.0's contrib actually
    exposes) are confirmed against the installed package before wiring the
    rate/bounds/decay application below, per this project's established
    verify-before-trusting discipline (changes 1-5)."""

    def at_tick(self):
        definition = BUFF_DEFINITIONS[self.key]
        rate_mod = definition.modifiers.get("rate")
        if rate_mod:
            _apply_rate_modifier(self.owner, rate_mod)   # see below

def _apply_rate_modifier(entity, rate_mod: dict) -> None:
    """Applies a per-tick delta to rate_mod['target']. When the target is one
    of entity.traits' gauge keys (hp/mp/sp), this writes into StaticTrait/
    GaugeTrait's mod component (change 3 D-7: reserved for BuffHandler,
    additive only, never a multiplier) via TraitHandler's own Mod API --
    flagged for implementer verification against the installed contrib's
    exact Mod/GaugeTrait interface. When the target is not a known trait key
    (e.g. magic_level_growth, sexual-state fields once change 7 exists), this
    function raises NotImplementedError with a message naming the owning
    change (change 7 for sexual-state fields, change 11b
    character-progression for magic_level_growth) rather than silently
    no-op'ing."""
    ...

def entity_active_buffs(entity) -> set[str]:
    """Thin wrapper naming the exact BuffHandler accessor this change's other
    modules (combat_modifiers.py) read -- isolates the one place that needs
    updating if the confirmed contrib API differs from BuffHandler.all()."""
    return set(entity.buffs.all().keys())

def blocks_action(entity) -> bool:
    """Declared seam for change 8's ActionResolver step 4 ('buffs forbidding
    action'). Returns True if any currently-active buff key is in a small,
    explicit BLOCKING_BUFF_KEYS set (paralysis, and climax-in-progress once
    change 7 supplies it). This change defines the query; change 8 decides
    when to call it and what 'forbidden' means for its own pipeline."""
    return bool(entity_active_buffs(entity) & BLOCKING_BUFF_KEYS)
```

**Mount** (`typeclasses/entities.py`, replacing change 3's placeholder, mirroring change 5's D-10 exactly):

```python
@lazy_property
def buffs(self):
    return BuffHandler(self)
```

`entity.buffs` is now a read-only computed property returning the handler instance — there is no
bare-assignment form, matching `entity.traits`/`entity.skills`/`entity.equipment`. **No raw payload is
ever assigned to `entity.buffs` or `entity.db.buffs` by this change's own code** — `BuffHandler`'s
internal storage (its own `dbkey`, expected to default to `"buffs"`, i.e. `entity.db.buffs`, per §4's
confirmation that duration/tick/stacking are already implemented) is the contrib's private concern, the
same way `TraitHandler`'s internal storage is change 3's contrib's private concern, not something this
change's code writes to directly. This satisfies hard requirement 2 by construction: there is no code
path anywhere in `world/rules/buffs.py` that assigns a dict to `entity.buffs` or hand-writes to
`entity.db.buffs`; every mutation goes through `BuffHandler`'s own `.add()`/`.remove()` API.

### D-5. The conferred growth-rate modifier is a buff instance, not a new sibling data model to
`ConferredSkillGrant`.

Change 5's D-6 built `ConferredSkillGrant` (`source_key`, `skill_key`, `trait_keys`, `scale`) for
Violet's ×10 partial 身體強化 conferral — a combat-stat multiplier, deliberately typed around
`trait_keys` and multiplicative `scale`, and explicitly *not* extended to cover the magic-growth-rate
half because that half is a rate-of-change concept (§6.4), squarely buff territory, not skill territory.

**Decision**: model the conferred growth-rate modifier as a **buff instance** of
`RulebookBuff` keyed `conferred_growth_rate`, carrying two instance-level values beyond its YAML
definition's shared tunables — `source_key` (Elosia's key) and `scale` (the fraction of the source's own
growth-rate multiplier Violet receives, e.g. `0.5` if the source-card's language of "百倍增幅" scaled down
means Violet gets half of whatever multiplier Elosia's own passive carries) — applied via:

```python
def grant_conferred_growth_rate(entity, source_key: str, scale: float) -> None:
    """The read-side-computation counterpart to change 5's grant_conferred():
    creates a RulebookBuff instance via BuffHandler.add(), not a bespoke
    dataclass, because design doc S6.4 assigns rate-of-change to buffs
    specifically. A plain, unconditional data write -- performs no ownership
    or resource check, exactly mirroring change 5's own grant_conferred()
    docstring. Change 8's ActionResolver (statue-parallel: whichever skill
    'casts' this conferral, analogous to 統御術's cast-time creation) is
    expected to call this after its own validation succeeds -- this function
    is the seam, not the cast."""
    entity.buffs.add("conferred_growth_rate", source_key=source_key, scale=scale)

def growth_rate_multiplier(entity) -> float:
    """Pure query, mirroring change 5's effective_value() discipline exactly:
    reads active buff state, returns a derived number, writes nothing back.
    Folds together every active conferred_growth_rate buff's scale (there may
    be more than one source in principle -- buffs.yaml's stacking:
    unique_per_source keeps each source's grant as its own instance) plus
    (declared, not built) whatever self-buff a future change might apply to
    represent an entity's own base growth rate. Returns 1.0 (no modifier) if
    no growth-rate buff is active."""
    multiplier = 1.0
    for buff in entity.buffs.all().values():           # exact accessor flagged
        if buff.key == "conferred_growth_rate":          # for verification, D-4
            multiplier *= buff.scale
    return multiplier
```

Why this is a buff and not a third dataclass alongside `ConferredSkillGrant`: reusing the identical
`source_key`/`scale` shape as a bespoke dataclass (call it `ConferredRateGrant`) would duplicate
`ConferredSkillGrant`'s structure while gaining nothing `BuffHandler` doesn't already provide — no
duration semantics, no stacking policy, no uniform place other buffs already live for a future reader to
find "every timed or standing effect on this entity" in one collection (`entity.buffs.all()`). Routing it
through `BuffHandler` instead means a `look`-style status display, a future dispel effect, or a save-file
inspection all find `conferred_growth_rate` in the exact same place they find `poisoned` or `fear`, with
no second lookup path to remember.

### D-6. What is out of scope, with a named owner: applying `growth_rate_multiplier()`'s output to an
actual XP/leveling event.

**Resolved during review.** At the time this design was first written, no roadmap item (§11) owned "how
`magic_level` actually increases as a character plays" — change 2's `RaceProfile.learning_multiplier`
(elf ×10.0) existed as lore data, but no change had yet built the progression mechanism that would read
it, let alone fold in a conferred buff's `scale`. That gap has since been closed at the roadmap level,
not just noted here: the coordinator added **change 11b (`character-progression`, depends on changes
5, 6, 11)** to §11, covering XP, magic-level growth, and skill improvement — guild merit and rank stay
change 16's. Change 11b is `growth_rate_multiplier()`'s consumer.

**Decision**: this change still builds `growth_rate_multiplier()` as a complete, tested, standalone query
function — proven correct against buff state alone, with a test constructing an entity holding a
`conferred_growth_rate` buff at `scale=0.5` and asserting the function returns `0.5`, and an entity with
no such buff returning `1.0` — and still does not wire it into any XP-gain code path, since change 11b
has not been proposed yet. Building the function here and having change 11b consume it later is the
correct split, not a compromise: it is the identical shape change 5's `effective_value()` had before
changes 8/9 existed to call it. Naming change 11b as the consumer now (rather than continuing to record
this as unclaimed, the way change 3 left `NPC.schedule`/`Monster.behaviour_tree` and change 5 left
`relations`/`persona`) is the one update this review round makes to this decision.

**Alternative considered**: deferring the entire mechanism a second time, on the reasoning that without a
progression system there is nothing real to test it against. Rejected — the task explicitly asks this
change to "design how a rate-of-change modifier is conferred from one entity to another," not to design
the progression system it will eventually feed; a pure, well-tested query function that returns the
right multiplier given buff state is a complete and independently verifiable unit of work, exactly the
same shape change 5's `effective_value()` was before change 8/9 existed to call it in anger.

### D-7. Test discipline: rule-ID-to-test-name mapping is mechanically checked, not just followed.

Design doc §10: "One test per rule ID. Test names mirror rule IDs one-to-one." **Decision**: a single
regression test, `test_every_rule_id_has_a_test()`, walks `combat_modifiers.yaml`'s loaded `Rule.id`
values and asserts a test function named `test_rule_<id>` exists in `test_combat_modifiers.py` (via
`inspect.getmembers` on the test module), and a symmetric test walks `buffs.yaml`'s buff keys against
`test_buff_<key>` in `test_buffs.py`. This makes "every rule has an ID and every ID has a unit test" a
property CI checks automatically the moment someone adds a tenth row to either YAML file without a
matching test function, rather than a discipline that only holds as long as code review catches its
absence — the same "structural guarantee, not a docstring" standard change 5's D-7 held itself to for
狀態偽裝's D2 compliance.

The two sexual-field rules get **two distinct tests, not one, each proving a different half of the
claim** (mirroring change 4's D-5 pluggable-check pattern, which likewise needed both a mocked test and a
real-import test to be convincing): a **unit test that runs today**,
`test_rule_high_arousal_agility_accuracy_penalty()`, feeding `evaluate_combat_modifiers()` a duck-typed
stub exposing `.arousal` (not a real `entity.sexual`, since `SexualState` does not exist yet) and
asserting the rule evaluates and produces the documented adjustment bundle right now — this proves the
condition grammar and the effect vocabulary work today, independent of change 7. A companion,
`test_high_arousal_rule_is_inert_without_sexual_state()`, asserts the same rule never fires while
`entity.sexual is None` (every entity's actual state today). Neither of these is sufficient on its own to
claim the rule will work against a *real* `SexualState`: a stub can be shaped however the test author
likes, and proves the matcher, not the eventual integration. A separate, **self-arming integration
test**, `test_high_arousal_rule_fires_once_sexual_state_exists()`
(`pytest.importorskip("world.rules.sexual_state")`), is therefore also required, living in its own test
module so it cannot be quietly folded into or dropped alongside the unit test: it skips — reported as
skipped, not passed — for the entire lifetime of this change and until change 7 lands, at which point it
starts asserting the rule fires against a genuinely live `entity.sexual`. A verification task confirms
this test currently reports skipped rather than passed, the same "a pass here would mean something is
silently wrong" discipline change 4's D-5 applied to its own skill-registry self-arming test.

## Risks / Trade-offs

- **[Risk] `evaluate_condition()`'s `gte` comparator assumes the caller hands it an already-orderable
  value for ordered-level fields (e.g. an ordinal, not the bare string `"高度"`), which change 7 might
  get wrong by passing the raw Chinese string through unordered.** → Mitigation: D-2 documents this
  explicitly as the caller's responsibility, and a test constructs a context with a plain `IntEnum`-like
  stand-in for `arousal` and asserts `gte` compares correctly against it — proving the contract works for
  *some* orderable type without asserting anything about change 7's specific `Trait` subclass, which does
  not exist yet.
- **[Risk] `poison_agility_penalty` and `fear_agility_and_accuracy_penalty`'s specific percentages
  (-10%/-15%) are invented placeholder numbers, not sourced from `world_info.md`.** → Documented
  explicitly in D-3 as a judgment call, flagged for change 9/16's eventual balance pass, mirroring change
  5's D-4 treatment of its own invented `body_enhancement_basic` multiplier.
- **[Risk] `RulebookBuff` being one generic class parameterized by `buffs.yaml` means a buff needing
  genuinely different Python behavior (not just different numbers) has no natural home — e.g. a future
  buff that needs a custom `at_remove` side effect.** → Accepted for this change's seed set: every buff
  here (poisoned/paralysis/fear/conferred_growth_rate) is fully expressible as rate/bounds/decay/marker
  data. A future buff needing bespoke behavior can subclass `RulebookBuff` directly — nothing in this
  design prevents that; it is simply not needed by today's seed set.
- **[Risk] `_apply_rate_modifier()`'s `NotImplementedError` branch for non-trait targets (sexual-state
  fields, `magic_level_growth`) means `poisoned`'s hp-rate modifier is the only rate modifier this change
  can actually exercise end-to-end today; `conferred_growth_rate`'s own rate modifier has no real target
  to write into yet.** → Accepted and stated directly in D-6: `growth_rate_multiplier()` is tested as a
  pure query against buff state, independent of any trait/field it would eventually feed, which is the
  complete and correct scope for a change whose progression consumer (change 11b,
  `character-progression`) has not been proposed yet.
- **[Risk] `BuffHandler`'s exact accessor names (`all()`, `.add()`, the default `dbkey`) are assumed, not
  confirmed against a locally installed Evennia 6.1.0 package.** → Flagged for implementer verification
  throughout D-3/D-4/D-5, consistent with changes 1–5's identical discipline for every other
  Evennia-contrib API assumption; design doc §4 confirms the classes exist and are usable directly, not
  every method name.
- **[Risk] Marker-only buffs (`paralysis`, `fear`) carry an empty `modifiers: {}` in `buffs.yaml`, which
  could look like a forgotten entry rather than a deliberate "presence-only" design to a future reader.**
  → Mitigation: D-4 documents the reasoning inline in the YAML's own comments and in this design doc;
  `blocks_action()`'s `BLOCKING_BUFF_KEYS` set and `combat_modifiers.yaml`'s `buff_active` rows are the
  two real consumers of a marker buff's presence, both named explicitly.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/` currently contains only change 3's `traits.py`. The only sequencing concerns are
operational:

- This change must land after change 3 (needs `LivingEntity`, the `buffs` seam attribute, and the
  `mod`-component boundary importable).
- This change should land in a way that leaves `world/rules/rulebook/schema.py` and its handoff docstring
  in place for change 7 to import when it is proposed — no edit to change 5's or change 4's artifacts is
  required or made by this change.
- Change 9 (`dice-combat`) is expected to call `evaluate_combat_modifiers()`; change 8
  (`action-resolver`) is expected to call `blocks_action()` and `grant_conferred_growth_rate()`; change 11
  (`world-clock`) is expected to call this change's buff-tick hook at its own chosen point in the fixed
  settlement order. None of these calls exist yet — this change only guarantees the callables exist with
  the documented signatures.

## Open Questions

- **Resolved: change 11b (`character-progression`) owns wiring `growth_rate_multiplier()`'s output into
  an actual `magic_level` progression/XP event.** No longer unassigned — the coordinator added change 11b
  (depends on changes 5, 6, 11; covers XP, magic-level growth, and skill improvement, with guild merit and
  rank staying change 16's) to §11 specifically to close this gap. What remains genuinely open, since
  change 11b has not itself been proposed yet: the exact call shape change 11b will use to read
  `growth_rate_multiplier()` (once per level-up check, once per XP-gain event, or some other cadence) is
  change 11b's own design decision, not fixed by this change.
- **Should `_apply_rate_modifier()`'s target vocabulary (currently just `entity.traits`' gauge keys) be
  extended once change 7 exists, so a buff can modify a `SexualState` field's rate/bounds/decay
  directly?** Left to change 7's own author to decide when `SexualState`'s concrete field API exists;
  this change's `NotImplementedError` branch names change 7 explicitly rather than guessing at its
  eventual interface.
- **Exact `BuffHandler`/`BaseBuff` method and hook names** (`.all()`, `.add()`, `at_tick`, the default
  `dbkey`) are left to the implementer to confirm against the installed Evennia 6.1.0
  `evennia.contrib.rpg.buffs` source, consistent with the verification discipline changes 1–5 already
  established — design doc §4 confirms the classes exist and are usable directly, but does not itself
  pin every method signature.
