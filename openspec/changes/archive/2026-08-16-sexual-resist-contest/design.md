## Context

`docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` §4 ("The Resist Contest") and
`2026-08-15-sexual-pleasure-model-design.md` §3.5 ("No extension cap; a resist opening instead") are
the source design for this proposal. Both are part of the six-document
`2026-08-15-sexual-act-system-overview-design.md` set; this is proposal `B6a` in that set's §4.2
implementation sequence.

Three pieces of shipped state this proposal reads without modifying:

- `world/rules/disengage.py::_attempt_flee` — the existing agility-contest idiom
  (`roll_d100() + actor_agility >= COMBAT_YAML["to_hit"]["defender_constant"] + pursuer_agility`,
  `defender_constant` is `51`), and `_adjusted_agility`, which reads
  `entity.skills.effective_value("agility")` through `evaluate_combat_modifiers_no_create()`.
- `world/rules/affinity_config.py` — `AffinityStage` (`id`, `floor`, `name`, `look_flavor`) and
  `get_config().stage_for_value(value) -> AffinityStage`, the seven shipped stages (`初識` floor 0
  through `絕對羈絆` floor 100), and `RelationHandler.stage_for(player) -> AffinityStage` mounted at
  `npc.relations` (`typeclasses/entities.py::LivingEntity.relations`).
  `apply_affinity_change` in `world/rules/affinity.py` further restricts the *writer* side to
  `isinstance(npc, NPC)`; this proposal only *reads* `stage_for`, which is defined on the shared
  `RelationHandler` mounted for every `LivingEntity`, but is only meaningful for an `NPC` resister —
  see Decision 4.
- `world/rules/sexual_state.py::SexualState` — `climax_phase` (an `OrderedLevelTrait` over
  `未達/接近/進行中/餘韻`) and `climax_turns` (an int, already shipped by `climax-settlement`,
  incremented once per settlement point spent in `進行中` and reset to `0` the moment `climax_phase`
  leaves it). No new field is added to `SexualState` by this proposal.

No caller of `resist_verdict()` exists yet. `sexual-act-effects` (`B5`) and `sexual-resist-turn-cost`
(`B6b`) are the proposals that will call it from a live act cast; `climax-settlement`'s own design
doc explicitly named this proposal as the deferred owner of "the resist opening at the sixth climax
turn". This proposal's scope stops at a correct, fully tested, callable verdict.

## Goals / Non-Goals

**Goals:**
- One pure function, `resist_verdict()`, that returns whether a resisting participant successfully
  refuses an act, given only the two participants and an injectable RNG.
- The two `auto_comply` conditions (affinity stage, climax-turn short circuit) are checked before any
  roll, so a guaranteed outcome never depends on `rng`.
- The ordinary contest reuses the shipped `to_hit` formula shape and constant exactly, and reads
  through `evaluate_combat_modifiers_no_create()` so combat-state effects (arousal, poison, buffs) apply to it
  automatically, with no new rule authored in `combat_modifiers.yaml`.
- Fully deterministic under an injected RNG, matching the `apply_event(rng=...)` and
  `_attempt_flee`/`roll_d100()` precedent.

**Non-Goals:**
- No act, effect handler, or turn-cost logic. This proposal has no caller in production code; only
  its own tests invoke `resist_verdict()`. Wiring it into an actual act cast, spending turns, and
  applying the affinity penalty on a forced act are `sexual-resist-turn-cost`'s (`B6b`) job.
- No change to `SexualState`. `climax_turns` and `climax_phase` are read, not written, and no new
  attribute is added.
- No change to `affinity_config.py`, `affinity.py`, or `affinity.yaml`. The affinity *modifier for
  resistance* is new data owned entirely by this proposal's own `sexual_resist.yaml`, keyed by the
  existing stage `id`s; it does not touch the existing gain/cap/budget system.
- No monster-initiated resistance modelling beyond "a `Monster` resister never auto-complies and
  always uses the plain stat contest" (Decision 4). Monsters do not initiate sexual acts in this
  document set's scope (`overview-design.md` §6); this proposal only needs to define how a monster
  behaves as the resisting party.

## Decisions

### Decision 1 — `resist_verdict()` is two-party, not battlefield-aware

`_attempt_flee(actor, battlefield)` scans every opposing, living, non-fled battlefield member to
find the fastest pursuer, because fleeing must beat *the whole opposing team's* fastest response. A
sexual act's resist check has exactly one resister per call — the participant deciding whether to
refuse a specific role in a specific act — so `resist_verdict(actor, resister, *, rng=roll_d100)`
takes no `battlefield` parameter at all. An `AREA` act with several resisting participants (per the
resolution design's participant model) calls this function once per resister, not once for the
whole act.

**Alternative considered:** accept a `battlefield` parameter for future flexibility. Rejected —
nothing in the shipped design ever needs a third party's stats to resolve one resister's contest, and
an unused parameter this codebase's own conventions would flag as dead weight (`AGENTS.md`: no
speculative surface for hypothetical future requirements).

### Decision 2 — Both contest scores blend `agility` and `atk_phys`, not `agility` alone

`_attempt_flee` uses agility alone because fleeing is purely a speed contest. Resisting a hold is
not: `agility` for the *speed* to break away, `atk_phys` for the *strength* to physically break
free. `sexual_resist.yaml` declares `agility_weight` and `atk_phys_weight` (non-negative, summing to
`1.0`, validated at load); each participant's score is
`effective_value("agility") * agility_weight + effective_value("atk_phys") * atk_phys_weight`.

**The two stats are read through `evaluate_combat_modifiers_no_create()` with two different, stat-specific
treatments — this is not a single shared "percentage/flat adjustment path".** Every existing
`agility`-producing row in `combat_modifiers.yaml` (`high_arousal_agility_accuracy_penalty`,
`fear_agility_and_accuracy_penalty`, `poison_agility_penalty`, `reincarnation_boon_yuka_agility_
bonus`) authors a **percentage string** (e.g. `"-20%"`), and `agility`'s sole existing consumers
(`disengage.py::_adjusted_agility`, `combat.py::_to_hit`) both apply it via
`combat._apply_percent_mod(base, modifiers.get("agility"))`. Every existing `atk_phys`-producing row
(`retainer_martial_training_atk_phys_bonus`, `dual_wield_style_atk_phys_bonus`) authors a **flat
integer** (`atk_phys: 5`), and its sole existing consumer, `combat.py::_adjusted_attack`, adds it
directly: `float(attack) + evaluate_combat_modifiers(entity).get("atk_phys", 0)` — never through
`_apply_percent_mod`, which raises `TypeError` on a non-string argument. The blended-score helper
this proposal adds MUST mirror both existing consumers exactly, one per stat: `agility` through
`_apply_percent_mod`, `atk_phys` as a flat addend — never the same helper applied to both.

**Alternative considered:** reuse `_adjusted_agility` verbatim (agility-only). Rejected per the
approved design (`sexual-act-resolution-design.md` §4.1 names both stats explicitly); an
agility-only contest would make a strength-built character no better at resisting than a
frail one, which reads wrong for a physical-restraint scenario.

### Decision 3 — Affinity modifier and `auto_comply` are new data, not a change to `affinity_config.py`

The seven shipped affinity stages (`affinity_config.py`) are a closed, validated table (`daily_interaction_cap`, `cap_breaks`, `stages` — exactly seven, floors
`0/10/30/50/70/90/100`). This proposal does not add a field to that schema. Instead,
`sexual_resist.yaml` declares its own table keyed by the existing stage `id` strings
(`acquaintance`, `familiar`, `warm`, `trusted`, `bonded`, `beloved`, `absolute_bond`):

```yaml
agility_weight: 0.6
atk_phys_weight: 0.4
climax_turn_auto_comply_limit: 5
affinity_resist_modifier:
  acquaintance: 15
  familiar: 10
  warm: 5
  trusted: 0
  bonded: -10
  beloved: { auto_comply: true }
  absolute_bond: { auto_comply: true }
```

A positive modifier *raises* the resister's score (easier to refuse a stranger); `bonded` goes
negative (a companion the player is closer to resists forcing *less* effectively — read as
reluctance to fight back, not literal weakness). `beloved` (`至愛`, floor 90) and `absolute_bond`
(`絕對羈絆`, floor 100) replace the number with `auto_comply: true`. Validated at load: every one of
the seven stage `id`s from `get_config().stages` must appear exactly once, each value is either a
finite number or the single-key `{auto_comply: true}` mapping, and no extra key is present — this
mirrors the fail-closed validation style `world/rules/rulebook/schema.py` and `affinity_config.py`
already use. The table is consumed through a module-level singleton loaded on first access
(`get_resist_config()`, mirroring `get_config()`'s own lazy-cache pattern) rather than an
import-time eager load: `get_config()` itself requires the quest definition registry (its
`cap_breaks` validation), which only server startup or test setup populates, so an import-time load
would crash every non-bootstrapped import (e.g. test collection).

**Why a flag instead of a very large number for the top two stages:** a numeric bonus cannot
guarantee anything in this engine — `body_enhancement_extreme` (an existing skill) multiplies
`atk_phys` by 1000, so any finite constant is out-scalable by a sufficiently built actor. `beloved`
(floor 90) is the highest stage reachable at the natural affinity cap (99); `absolute_bond`'s floor
(100) exceeds that cap and is therefore unreachable without a `cap_breaks` milestone. So `beloved` is
the highest stage an ordinary player reaches, and only affinity — never a stat build — can produce
compliance at or above it.

**Alternative considered:** apply the modifier as a percentage of the resister's blended score
instead of a flat addend. Rejected — a flat addend keeps the table's units directly comparable to
`defender_constant` (`51`) and to `_attempt_flee`'s own flat-value contest, and avoids a
multiplicative interaction with Decision 2's weighted blend that would be harder to reason about at
balance-tuning time.

### Decision 4 — Affinity only ever helps the resister, and only when the resister is an `NPC`

The resist score's affinity lookup is: if `resister` is an `NPC` instance (checked with
`isinstance`, mirroring `apply_affinity_change`'s own owner check) and `actor` resolves to a
`PlayerCharacter`, read `resister.relations.stage_for(actor)` and apply that stage's modifier (or
short-circuit on `auto_comply`). Otherwise — the resister is a `Monster`, or the resister is a
`PlayerCharacter` (a player is never the resisting side against another player in this system; every
act in this document set's scope is player-cast), or `actor` does not resolve to a player — the
affinity term is `0` and no `auto_comply` short circuit from this source is possible.

This is a strict reading of the resolution design's own text: "Monsters have no affinity record.
Their resist is a pure stat contest and can never auto-comply." A `Monster`'s `.relations` handler
exists (mounted on the shared `LivingEntity` base) but is never populated for it, because
`apply_affinity_change` — the sole affinity writer — rejects any non-`NPC` owner; reading
`stage_for()` on an untouched handler correctly returns the zero-value default stage (`初識`, floor
0), which this proposal's own affinity term maps to `+15`, not `0` and not `auto_comply`. The
`isinstance(resister, NPC)` check is therefore load-bearing, not defensive — without it, a monster
resister would incorrectly receive `初識`'s bonus.

**Alternative considered:** key the affinity lookup on `hasattr(resister, "relations")` instead of
`isinstance(resister, NPC)`. Rejected — every `LivingEntity` has `.relations`, including `Monster`,
so this would silently grant monsters the `初識` stat bonus described above. The explicit type check
is the only correct gate.

### Decision 5 — The climax-turn short circuit reads stored state; no new counter

`resist_verdict()` short-circuits to compliance whenever the resister's stored climax state reads
as `climax_phase` level `進行中` with `climax_turns <= climax_turn_auto_comply_limit` (`5`, from
`sexual_resist.yaml`). Both facts are read from persistent storage without materializing the
`sexual` handler — the phase level through `combat_modifiers.build_no_create_condition_context`
(the same stored-state context the preview and no-create paths use; an entity whose sexual state
has never been touched reads as not-in-進行中 and falls through to the ordinary contest) and
`climax_turns` directly from the `sexual_state` attribute category. Materializing the handler is a
state write, not a read: `SexualState.__init__` creates the stored traits on first access, which
would break `resist_verdict()`'s no-mutation contract. (Rubber-duck review finding: the first
implementation draft read `getattr(resister, "sexual", None)` and would have persisted traits on
the first verdict against a fresh entity; the shipped tests pin the fix with a
"never materializes sexual state" integration test.)

This composes for free with Decision 2 in the common case: entry into `進行中` requires having passed
through `接近`, which itself requires `pleasure` to have reached the `極限` band (`climax_gate`'s
condition). Whenever the resister's `pleasure` is *still* in `極限` at contest time — the case the
climax-turn short circuit is actually built for, since it directly resolves the auto-comply — the
shipped `high_arousal_agility_accuracy_penalty` rule (`agility: "-20%"`) is already applied to that
entity's `agility` term by `evaluate_combat_modifiers_no_create()`, with no new rule authored for it. Nothing
in this proposal *requires* that condition to hold for correctness — `resist_verdict()` always reads
the live stored-state bundle regardless — so a resister whose `pleasure` has since decayed below `極限` while still
technically in `進行中` (a narrow window `sexual.yaml`'s rule cascade does not obviously rule out)
simply loses this particular bonus without breaking anything.

**Alternative considered:** track a dedicated "resist-eligible" flag on `SexualState` instead of
comparing `climax_turns` against a threshold constant. Rejected — `climax_turns` already exists,
already means exactly "consecutive settlement points spent in `進行中`", and `climax-settlement`'s
own design explicitly reserved it for "a later proposal [to] read it" (Non-Goals). Adding a second,
derived field would duplicate state that can be computed from what already exists.

### Decision 6 — `resist_verdict()` returns a small typed result, not a bare bool

```python
@dataclass(frozen=True)
class ResistVerdict:
    resisted: bool
    auto_comply: bool          # True when no roll occurred
    roll: int | None           # the raw d100, or None when auto_comply
    actor_score: float
    resister_score: float
```

Mirrors `_attempt_flee`'s existing return shape (`tuple[bool, dict[str, float | int | None]]`) in
spirit but as a named, typed structure — this codebase's skill-effects module (`world/skills/
effects.py`) already establishes frozen dataclasses over ad hoc dicts/tuples as the house style for
typed intermediate results. The detail fields let `sexual-resist-turn-cost` build a
`disengage_attempt`-style EventLog description without recomputing anything, and let this proposal's
own tests assert on `auto_comply` without inferring it from `roll is None`.

**Alternative considered:** return `_attempt_flee`'s exact `tuple[bool, dict]` shape for maximum
consistency. Rejected — `_attempt_flee` is `disengage.py`-private (leading underscore, no `__all__`
export) and this codebase's newer modules (`world/skills/effects.py`, `SexualActDef` per the
resolution design) already prefer a typed dataclass for anything a sibling module will consume; the
sibling here is a different proposal (`B6b`) entirely, which makes an ad hoc dict a worse contract
than a named type.

## Risks / Trade-offs

- **[Risk]** A future caller (`B6b`) could invoke `resist_verdict()` with the actor and resister
  swapped, silently inverting who benefits from the affinity/climax-turn short circuits.
  → **Mitigation:** the function signature names both parameters explicitly (`actor`, `resister`,
  keyword-only past that point is not needed since there are only two), and this proposal's test
  suite includes an explicit asymmetry test: swapping the two arguments on a fixture where only one
  side qualifies for `auto_comply` must change the verdict. `sexual-resist-turn-cost`'s own tests are
  expected to additionally assert the call site passes them in the documented order, but that
  assertion belongs to that sibling proposal, not this one.
- **[Risk]** The blended-score weights (Decision 2) and the affinity modifier table (Decision 3) are
  invented balance numbers with no existing precedent to anchor them, unlike `defender_constant`
  (already calibrated by `dice-combat`'s D-2 for 50% parity).
  → **Mitigation:** both live entirely in `sexual_resist.yaml`, changeable without touching Python,
  consistent with every other rulebook table in this codebase (`combat.yaml`, `overwhelm.yaml`,
  `affinity_config.py`'s own stage floors). No test asserts a specific numeric outcome tied to these
  exact values beyond the qualitative properties in Goals (auto-comply short circuits before any
  roll; a higher-affinity stage's numeric modifier is never worse for the resister than a
  lower-affinity stage's, verified as a monotonicity property across the five numeric stages).
- **[Risk]** This proposal ships an unconsumed capability, identical in shape to the risk
  `climax-settlement` accepted for `stage_climax_extension()`: until `sexual-resist-turn-cost` lands,
  nothing in production code calls `resist_verdict()`.
  → **Mitigation:** accepted deliberately, matching this document set's file-ownership-driven
  parallelization strategy (`overview-design.md` §4) — shipping the pure function independently is
  what lets it be implemented in the same batch as `sexual-act-effects` (`B5`) rather than serially
  after it. The capability is fully tested in isolation in the meantime.
- **[Trade-off]** `isinstance(resister, NPC)` (Decision 4) means a hypothetical future non-`NPC`,
  non-`Monster` `LivingEntity` subclass would fall through to "no affinity term" by default rather
  than erroring.
  → Accepted: this matches the codebase's existing pattern of treating unrecognized entity shapes
  permissively at read sites (e.g. `climax_settlement_action`'s `getattr(entity, "sexual", None)`
  guard) rather than raising, and no such subclass exists today (`LivingEntity`'s only concrete
  subclasses are `PlayerCharacter`, `NPC`, and `Monster`).

## Migration Plan

None. The project has no released users (`AGENTS.md`); no backward-compatibility layer or data
migration is required. This proposal adds two new files and no existing call site changes, so
nothing to roll forward or back beyond the files themselves.
