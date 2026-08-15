# Sexual Act Resolution — Design

**Date:** 2026-08-15
**Status:** Approved (pending final user review)
**Scope:** `world/lore/sexual_vocab.py`, new `world/skills/sexual_acts/` package,
`world/skills/handler.py`, `world/skills/effects.py`, `world/rules/action.py`,
new `world/rules/sexual_acts.py`, new `world/rules/sexual_resist.py`,
new `world/rules/rulebook/sexual_resist.yaml`, `world/rules/combat_session.py`,
`world/rules/affinity.py`.

Part of the [Sexual Act System document set](2026-08-15-sexual-act-system-overview-design.md).
Covers proposals `C1` (vocabulary), `B4` (registry and unlock), `B5` (effects and participants),
`B6a` (resist contest), `B6b` (turn cost).

---

## 1. Body Part Vocabulary (proposal `C1`)

`world/lore/sexual_vocab.py` is the canonical vocabulary owner and its spec requires it to contain
**no behaviour and no dependency on `world/rules/` or `world/imports/`**. `C1` therefore adds
constants only:

```python
BODY_PARTS = ("口唇", "頸項", "耳朵", "乳房", "腰腹", "臀部", "大腿", "足部", "私處", "後庭")
GENERIC_BODY_PART = "軀體"
```

`GENERIC_BODY_PART` is deliberately **not** a member of `BODY_PARTS`, which makes "no act may declare
the generic channel" a structural test rather than a convention.

`尾巴` is not included. It existed in the shipped spec only as an example of an arbitrary part name
on a monster; monsters now resolve to `GENERIC_BODY_PART` instead (§3.2). Because
`SexualState.sensitivity` is a lazily-populated mapping that defaults any unseen part to `普通`
without raising, a future non-human *player* race needing an extra part is a one-string addition
with no migration.

`resolve_part()` itself lives in `world/rules/sexual_acts.py` (proposal `B5`), not here — it needs
`isinstance(entity, Monster)` and this module must stay behaviour-free.

---

## 2. Act Registry (proposal `B4`)

### 2.1 Two registries, one key

Each act contributes **two** entries under the same key:

- A perfectly ordinary `SkillDef` in `SKILL_REGISTRY`, declaring
  `category=SkillCategory.SEXUAL_ACT` and its line as `group`. This is what `ActionResolver`,
  `combat_view.py`, and the `cast` command see. They need no knowledge that sexual acts exist.
- A `SexualActDef` in a parallel frozen `SEXUAL_ACT_REGISTRY`, carrying the act-specific metadata
  that would be dead weight on the other 118 skills.

```python
@dataclass(frozen=True)
class SexualActDef:
    key: str                              # same key as the SkillDef
    line: str                             # 獨處 / 羞恥 / 關係 / 戰鬥 / 異種 / 神之秘法
    unlock: Mapping[str, int]             # counter name -> threshold; ALL must be met
    base_pleasure: int                    # pre-multiplier magnitude
    actor_part: str | None                # a BODY_PARTS member
    target_part: str | None               # a BODY_PARTS member; None for 異種 and 神之秘法
    actor_pleasure_ratio: float           # share of base applied to the actor (D-4)
    actor_counters: tuple[str, ...]
    participant_counters: tuple[str, ...]
    sexual_events: tuple[str, ...]        # existing sexual.yaml event names to emit
    resistible: bool
```

An act with an empty `unlock` mapping is a seed: always available.

### 2.2 Package layout and the pre-stub rule

```
world/skills/sexual_acts/
    __init__.py          assembles SEXUAL_ACT_REGISTRY from all six modules
    _builder.py          _act_family(), validation
    solo.py              獨處線
    shame.py             羞恥線
    partner.py           關係線
    combat.py            戰鬥線
    interspecies.py      異種線
    divine.py            神之秘法線
```

`B4` ships **all six modules already present, already imported by `__init__.py`, each exporting an
empty tuple.** The six catalog proposals then each fill exactly one module and touch nothing else,
making batch 6 fully parallel (overview §4.5). Explicit stubs are used rather than package
auto-discovery to match this codebase's preference for deterministic, inspectable registries.

`_act_family()` mirrors the existing `_elemental_spells()` idiom: one tuple row per act, with the
shared line, tier, and unlock requirements written once for the family. Adding a flavour variant is
one line.

### 2.3 Unlock query

```python
SexualState.unlocked_act_keys() -> frozenset[str]
```

Returns every act key whose `unlock` thresholds are all met by the entity's counters — **or the
entire catalog** when the entity directly owns any skill carrying `SexualMasteryEffect`.

That blanket unlock is the missing consumer for a forward-declared seam: `SexualMasteryEffect` has
existed in `world/skills/effects.py` since the skill-system redesign, its docstring states it should
"unlock casting of the sex-magic skill family", and the redesign's effect table describes it as the
non-elemental sibling of `ElementMasteryEffect`'s cast-gate override — but **no code has ever read
it**. Two skills carry it today: `divine_sexual_mastery` (性魔法主宰) and `reincarnation_boon_yuna`
(轉生祝福·悠奈).

The ownership test mirrors `can_cast_spell_tier`'s discipline exactly, including the clause that is
easy to miss: **conferred grants never satisfy a mastery override** (skill-system redesign D4/D6 —
only `owned_keys()` counts, never `conferred_grants()`). So `dominion_art` (統御術) conferring a
fraction of 性魔法主宰 does **not** unlock the catalogue for the recipient, exactly as it does not
unlock an element's spells.

Counters keep accumulating under a blanket unlock. They still feed flavour, narration, and the
divine line's own gates; they simply stop gating.

### 2.4 Ownership integration, and the recursion it would otherwise cause

`SkillHandler.owned_keys()` appends the unlocked act keys, which is what makes locked acts
simultaneously un-castable (`_step1_ownership` rejects them) and unrenderable (`combat_view.py`
never sees them), with no possibility of the two disagreeing.

Two constraints shape how:

**Dependency direction.** The `universal-action-ownership` spec requires `world/skills/handler.py`
to contain no import from `world/rules/`, and its scenario inspects import statements. `owned_keys()`
therefore reaches the unlock set by a duck-typed attribute read on the entity
(`getattr(entity, "sexual", None)`), never by importing `world.rules.sexual_state`. No static
dependency is created in the forbidden direction.

**Recursion.** `unlocked_act_keys()` must test skill ownership for the mastery blanket. If it called
`owned_keys()`, and `owned_keys()` calls `unlocked_act_keys()`, the two recur infinitely.

`SkillHandler` therefore gains `base_owned_keys()` — the entity's imported active and passive keys
plus `INNATE_SKILL_ORDER`, i.e. exactly today's `owned_keys()` — and `owned_keys()` becomes
`base_owned_keys()` plus the unlocked acts. The mastery check consults `base_owned_keys()`.

This is not merely a cycle-breaker; it is also **correct**. Mastery skills are imported passives and
can never themselves be sexual acts, so the base set is the right thing to search.

### 2.5 Structural invariants

Enforced at registry-load or by structural test, following the `sexual.yaml` precedent of proving
coverage rather than trusting convention:

1. **Every act applying pleasure to another participant applies non-zero pleasure to the actor**
   (`actor_pleasure_ratio > 0`), *unless* its `SkillDef` declares `requires_divine_arts`. This is
   the system's only self-limiting mechanism (overview D-4/D-9). The exemption is keyed on the
   existing data field, never a hardcoded key list. Self-only reduction acts (快感控制, 極限忍耐)
   are exempt because they target no other participant.
2. No act declares `GENERIC_BODY_PART` for either role.
3. No `異種` or `神之秘法` act declares a `target_part`.
4. Every part named by any act is a member of `BODY_PARTS`.
5. Every counter named in `unlock`, `actor_counters`, or `participant_counters` exists on
   `SexualState`.
6. Every event named in `sexual_events` is a `when.event` value appearing in `sexual.yaml`.
7. `SEXUAL_ACT_REGISTRY.keys()` and the set of `SKILL_REGISTRY` keys categorised `sexual_act`
   (excluding the three pre-existing mastery/mystery skills) are identical.

---

## 3. Effects and Participants (proposal `B5`)

### 3.1 Two new effect prefixes

Registered through the existing `register_effect_handler` seam in `world/rules/action.py`, beside
`sexual_event`, `damage`, `heal`, and the rest. No new dispatch mechanism.

| Prefix | Typed dataclass | Behaviour |
|---|---|---|
| `pleasure:<magnitude>` | `PleasureEffect(magnitude)` | Computes and applies gain to every participant per the [pleasure model](2026-08-15-sexual-pleasure-model-design.md) §1.5; sets the extension flag when the computed gain meets the threshold |
| `sexual_counter:<name>` | `SexualCounterEffect(name)` | Increments one counter through its sanctioned mutator |

Both declare the rollback surfaces `frozenset({"sexual", "traits"})` — the same set
`sexual_event` already declares — so a mid-pipeline failure restores gauge, counters, and the
transient extension state along with everything else. `parse_effect` raises at registry-load time
for a malformed payload, as it does for every other prefix.

### 3.2 The participant model

`participants = {actor} ∪ resolved_targets`. Every participant receives pleasure and counter grants;
the actor's share is `base_pleasure × actor_pleasure_ratio`, and roles determine which counters
apply.

This is what makes `SELF`, `SINGLE`, and `AREA` acts express solo, two-person, and group scenes
without extending `TargetSpec` — a solo act simply has an empty target list, so the participant set
is the actor alone.

Part resolution runs per participant:

```python
def resolve_part(entity, declared_part):
    return GENERIC_BODY_PART if isinstance(entity, Monster) else declared_part
```

`isinstance(entity, Monster)` is the **same predicate `SexualState.__init__` already uses** to clamp
monster `shame`, so no new taxonomy is introduced. Monsters keep exactly one sensitivity channel
where a humanoid has ten, which means sensitivity training still works on them — it simply is not
part-specific. No per-monster anatomy data exists or is needed, consistent with the
`sexual-state-handler` spec's 2026-08-09 amendment refusing per-archetype monster baselines.

### 3.3 Reused events

Acts emit existing `sexual.yaml` events rather than new ones wherever one already fits, which is
most of the time: `stimulus_applied`, `sustained_stimulus_applied`, `direct_stimulus_applied`,
`extreme_stimulus_applied`, `frequent_stimulation`, `masturbation_climax`, `public_exposure`,
`watched_during_activity`, `public_sexual_activity`, `breast_sex_performed`,
`first_vaginal_penetration`, `penetrative_sex_with_female`, `sexual_activity_with_nonhuman`.

Twenty of the twenty-five shipped rules currently have no emitter. This system is largely their
first consumer, not a new rule surface.

### 3.4 Resist outcome contract (for `B6b`)

For every participant the resist contest at §4 applies to, the effect handler must emit exactly one
`EventEntry` recording the outcome, so `sexual-resist-turn-cost` (`B6b`) can react to it without a
direct call into this module:

```python
EventEntry(
    kind="sexual_resist",
    actor=<caster's entity key>,
    target=<participant's entity key>,
    data={"resisted": bool, "auto_comply": bool, "roll": int | None},
    text_template=<a narrative line appropriate to the outcome>,
)
```

emitted once per resistible participant regardless of outcome — so a downstream scan can distinguish
"no entry because this participant was never resistible" (for example, the actor, or a participant an
act does not resist against) from "an entry recording compliance." The three `data` field names and
types match `resist_verdict()`'s own `ResistVerdict` fields (§4.1) exactly, so this module and
`world/rules/sexual_resist.py` share one vocabulary with nothing to translate between them.

This contract exists so `B6b`'s post-round affinity scan (§5) has a durable, replayable record to
react to without importing this module's effect-handler code directly — the same reason
`_scan_friendly_fire` reacts to `damage`-kind `EventEntry` records rather than being called directly
by the damage handler. Whichever of `B5`/`B6a`/`B6b` lands last in the approved batch sequence, this
contract is fixed here, in the shared source design, rather than in only one sibling proposal's own
design.md — `B5`'s own implementer must honor it regardless of batch order relative to `B6b`.

---

## 4. The Resist Contest (proposal `B6a`)

### 4.1 Formula

Specified as a **pure function** returning a verdict, with no state mutation, so it is testable
standalone and can be implemented in parallel with `B5`.

The contest reuses `disengage.py::_attempt_flee`'s exact shape rather than inventing a second idiom:

```
resist succeeds when
    roll_d100() + resist_score >= COMBAT_YAML["to_hit"]["defender_constant"] + actor_score
```

with `defender_constant` the shipped `51`, and both scores blended from effective `agility` and
`atk_phys` read through `evaluate_combat_modifiers()` exactly as `_adjusted_agility` does. The blend
weights live in a new `world/rules/rulebook/sexual_resist.yaml`.

Reading through the modifier evaluator delivers one behaviour for free: an entity in `進行中` is
necessarily in the `極限` band, so the existing `high_arousal_agility_accuracy_penalty` already
applies `agility: -20%` to their resist score. **"Someone mid-climax struggles to break free" is
emergent, not authored.**

### 4.2 Affinity

The resister's score is modified by a per-stage value from `sexual_resist.yaml`, keyed to the seven
shipped affinity stages. The two stages at and above the natural cap carry `auto_comply: true`
rather than a number:

| Stage | Floor | Resist modifier |
|---|---|---|
| 初識 | 0 | (largest resist bonus) |
| 熟識 | 10 | ↓ |
| 親睦 | 30 | ↓ |
| 信賴 | 50 | ↓ |
| 羈絆 | 70 | ↓ |
| 至愛 | 90 | **`auto_comply`** |
| 絕對羈絆 | 100 | **`auto_comply`** |

`至愛` is the highest stage reachable without a `cap_breaks` milestone — the natural affinity cap is
99 and `絕對羈絆`'s floor is 100 — so it is the correct place for guaranteed compliance.

A flag rather than a large constant, because **a numeric bonus cannot guarantee anything in this
engine**: `body_enhancement_extreme` multiplies stats by 1000, so any fixed constant is out-scalable.
The flag delivers the intended behaviour and cannot be defeated by a stat build.

Monsters have no affinity record. Their resist is a pure stat contest and can never auto-comply.

### 4.3 Climax-turn short circuit

For climax turns 1–5 an entity in `進行中` auto-complies; from turn 6 the ordinary contest applies.
Rationale and consequences are in the
[pleasure model](2026-08-15-sexual-pleasure-model-design.md) §3.5.

---

## 5. Turn Cost and Affinity Consequence (proposal `B6b`)

The effect handler documented in §3.4 emits one `EventEntry(kind="sexual_resist", ...)` per
resistible participant; this section's post-round scan reacts to that record rather than calling
`resist_verdict()` (§4.1) directly.

| Outcome | Actor's turn | Target's turn | Affinity |
|---|---|---|---|
| Comply (rolled or auto) | consumed | consumed | unchanged |
| Resist succeeds | **wasted** | proceeds normally | unchanged |
| Resist fails (forced) | consumed | consumed | **penalty applied** |

Consuming both turns is what makes an act a genuine 1-for-1 action trade: neutral in a duel,
favourable when outnumbering, ruinous when outnumbered. Party composition therefore matters, without
any new tactical subsystem.

**Only a forced act costs affinity** (overview D-7). A refused attempt costs the wasted turn and
nothing more. The penalty routes through the existing sole affinity writer in
`world/rules/affinity.py`, alongside `friendly_fire_penalty_per_hit`, so the shipped daily-budget and
clamping rules apply unchanged.

The penalty can drive a companion below `invite_threshold` (70) and trigger the existing party
auto-leave. That consequence is intended: it is what gives forcing weight. A companion at `至愛` or
above auto-complies and can therefore **never** take this penalty.

Out of combat there is no turn economy. A successful resist simply fails the act; the SP costs,
state transitions, and affinity consequences are otherwise identical.

---

## 6. Error Handling & Validation

| Condition | Behaviour |
|---|---|
| Casting a locked act | `_step1_ownership` rejects — the key is not in `owned_keys()`. Identical to casting an unowned skill; no new reject reason. |
| An act naming a counter that does not exist | Structural test failure at build time (§2.5.5), never a runtime error. |
| An act naming an event absent from `sexual.yaml` | Structural test failure (§2.5.6). |
| A `sensitivity`-targeting event with no `part` | The shipped rule already raises rather than defaulting; act resolution always supplies a resolved part, so this stays unreachable. |
| Malformed `pleasure:` / `sexual_counter:` payload | `parse_effect` raises at registry-load time. |
| A mid-pipeline failure after pleasure was staged | Full rollback through the declared `sexual`/`traits` surfaces. `ActionResolver`'s all-or-nothing guarantee is inherited unchanged. |

---

## 7. Testing Strategy

- **Unlock query:** thresholds gate exactly; a blanket unlock from each of the two mastery-bearing
  skills; a **conferred** grant of 性魔法主宰 does *not* unlock the catalogue (the D4/D6 discipline,
  pinned); and a regression test proving `owned_keys()` and `unlocked_act_keys()` do not recur
  (§2.4).
- **Ownership integration:** a locked act is absent from `owned_keys()`, rejected by
  `_step1_ownership`, and absent from the combat panel payload — asserted together, since the point
  of D-2 is that the three can never disagree.
- **Import discipline:** a test inspecting `world/skills/handler.py`'s import statements for any
  `world.rules.*` reference, extending the shipped `universal-action-ownership` scenario.
- **Participants:** a solo act grants the actor alone; a two-person act grants both; an AREA act
  grants all; role-scoped counters land on the correct ledgers.
- **Part resolution:** a humanoid target trains the declared part; a `Monster` target trains
  `軀體` and never the declared part; repeated acts on one part raise that part's sensitivity and no
  other's, and the raised sensitivity measurably increases later gain.
- **Resist contest:** deterministic under an injected RNG at the boundary rolls; `至愛` and
  `絕對羈絆` short-circuit without rolling; a monster never auto-complies; the `-20%` agility penalty
  from `極限` is present in the resist score without any rule authored for it.
- **Turn cost:** all three outcome rows in §5 asserted against a live combat session.
- **Affinity:** a forced act applies exactly one penalty through the sole writer; a refused attempt
  applies none; a forced act on a low-affinity companion can cross `invite_threshold` and trigger
  auto-leave.
- **Structural invariants:** one test per numbered item in §2.5, each failing loudly when a
  hypothetical violating act is added.
