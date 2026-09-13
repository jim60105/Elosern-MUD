# Declarative Item Effect Model — Design

**Date:** 2026-09-14
**Status:** Approved
**Scope:** Replace the closed `ItemEffectKey` vocabulary with a declarative,
per-item effect list (which stat, how much, which targets); decouple the
shared target resolver from `SkillDef`; extend item-use settlement to
multiple effects and multiple targets.

---

## 1. Context and Problem

A usable item today declares exactly one member of a four-member closed
enumeration:

```python
ItemUseMechanics(effect_key=ItemEffectKey.SELF_HEAL, consumable=True, combat_allowed=True)
```

`world/rules/rulebook/item_effects.yaml` then stores one `amount` per effect
key, and `world/rules/items.py` hard-codes the rest: a `_EFFECT_GAUGES` map
from effect key to gauge name, a dedicated `if` branch for
`blessed_cleansing`, a per-gauge rejection-reason table, and a per-gauge
Traditional Chinese noun for the event text. Every item is settled against
the acting entity alone — `ItemUseRequest` carries no target field at all.

Three consequences block the world-building in `docs/lore/items.md`:

1. **Every new effect is a schema change.** 解毒, 回復體力值, 持續回春, and
   催情 (快感推進) are all flagged in the lore document as blocked behind "a
   dedicated enumeration extension and design review". The 性玩具 category is
   blocked on the same list.
2. **One item can express exactly one effect.** 靈露 is specified as an
   extreme aphrodisiac whose wound-closing is a downstream consequence — two
   effects on one drink. The model cannot hold it.
3. **Nothing can target anyone else.** 女神之吻聖霧 (a spray), 情欲香爐 (a
   censer whose smoke fills a space), and any future thrown or offensive
   consumable have no representation.

The skill system already solved the general shape of this problem: typed
effects, a handler dispatch table, and a combat-agnostic target resolver in
`world/rules/targeting.py`. Items never connected to any of it.

The project has no released users (`AGENTS.md`), so no compatibility layer or
data migration is required: the old vocabulary is deleted outright.

---

## 2. Goals and Non-Goals

**Goals**

- An item declares an ordered list of 1..N effects; each effect names what it
  changes, by how much (signed), and whom it reaches.
- The model covers every effect the lore document currently has on its
  pending list, with no further enumeration extensions.
- Item targeting reuses the shipped target resolver rather than growing a
  second one.
- The target resolver stops depending on `SkillDef`.

**Non-Goals**

- `ItemKind.TOY` (a presentation category) and the ammunition consumption
  mechanic. Both are flagged separately in the lore document and neither is
  an effect-model concern.
- Equipment effects (`equipment_effects.yaml`). Untouched.
- Duration-bearing item effects. A timed stat boost is a buff; items reach it
  through `apply_status`, never through a direct stat write.
- New item content. Only the four shipped usable items are migrated; adding
  the lore catalogue is separate work on top of this model.

---

## 3. Data Model

### 3.1 Registry side

`ItemEffectKey` is deleted. `ItemUseMechanics` keeps only its two behavioral
flags:

```python
@dataclass(frozen=True)
class ItemUseMechanics:
    consumable: bool
    combat_allowed: bool
```

"This item is usable" remains `use_mechanics is not None`. The registry now
plays exactly the role it plays for equipment: it declares the *shape* of the
mechanic and owns no magnitude. The binding to the rulebook is the item's own
key, mirroring `EquipmentModifierKey`'s identity rule without needing a second
enumeration to express it.

### 3.2 Rulebook side

`world/rules/rulebook/item_effects.yaml` is re-keyed by **item key**:

```yaml
item_use_seconds: 6

items:
  healing_potion:
    effects:
      - { stat: hp, amount: 40, scope: self }
  greater_healing_potion:
    effects:
      - { stat: hp, amount: 120, scope: self }
  mana_potion:
    effects:
      - { stat: mp, amount: 40, scope: self }
  baptismal_holy_water:
    effects:
      - { remove_status: negative, scope: self }
```

A composite item — the shape the current model cannot express — reads:

```yaml
  censer_of_desire:
    effects:
      - { stat: pleasure, amount: 10, scope: all-allies }
      - { apply_status: aphrodisiac_mist, scope: all-allies }
```

### 3.3 Typed effects

A new module `world/rules/item_effects.py` owns the vocabulary, the loader,
and the frozen dataclasses. It is a new module rather than more of
`world/rules/items.py` because that file is already 730 lines and owns a
different responsibility (settlement, journalling, and the clock seam).

```python
class ItemStat(StrEnum):
    HP = "hp"
    MP = "mp"
    SP = "sp"
    PLEASURE = "pleasure"


class ItemTargetScope(StrEnum):
    SELF = "self"
    SINGLE = "single"
    ALL_ALLIES = "all-allies"
    ALL_ENEMIES = "all-enemies"
    ALL = "all"


@dataclass(frozen=True)
class GaugeAdjustEffect:
    stat: ItemStat
    amount: int                 # non-zero, |amount| <= MAX_EFFECT_AMOUNT
    scope: ItemTargetScope


@dataclass(frozen=True)
class StatusApplyEffect:
    status: str                 # a concrete BUFF_DEFINITIONS key
    scope: ItemTargetScope


@dataclass(frozen=True)
class StatusRemoveEffect:
    selector: str               # a concrete key, or all/positive/negative
    scope: ItemTargetScope


ItemEffect = GaugeAdjustEffect | StatusApplyEffect | StatusRemoveEffect


@dataclass(frozen=True)
class ItemEffectProfile:
    effects: tuple[ItemEffect, ...]     # ordered; order is application order
```

Each YAML entry carries exactly one verb key — `stat`, `apply_status`, or
`remove_status` — and the verb selects the dataclass. Two verbs, or none,
fails the load.

Splitting apply and remove into two verbs rather than one `status` key plus a
mode flag is deliberate: the three selectors are meaningful only when
removing ("apply every status" is not a thing), so the split makes the
illegal combination unrepresentable instead of a cross-field rule the loader
has to remember to check.

### 3.4 Status selectors

| Selector | Meaning |
| --- | --- |
| `negative` | every active debuff-polarity status |
| `positive` | every active buff-polarity status |
| `all` | both |
| a concrete key | exactly that status |

`BuffDefinition.polarity` is closed over `{"buff", "debuff"}`, so the three
selectors partition the space with no unreachable remainder.

The selectors are spelled `positive`/`negative` rather than reusing
`buff`/`debuff` because `remove_status: buff` reads as "remove the status
named buff" — the selector namespace and the key namespace share one field,
so they must not share vocabulary.

`remove_status: negative` is the shipped 受洗聖水 behavior, byte-for-byte:
it resolves to the existing `cleanse_debuffs` path.

### 3.5 Loader validation

Mirrors `equipment_effects.py`'s two-way alignment, at import time:

1. The `items` key set equals exactly the set of registry keys whose
   `use_mechanics is not None`. An orphan entry and a missing entry both fail
   startup.
2. Every profile carries at least one effect.
3. `stat` requires a non-zero integer `amount` with `abs(amount)` at most
   `MAX_EFFECT_AMOUNT` (9999, the existing bound).
4. `apply_status` requires a concrete `BUFF_DEFINITIONS` key; a selector is
   rejected.
5. `remove_status` accepts a concrete key or one of the three selectors.
6. `scope` is an `ItemTargetScope` member. Absent means `self`.
7. `item_use_seconds` keeps its existing bounds check.

### 3.6 Migration of the shipped items

| Item | Old effect key | New effect list |
| --- | --- | --- |
| `healing_potion` | `self_heal` | `[{stat: hp, amount: 40, scope: self}]` |
| `greater_healing_potion` | `greater_heal` | `[{stat: hp, amount: 120, scope: self}]` |
| `mana_potion` | `mana_restore` | `[{stat: mp, amount: 40, scope: self}]` |
| `baptismal_holy_water` | `blessed_cleansing` | `[{remove_status: negative, scope: self}]` |

Magnitudes are unchanged, so no balance shifts with this change.

### 3.7 Coverage of the lore backlog

| Lore-flagged effect | Representation |
| --- | --- |
| 解毒 | `{remove_status: poisoned}` |
| 回復體力值 (SP) | `{stat: sp, amount: +N}` |
| 持續回春 | `{apply_status: <regen buff>}` |
| 催情 `pleasure_surge`, three bands | `{stat: pleasure, amount: <band value>}` |
| 靈露 (aphrodisiac plus wound closing) | `[{stat: pleasure, amount: N}, {stat: hp, amount: M}]` |
| 催情霧 | `{apply_status: aphrodisiac_mist}` |
| 女神之吻聖霧 (a spray) | `{stat: pleasure, amount: N, scope: all-allies}` |
| Future thrown damage item | `{stat: hp, amount: -N, scope: single}` |
| Future dispel item | `{remove_status: positive, scope: all-enemies}` |

None of these requires a further enumeration extension. The only thing a new
status effect still requires is a `buffs.yaml` definition, which is already
ordinary data work.

---

## 4. Target Resolution Refactor

### 4.1 The coupling to remove

`world/rules/targeting.py` documents itself as "combat-agnostic target
validation for deterministic actions", but:

| Coupling | Location |
| --- | --- |
| All four validators take `skill: SkillDef`; `_validate_presence` and `_validate_alive` never read it | `targeting.py:131-137` |
| `resolve_targets` special-cases `SkillCategory.SEXUAL_ACT` to forbid self-casting — a general resolver that knows about one skill category | `targeting.py:222-236` |
| `ActionContext.is_in_range(actor, target, skill)` carries a skill both implementations ignore (`RoomActionContext` returns `True`; `BattlefieldActionContext` reads only `fled`) | `targeting.py:38`, `combat.py:123` |
| `damage_requires_battlefield()` — a skill-effect combat-state gate — lives in the targeting module | `targeting.py:99` |
| `resolve_targets(request: Any, ...)` reaches into `request.actor` / `request.context` with no declared contract | `targeting.py:200` |

### 4.2 `TargetRequirement`

One frozen value object becomes the resolver's only input contract:

```python
@dataclass(frozen=True)
class TargetRequirement:
    spec: TargetSpec
    faction: FactionConstraint = FactionConstraint.ANY
    forbid_self: bool = False
```

`SkillDef` gains a `target_requirement` property that produces one, with
`forbid_self = (self.category is SkillCategory.SEXUAL_ACT)`. The sexual-act
rule is thereby stated by the skill that owns it, and the resolver stops
recognizing skill categories entirely.

Item scopes map as:

| Scope | `spec` | `faction` | Candidate source |
| --- | --- | --- | --- |
| `self` | `SELF` | `SELF_ONLY` | the actor |
| `single` | `SINGLE` | `ANY` | the player's explicit target |
| `all-allies` / `all-enemies` / `all` | `AREA` | `ANY` | `expand_target_shorthand` |

### 4.3 Signature changes

| Before | After |
| --- | --- |
| `resolve_targets(request, skill, candidates)` | `resolve_targets(actor, context, requirement, candidates)` |
| `candidate_rejection(request, target, skill)` | `candidate_rejection(actor, context, requirement, target)` |
| `_validate_*(request, target, skill)` | `_validate_*(actor, context, requirement, target)` |
| `ActionContext.is_in_range(actor, target, skill)` | `ActionContext.is_in_range(actor, target)` |

Dropping the `skill` parameter from `is_in_range` is behavior-preserving:
neither implementation reads it.

`damage_requires_battlefield()` moves out of `targeting.py` to a new
`world/rules/action_gates.py`. It is a skill-effect gate, not target
validation; `action.py` and `action_preview.py` (its only callers) import it
from the new home. `world/rules/tests/test_action_pipeline_rejections.py`
asserts against its source text via `inspect.getsource`, so that test follows
the move.

### 4.4 Blast radius

Non-test callers are four: `action.py:394`, and `action_preview.py:215`,
`:222`, `:327`. The real cost is `world/rules/tests/test_targeting.py`, whose
~15 call sites all change signature.

---

## 5. Item-Use Settlement

### 5.1 Request shape

```python
@dataclass(frozen=True)
class ItemUseRequest:
    actor: Any
    item_key: str
    target: Any | None = None
```

The player supplies **at most one** explicit target. `self` scopes resolve to
the actor, `all-*` scopes expand through the context, and `single` scopes
consume this field. Unlike a skill, an item's reach is a property of the item
and is fixed in the rulebook — the player never selects an area shorthand.

### 5.2 Preflight

`preflight_item_use(request, *, in_combat, context)` gains the context
parameter (`BattlefieldActionContext` in a session; `use_item` constructs a
`RoomActionContext` from the actor's location otherwise).

Order:

1. Registry lookup, `use_mechanics` present, `combat_allowed` versus mode,
   canonical inventory holds the key, actor alive — all unchanged.
2. Look up the item's `ItemEffectProfile`.
3. Per effect, resolve its target set through the refactored resolver.
4. Per (effect, target) pair, compute an `ItemEffectStep` carrying the
   **actually applicable** magnitude for current state.
5. If no step is effective, reject. If any step is effective, proceed.

### 5.3 Effectiveness

| Effect | Effective when | Applied magnitude |
| --- | --- | --- |
| gauge, positive amount | `current < maximum` | `min(amount, maximum - current)` |
| gauge, negative amount | `current > 0` | `min(abs(amount), current)` |
| pleasure, positive | `current < 100` | clamped delta |
| pleasure, negative | `current > 0` | clamped delta |
| `apply_status` | the target is not equipment-immune to it | n/a |
| `remove_status` | the selected instance set is non-empty | count removed |

`apply_status` is effective even when the target already carries the status:
`BuffDefinition.stacking` defaults to `refresh`, so re-applying renews the
duration, which is a real change. The one ineffective case is the
equipment-immunity backstop in `_add_buff`, which refuses the write outright
for a debuff the target's equipment immunizes against.

`remove_status` resolves its selector against **live buff instances**, not
definition keys: `_remove_buff_keys` takes instance keys (`buff.buffkey`),
exactly as `cleanse_debuffs` already does. A concrete-key selector filters
active instances by `definition_key`, and the three polarity selectors filter
by `BUFF_DEFINITIONS[...].polarity`. One buff definition with several live
instances therefore loses all of them.

An ineffective step is skipped silently and logs nothing; only what actually
happened is reported.

### 5.4 Rejection reasons

Each ineffective step names its own reason code. When the whole use is
rejected: if every step named the same code, that code is returned;
otherwise `no_effect`. Single-effect, single-target items therefore keep
their exact current behavior, and the shipped spec scenarios for `hp_full`,
`mp_full`, and `no_debuffs` survive unchanged.

`ItemUseReason` gains `SP_FULL`, `PLEASURE_FULL`, `NO_EFFECT`, `NO_TARGET`
(a `single` scope with no target supplied), and `TARGET_INVALID` (the
resolver rejected the supplied target). `world/rules/service_messages.py`
gains a Traditional Chinese message for each.

### 5.5 Plan shape

```python
@dataclass(frozen=True)
class ItemEffectStep:
    effect: ItemEffect
    target: Any
    amount: int = 0                      # signed, gauge family
    status_keys: tuple[str, ...] = ()    # status family


@dataclass(frozen=True)
class ItemUsePlan:
    actor: Any
    item_key: str
    consumable: bool
    mirror_pk: int | None
    steps: tuple[ItemEffectStep, ...]
```

The plan stays fully computed before any write, as today.

### 5.6 Appliers

Every effect family routes through one entry point; no effect gains a second
increment path.

| Family | Entry point | Current state |
| --- | --- | --- |
| hp / mp / sp | `_write_gauge` (the trait handler clamps) | exists |
| pleasure | `_apply_pleasure_gain` | **private to `action.py`, yet already imported across modules** by `world/rules/defeat_aftermath.py:47` — extract to `world/rules/pleasure.py`, both callers import it |
| `apply_status` | `buffs._add_buff` | **private** — publish as `apply_buff()`; its equipment-immunity no-write backstop already guards it |
| `remove_status` | one new `buffs.remove_by_selector()` over the existing `_remove_buff_keys` | `cleanse_debuffs` is re-expressed as `remove_by_selector(entity, "negative")` so both callers keep one semantics |

A buff whose definition declares `stacking: unique_per_source` requires a
`source_key`. Note that `source_key` alone does **not** produce independent
instances: `_add_buff` keys the handler entry on `instance_key or
definition_key` and carries `source_key` only as opaque cache data. Per-source
stacking therefore needs an explicit instance key, exactly as
`grant_conferred_growth_rate` already does
(`instance_key=f"conferred_growth_rate:{source_key}"`). Item-applied statuses
pass `source_key=f"item:{item_key}"` **and**
`instance_key=f"{status}:item:{item_key}"` for a `unique_per_source`
definition, so two different items granting the same status stack
independently while re-using one item refreshes its own instance.

`world/rules/action.py:1380`'s `_zero_pleasure` is a **second** direct writer
of `entity.sexual.pleasure.base`, used by the drain handler. It must stay
separate rather than being folded into the gain entry: routing a zeroing
through `apply_pleasure_gain(entity, -current)` would trip that function's
`was_at_critical_point` branch and push a target sitting at 接近 into 進行中 —
the opposite of what draining someone's pleasure to zero means. It moves into
`world/rules/pleasure.py` alongside the gain entry, so the checkable invariant
is "every pleasure write lives in this one module", not "every pleasure write
is one function".

A negative pleasure amount goes through the same `apply_pleasure_gain`
entry, clamped at zero. The arousal / wetness / climax cascade inside that
function is gated on an *increase* and therefore does not fire on a
reduction, which is the intended reading: suppressing arousal must not walk
the climax state machine forward.

### 5.7 Event log

One successful use emits one `EventLog` containing one `item_used` entry per
**effective** step. Entry data becomes:

- gauge family: `{item_key, consumable, target, stat, amount}`
- status family: `{item_key, consumable, target, status_keys, count}`

The `effect_key` field is removed. `targets` on the `EventLog` becomes the
deduplicated set of touched entities rather than always the actor.

### 5.8 Rollback journal

This is the highest-risk part of the change. `ItemTouchedJournal.capture()`
today snapshots one entity's traits, inventory, quest log, and buffs. With
multiple targets:

- inventory and quest log remain actor-only (only the actor consumes);
- traits and buffs are captured **per touched target**;
- a **sexual-state surface** is added, because a pleasure write moves
  `pleasure`, `arousal`, `wetness`, and `climax_phase` together;
- the **in-process cache drop runs per touched target too**. `restore()` today
  calls `_refresh_advance_entity_caches(actor)`, which clears the trait cache
  *and* pops the memoized `entity.sexual` handler
  (`world/rules/clock.py:561-580`). `restore_traits` alone clears only the
  trait cache, so a per-entity restore that skips the handler pop would roll
  back a companion's stored sexual state while leaving a stale in-memory
  `companion.sexual` readable in the same process — precisely the failure
  `_refresh_advance_entity_caches` exists to prevent.

`restore()` walks every captured entity. The combat path
(`combat.py:659`) folds the multi-entity journal into its existing outer
rollback contract; the round-occupancy rule is unchanged — a multi-target
item still consumes exactly one round.

---

## 6. Consumer Changes

| Location | Change |
| --- | --- |
| `commands/items.py` | `使用 <item_key> [target]`; a `single` scope with no target rejects as `no_target` |
| `web/webclient/actions/service_actions.py:503` | the use payload gains an optional target |
| `world/rules/combat_session.py:1235`, `:1248` | both `ItemUseRequest` constructions pass the target and the battlefield context |
| `world/rules/service_view.py:770` | builds a `RoomActionContext` for the descriptor preflight |
| `world/rules/service_messages.py` | five new reason messages |
| `docs/lore/items.md` | 第六層 (使用效果欄位) rewritten; the pending-effect notes in 藥劑 and 性玩具 updated to point at the new model |
| `docs/development/adding-items.md` | §1 table, §2 question 4, and §5 rewritten |
| `openspec/specs/item-use-resolution/spec.md` | delta rewriting the mechanics-declaration, preflight, event-log, and blessed-cleansing requirements |

---

## 7. Testing

- **Loader** (`world/rules/tests/test_item_effects_rulebook.py`, rewritten):
  orphan entry, missing entry, zero amount, over-bound amount, two verbs in
  one entry, no verb, selector under `apply_status`, unknown status key,
  unknown scope, unknown stat.
- **Preflight**: per-stat full rejection; the mixed-code fallback to
  `no_effect`; `no_target`; `TARGET_INVALID`; a composite item where one
  effect is ineffective and one is not proceeds and applies only the latter.
- **Settlement**: signed gauge writes clamp at both ends; pleasure positive
  and negative through the single entry point; apply/remove status including
  each selector; the equipment-immunity backstop refusing an `apply_status`.
- **Multi-target**: an `all-allies` item reaching every co-located ally out
  of combat and every team member in a session; an `all-enemies` item in a
  session; a room with no valid candidates.
- **Rollback**: fault injection after a multi-target partial application
  restores traits, buffs, and sexual state on **every** touched entity plus
  the actor's inventory and mirror.
- **Targeting refactor**: the existing `test_targeting.py` suite ported to
  the new signatures, plus a test that the resolver module no longer imports
  `SkillCategory`.
- **Regression**: all four migrated items reproduce their current magnitudes,
  reason codes, and single-entry event logs.

---

## 8. Risks

| Risk | Mitigation |
| --- | --- |
| Multi-entity rollback is the subtlest part of the change and the easiest to get silently wrong | Fault-injection tests per surface per target; extend the shipped injection pattern rather than inventing one |
| The targeting refactor touches the skill pipeline, which items do not otherwise need | Behavior-preserving by construction (dropped parameters are unread); the existing suite is the regression net |
| Extracting `_apply_pleasure_gain` moves code the sexual-act pipeline depends on | Pure move plus import; the function body is unchanged and its existing tests cover it |
| Negative pleasure is a new direction through a function written for gains | Explicit tests that the arousal/climax cascade does not fire on a reduction |
