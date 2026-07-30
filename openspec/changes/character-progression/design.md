## Context

This is roadmap item #11b (design doc §11), depending on change 5 (`skills-equipment`), change 6
(`buffs-rulebook`), and change 11 (`world-clock`). No code exists yet for this change's scope —
`world/rules/` currently holds `traits.py` (change 3), `buffs.py`/`combat_modifiers.py` (change 6), and
`clock.py`/`skip_safety.py` (change 11); nothing named `progression.py` exists, even though design doc
§3.2 already forward-declares it in the same line as `traits · sexual_state · buffs · progression`.

**This change exists because change 6 surfaced a gap and named this change as the fix.** Change 6's
design.md D-6 built `growth_rate_multiplier(entity)` (a pure query folding together every active
`conferred_growth_rate` buff's `scale`) and `grant_conferred_growth_rate(entity, source_key, scale)` (a
plain, unconditional write creating that buff instance) specifically for Elosia's card, which narrates a
partial magic-growth-rate conferral onto Violet ("獲得「XXXX：魔法成長百倍增幅」的部份效果，魔法成長提升").
Both functions are tested against buff state alone and call nothing — change 6's own Non-Goals state
plainly: "No progression, XP, or leveling system reading `growth_rate_multiplier()`'s output for real —
change 11b ... owns 'how `magic_level` actually increases over time' and is this function's consumer."
Until this change lands, `entity.traits.magic_level` (a `CounterTrait`, change 3) starts at `0` and never
moves — no code path anywhere in the project increments it, and `growth_rate_multiplier()`'s return value
is read by nothing.

**Two source-card numbers anchor this change's calibration, both read directly from
`tmp/story_settings/character/`:**

- **Violet** (`VioletAltoria.md`): 「15歲時，以王立魔法初等學校史上最年輕的首席身份畢業。由於過人的智力及
  努力，魔法等級由初始10級升上30級」— levels 10→30 (20 levels) between roughly ages 7 and 15 (8 years),
  entirely **before** she becomes Elosia's student at 16. This is dedicated study by a human prodigy,
  with **no conferred buff active yet** (the conferral is narrated as a *current-state* status effect
  acquired after apprenticeship began) — the cleanest available data point for calibrating the
  study-driven growth rate at `growth_rate_multiplier() == 1.0`, `learning_multiplier == 1.0`.
- **Elosia** (`ElosiaShadowmoon.md`): 「轉生特典: 魔法成長百倍增幅：能以百倍的速度學習魔法，是該種族平均的百
  倍速」(her own passive grants her 100× her own race's average learning speed) and 「打發時間學的魔法達到
  魔法等級873級」(magic learned "just to pass the time" — explicitly casual, not dedicated study — reached
  level 873), against her card's 魔法等級 line: 「偽裝 120 實際 873」and `RaceProfile.magic_cap["elf"] ==
  900`. Her combined multiplier is `learning_multiplier (10.0, elf) × self-multiplier (100, her own
  passive)` = 1000× the human baseline rate.

Both cards' `disguised_stats`-adjacent 「偽裝/實際」 notation and the `*10`/`*100` static-stat suffixes are
change 5's and change 3's territory (skill-multiplier resolution, base-value storage) — this change reads
only the `魔法等級` (magic level) lines, which are progression data, not combat-stat data.

## Goals / Non-Goals

**Goals:**
- `world/rules/progression.py`: magic-level growth from a documented combination of ambient study time
  and combat-kill experience, all funneled through one multiplier function,
  `effective_magic_growth_multiplier(entity)`, that folds together `RaceProfile.learning_multiplier`
  (change 2), a self-multiplier read from the entity's own owned passive skills (this change's own
  `magic_growth_multiplier:<N>` effect-ID convention), and change 6's `growth_rate_multiplier(entity)`
  (conferred buffs) — **the concrete consumer change 6 was built for.**
- A hard ceiling: `magic_level` never exceeds `RaceProfile.magic_cap` (or `0` for a `Monster`, which has
  no race). Every multiplier accelerates *rate*, never raises this ceiling.
- Skill proficiency (`entity.db.skill_proficiency`) as a second, independent counter — practice-driven,
  scaled only by `RaceProfile.learning_multiplier`, structurally separate from `magic_level`.
- A settlement-stage-shaped callable, `accrue_magic_study(entities, seconds, source)`, ready for change
  11's stage registry to invoke — and a precise, non-code-editing specification of exactly where it
  needs to slot into change 11's fixed `_STAGE_ORDER`.
- Fully deterministic, golden-value regression tests — no randomness appears anywhere in this module's
  formulas, so "fixed-seed" is vacuous here; the equivalent discipline is fixed, hand-computed expected
  values for fixed inputs.

**Non-Goals:**
- No guild merit or guild rank — `entity.traits.guild_merit` (a `CounterTrait`, change 3) is untouched by
  this change; change 16 (`guild-economy`) owns both the merit counter's growth and rank promotion.
- No quest completion rewards — change 15 (`quest-runtime`) does not exist yet. This change declares
  `grant_combat_kill_xp()` as the one XP-granting seam a future quest-completion consumer could also call
  (a quest reward is, mechanically, just another XP grant), but does not build any quest-specific code
  path or attachment point beyond noting the seam is reusable.
- No new player-facing command. Ambient study reuses change 11's already-built `rest`/`sleep`/`wait`
  commands (via their shared `AdvanceSource.SKIP`) rather than inventing a `study` command — see D-2.
- No edit to change 11's OpenSpec artifacts. This change's own settlement-stage-shaped callable is built
  and tested standalone (mirroring change 6's own treatment of `tick_buffs(entity)` before change 11
  existed to call it); the exact stage name, gate, and position change 11 needs are specified in this
  design (D-2) and in the proposal's Impact section, for the coordinator to carry into change 11
  directly — not made here.
- No edit to change 5's, change 6's, or change 3's OpenSpec artifacts. This change reads
  `SKILL_REGISTRY`/`entity.skills.owned_keys()` (change 5), `growth_rate_multiplier()`/`entity.buffs`
  (change 6), and `entity.traits.magic_level`/`RACE_REGISTRY` (changes 2/3) without modifying any of
  them.
- No numeric progression counter for 神之秘法 (divine arts) — `RaceProfile.can_use_divine_arts` is a
  boolean gate only; no lore source or entity-traits change defines a divine-arts level trait. The
  "casual decades vs. dedicated one year" 30-fold anchor for divine arts specifically is therefore not
  numerically reproducible by this change — see Risks.
- No combat resolution, damage formula, or kill-detection logic (changes 9/10) — `grant_combat_kill_xp()`
  is a pure data-write seam; deciding *when* a kill has occurred is combat's job, not this change's.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/progression.py` does not exist yet.

## Decisions

### D-1. Magic-level growth is a documented combination: ambient study time (primary) plus combat-kill
XP (secondary) — ordinary skill *casting* grants no `magic_level` XP of its own.

The task requires deciding whether `magic_level` grows from experience, casting, study, or a
combination, and justifying the choice against the calibration anchors.

**Study time is the primary driver, because it is the only mechanism either anchor's narrative
actually shows.** Neither Violet (a royal scholar, not an adventurer, for the entire 10→30 span) nor
Elosia (whose 873 is explicitly "learned to pass the time," 打發時間) reaches their documented level
through combat. Both anchors are pure study/practice. A design that made `magic_level` grow only from
combat kills would be unable to reproduce either anchor at all.

**Combat-kill XP is a secondary, additive driver, because hard requirement 3 states plainly that
combat kills are available** (changes 9/10 emit `EventLog`s) and the roadmap explicitly frames this
change as the consumer of accumulated game mechanics, not merely a re-derivation of one card's
backstory. `grant_combat_kill_xp(entity, monster_tier_key)` is declared as a seam for a future
combat-completion consumer to call once per kill, scaled by the same
`effective_magic_growth_multiplier()` study-XP uses — one shared multiplier function, one shared XP
pool (`entity.db.magic_xp`), two ways to fill it.

**Ordinary casting (using a skill you already know) does not itself grant `magic_level` XP.**
`world_info.md`'s own framing of `魔法等級` ties it to understanding magic-circle theory and capability
tier (初級/中級/高級/超級/究極, each gated by what magic you can *understand*, not how many times you've
cast a spell you already have) — repeatedly casting `fire_ball` does not make magic-circle theory click
faster. Casting *does* drive a different counter this change also builds — **skill proficiency**
(D-4) — kept structurally separate. This split has a direct textual anchor: 刀術強化 (a *skill*,
D-4) is described as improving through "長年訓練" (long-term training, i.e., repeated practice), while
`魔法等級` growth in both anchors is described as scholarly effort ("智力及努力"，"打發時間學的魔法"), never
as "cast this spell N times."

**Alternative considered**: fold combat-kill XP and study-time XP into the same call path (e.g., treat
every `advance()` call identically regardless of source). Rejected — collapsing them would mean a
`COMBAT`-sourced `advance()` (typically a handful of six-second rounds) would also silently accrue
ambient "study" XP for that same interval, double-counting the same span of time under two different
mechanisms. Gating `accrue_magic_study()` to `AdvanceSource.SKIP` only (D-2) keeps the two sources
cleanly partitioned by which kind of `advance()` call is in flight.

### D-2. `accrue_magic_study()`: a settlement-stage-shaped, closed-form callable, gated to
`AdvanceSource.SKIP` — no new player command, no quantum loop.

```python
# world/rules/progression.py
def accrue_magic_study(entities, seconds: int, source: "AdvanceSource") -> None:
    """Grants ambient magic-study XP for elapsed AdvanceSource.SKIP time only
    (rest/sleep/wait -- deliberate downtime). No-ops entirely for COMMAND
    (a single 6-second cast) and COMBAT (fighting is not studying; combat's
    own XP path is grant_combat_kill_xp(), called separately per kill) --
    matching this change's shared-pool-two-sources split (D-1).

    Closed-form: elapsed_hours * STUDY_BASE_XP_PER_HOUR *
    effective_magic_growth_multiplier(entity), computed once per entity per
    call -- the same O(1)-per-advance() discipline change 11's own
    _settle_gauge_regen() uses, and unlike change 6/7's tick_buffs()/
    decay_tick() (which require change 11's GCD-derived settlement quantum
    because they are each 'one call = one interval's worth'). This function
    introduces no new tick_interval/decay interval into change 11's
    SETTLEMENT_QUANTUM_SECONDS derivation."""
    if source is not AdvanceSource.SKIP:
        return
    hours = seconds / 3600
    for entity in entities:
        xp = hours * STUDY_BASE_XP_PER_HOUR * effective_magic_growth_multiplier(entity)
        entity.db.magic_xp = (entity.db.magic_xp or 0.0) + xp
        _apply_level_ups(entity)
```

**Why no new player command.** Change 11 already built `rest <duration>`, `sleep`, and
`wait until <daypart>` — the exact shape of "the player deliberately spends time" the setting needs for
"long-term training." Building a fourth, `study`, would duplicate `rest`'s own safety-gate and
duration-parsing machinery for no new mechanical behavior; `AdvanceSource.SKIP` already tags every
elapsed second from all three existing commands identically, and that tag alone is what
`accrue_magic_study()` needs to decide whether ambient study applies.

**Why no quantum loop.** Change 6's `tick_buffs()`/change 7's `decay_tick()` are documented as
"one call = one tick's/interval's worth," forcing change 11's `_settle_buffs_and_decay()` to call them
once per `SETTLEMENT_QUANTUM_SECONDS` so their own internal accumulators cross the right number of
interval boundaries. `accrue_magic_study()` has no such constraint — it is a closed-form multiplication
over the *entire* elapsed `seconds` argument in one call, exactly like change 11's own
`_settle_gauge_regen()`. A skip of 8 hours costs the same one multiplication as a skip of 8 minutes.
This also means this change adds **no new entry** to the GCD computation `SETTLEMENT_QUANTUM_SECONDS`
derives from (change 6's `tick_interval`s, change 7's `interval_seconds`s) — a fact worth stating
explicitly since a future reader might otherwise assume every settlement-stage callable needs to
participate in that derivation.

**Alternative considered**: gate on elapsed-time magnitude instead of `AdvanceSource` (e.g., only accrue
study XP for skips longer than some threshold, on the reasoning that a `rest 1h` isn't "serious study").
Rejected — this would need an arbitrary threshold with no source to calibrate it against, and
`AdvanceSource.SKIP` already captures exactly the intended semantic ("the player chose to let time pass
with no other action") more precisely than a duration heuristic could.

### D-3. `effective_magic_growth_multiplier()`: three independent multiplier sources, one combination
function — the concrete consumer of change 6's `growth_rate_multiplier()`.

```python
MAGIC_GROWTH_MULTIPLIER_PREFIX = "magic_growth_multiplier:"  # this change's own convention,
                                                                # mirroring change 5's D-5
                                                                # stat_multiply:<trait>:<multiplier>
                                                                # exactly, for a magic-growth-rate
                                                                # self-multiplier instead of a
                                                                # combat-stat multiplier

def _self_magic_growth_multiplier(entity) -> float:
    """Scans entity.skills.owned_keys() for a PASSIVE skill whose SkillDef.effects
    includes a 'magic_growth_multiplier:<N>' entry -- this change's own
    convention for a 'reincarnation boon'-style self multiplier (Elosia's
    own passive, change 5's reincarnation_boon_elosia). Multiplicative
    combination across matches, mirroring change 5's own effective_value()
    combination rule exactly. Returns 1.0 if no owned skill carries this
    effect."""
    multiplier = 1.0
    for key in entity.skills.owned_keys():
        skill = SKILL_REGISTRY.get(key)
        if skill is None:
            continue
        for effect_id in skill.effects:
            if effect_id.startswith(MAGIC_GROWTH_MULTIPLIER_PREFIX):
                multiplier *= float(effect_id.removeprefix(MAGIC_GROWTH_MULTIPLIER_PREFIX))
    return multiplier

def effective_magic_growth_multiplier(entity) -> float:
    """THE single place all three magic-growth-rate multiplier sources
    combine. Pure query -- reads race/skill/buff state, writes nothing.
    race.learning_multiplier defaults to 1.0 for an entity with no race
    (a Monster, per entity-traits D-3/D-11)."""
    race_key = getattr(entity, "race", None)
    race = RACE_REGISTRY.get(race_key) if race_key else None
    race_multiplier = race.learning_multiplier if race is not None else 1.0
    return race_multiplier * _self_magic_growth_multiplier(entity) * growth_rate_multiplier(entity)
```

`growth_rate_multiplier(entity)` is imported directly from change 6's `world/rules/buffs.py` — this is
the literal, concrete call site change 6's design.md named this change as owning. A regression test
constructs an entity with `race="human"` (`learning_multiplier=1.0`), no owned
`magic_growth_multiplier:` skill, and an active `conferred_growth_rate` buff at `scale=0.5` (created via
change 6's `grant_conferred_growth_rate(entity, source_key="elosia", scale=0.5)`), then asserts
`effective_magic_growth_multiplier(entity) == 0.5` and that `accrue_magic_study()` grants exactly half
the XP it would grant the same entity with no buff active — proving hard requirement 1 (change 6's
conferred grant "must actually change [Violet's] progression rate through your code") with a concrete,
executable test, not merely a docstring claim.

**Why `growth_rate_multiplier()` is folded into magic-level growth only, never into skill
proficiency.** Change 6's `buffs.yaml` defines `conferred_growth_rate`'s own modifier target explicitly
as `magic_level_growth` (change 6 design.md D-4's YAML: `modifiers.rate = {target: magic_level_growth,
...}`) — the buff's own data names its target, and that target is not "skill practice." Applying it to
`grant_skill_practice_xp()` as well would silently widen a buff's documented scope beyond what change 6
built and tested it for.

**Why multiplicative combination across all three sources, not additive.** This mirrors change 5's own
`effective_value()` precedent exactly (multiple owned multiplier skills combine multiplicatively, and a
conferred grant's `scale` multiplies in too) — one uniform combination rule across every multiplier this
project has, not a second rule invented here.

**Flagged for coordination**: change 5's `reincarnation_boon_elosia`/`_yuka`/`_yuna` `SkillDef` entries'
exact `effects` strings are **not pinned** by change 5's own artifacts — change 5's tasks.md only
requires "each with a distinct `effects` entry." This change's own tests construct a synthetic
`SkillDef` fixture carrying `magic_growth_multiplier:100` to prove `_self_magic_growth_multiplier()`
works correctly, independent of whatever exact string change 5's implementation actually assigns to
Elosia's passive. If change 5's real seed data does not use this convention for her entry, this
function will silently return `1.0` for her self-multiplier component (though her overall growth still
benefits from `growth_rate_multiplier()` if she is ever the *source* of a conferral elsewhere, and her
own multiplier would then need change 5's implementation — not its artifacts — adjusted to match this
convention). See Risks.

### D-4. Magic-level cap enforcement: closed-form, O(1), and a hard ceiling — rate accelerates, the
cap never moves.

```python
MAGIC_XP_PER_LEVEL = 600   # invented placeholder; calibrated against Violet's anchor (D-5), flagged
                             # for a future balance pass exactly like every other change's invented
                             # combat/economy constant

def _apply_level_ups(entity) -> None:
    """Closed-form: no while-loop bounded by elapsed time, no per-level
    iteration proportional to XP surplus -- a single floor-division and a
    min() against the cap, mirroring change 11's own O(1)-per-advance()
    discipline. Surplus XP beyond the cap is discarded, never banked,
    satisfying hard requirement 2 (the cap is a hard ceiling; multipliers
    accelerate rate, never raise it)."""
    magic = entity.traits.magic_level
    cap = magic.max   # RaceProfile.magic_cap at construction time (change 3),
                        # or 0 for a Monster -- exact CounterTrait attribute
                        # name (.max vs a differently-named max accessor)
                        # flagged for implementer verification, per this
                        # project's established discipline
    current = magic.value   # exact attribute name flagged for verification, same discipline
    if current >= cap:
        entity.db.magic_xp = 0.0
        return
    xp = entity.db.magic_xp or 0.0
    levels_gained = int(xp // MAGIC_XP_PER_LEVEL)
    new_level = min(cap, current + levels_gained)
    entity.db.magic_xp = 0.0 if new_level >= cap else xp - levels_gained * MAGIC_XP_PER_LEVEL
    magic.value = new_level
```

A test constructs an elf entity (`magic_cap = 900`) with `entity.db.magic_xp` set to an enormous value
(far more than 900 levels' worth) and asserts `entity.traits.magic_level.value == 900` exactly, never
higher, and `entity.db.magic_xp == 0.0` afterward — proving hard requirement 2 directly: Elosia's 873
sits under the elven 900, and nothing this change builds can push any entity past its race's cap
regardless of how large a multiplier or XP surplus it is given.

### D-5. Calibration: the growth curve checked against every anchor in the task, with an honest
accounting of what it does and does not reproduce.

**Violet: 10→30 in 8 years, no buff, `learning_multiplier=1.0`.** `world_info.md`'s own card gives no
exact "hours per day" figure — this change documents an assumption rather than inventing a curve blind:
Violet's account names dedicated magical study specifically ("在偶然的魔法啟蒙課中...從此被宮廷冠以'神童'
稱號"), distinct from her broader royal curriculum ("宮廷禮儀、多國語言、政治史學"). Assuming roughly 4
dedicated magic-study hours/day (a documented, invented assumption, not sourced) across 8 years gives
`4 × 365 × 8 = 11,680` study-hours. At `STUDY_BASE_XP_PER_HOUR = 1.0` and `MAGIC_XP_PER_LEVEL = 600`,
that yields `11,680 / 600 ≈ 19.5` levels — matching the documented 20-level gain within rounding. **This
is the anchor `MAGIC_XP_PER_LEVEL`'s value of 600 is deliberately calibrated against**, not an
independent invention checked afterward.

**Ordinary human, 30-50-level lifetime cap (`RaceProfile.magic_cap["human"] = 90`).** A professional
mage devoting a more modest ~2 study-hours/day across a ~40-year career: `2 × 365 × 40 = 29,200` hours
`/ 600 ≈ 48.7` levels — squarely inside the documented 30-50 range for "大多數人只能達到" (most people can
only reach). This is a **secondary confirmation**, not a second calibration target — the same constants
derived from Violet's anchor independently reproduce the "ordinary human" band under a plausible,
independently-chosen effort assumption (half of Violet's daily study intensity, four times her
duration).

**Elosia: 873/900, "casual" (`打發時間`), combined multiplier `10.0 × 100 = 1000×`.** Reaching level 873
requires `873 × 600 = 523,800` raw XP; at a `1000×` combined multiplier, that needs only `523,800 / 1000
= 523.8` study-hours. Even at a genuinely casual 2 hours/day, that is `≈ 262` days — under nine months
out of her ~10-year life, leaving the overwhelming majority of her life free for everything else her
card describes. **This reproduces the anchor's own qualitative claim directly**: "打發時間學的" (learned
just to pass the time) is not a euphemism under this curve — it is a small fraction of one already-short
elven childhood, exactly as the card implies, while her level stays strictly under her race's 900 cap
(D-4) as hard requirement 2 demands.

**精靈 learning_multiplier = 10.0, "average initial elf level 30."** This reproduces the *relationship*
between the two races precisely but not an exact number: under this curve, an ordinary elf investing far
less effort than Violet's near-genius regimen — e.g., a few years of modest childhood schooling at ~0.5
study-hours/day, `0.5 × 365 × 5 = 912.5` hours `× 10 = 9,125` raw-equivalent XP `/ 600 ≈ 15` levels —
lands in the same general neighborhood as Violet's *dedicated, prodigy-level* human effort (≈20 levels)
for a small fraction of the invested time, which is exactly what "learning speed 10× a human's" means:
what takes a human genius near-total childhood dedication is unremarkable for an ordinary elf. **This
change does not claim to reproduce the literal number 30 exactly** — no source document states how many
hours per day an "average" elf studies, so the precise figure is not independently checkable, only the
qualitative 10× relationship, which the arithmetic above demonstrates.

**神之秘法's "casual decades vs. dedicated one year" (~30× spread) — not reproduced, and cannot be.**
`世界觀` names this ratio for divine-arts learning specifically, a system gated by
`RaceProfile.can_use_divine_arts` (a boolean) with **no numeric level trait anywhere in the entity model**
(entity-traits change 3 defines exactly eight traits; none is a divine-arts level). This change does not
invent one — doing so would mean authoring a new `CounterTrait` and its construction-time seeding, which
belongs to entity-traits' own scope (frozen, not edited by this change) if it belongs anywhere at all.
**Stated plainly**: this curve reproduces the *magic_level* anchors (Violet, ordinary humans, Elosia,
the elf/human ratio) but does not and cannot reproduce the divine-arts-specific 30× ratio, since no
trait exists in the codebase for it to act on.

### D-6. Skill proficiency: `entity.db.skill_proficiency`, practice-driven, `learning_multiplier`-only,
kept structurally separate from `magic_level`.

```python
SKILL_PROFICIENCY_XP_PER_LEVEL = 50   # invented placeholder, flagged for balance pass
SKILL_PRACTICE_XP_PER_USE = 1.0        # invented placeholder, flagged for balance pass

def grant_skill_practice_xp(entity, skill_key: str, uses: int = 1) -> None:
    """Declared seam: called once per successful use of skill_key by a
    future ActionResolver integration (change 8's implementation, not its
    artifacts). A plain, unconditional data write -- no ownership/resource
    check, mirroring change 5's grant_conferred()/change 6's
    grant_conferred_growth_rate() discipline exactly."""
    race_key = getattr(entity, "race", None)
    race = RACE_REGISTRY.get(race_key) if race_key else None
    multiplier = race.learning_multiplier if race is not None else 1.0
    proficiency = dict(entity.db.skill_proficiency or {})
    proficiency[skill_key] = proficiency.get(skill_key, 0.0) + uses * SKILL_PRACTICE_XP_PER_USE * multiplier
    entity.db.skill_proficiency = proficiency

def skill_proficiency_level(entity, skill_key: str) -> int:
    """Pure derived query -- floor(accumulated practice XP / XP-per-level).
    No upper bound: no lore source specifies a per-skill proficiency
    ceiling, unlike magic_level's race-capped ceiling (D-4)."""
    xp = (entity.db.skill_proficiency or {}).get(skill_key, 0.0)
    return int(xp // SKILL_PROFICIENCY_XP_PER_LEVEL)
```

**Why a new, additive `entity.db.skill_proficiency` attribute, not a field on `SkillDef` or a method on
`SkillHandler`.** `SkillDef` is a frozen, shared *definition* (one `body_enhancement` entry describes the
skill for every entity that owns it) — proficiency is *per-entity, per-skill* state, which cannot live on
the shared definition without corrupting it for every other owner. Adding it as a method to change 5's
`SkillHandler` class would mean editing change 5's already-frozen artifacts, which this change may not
do. `entity.db.skill_proficiency` is the identical "new, additive, raw Evennia attribute; no edit to the
owning change's typeclass" pattern change 5's own `entity.db.skill_grants` (D-6) and change 4's
`entity.db.inventory` (D-13) already established — `world/rules/progression.py` reads and writes it
directly, the same way `world/rules/buffs.py` never touches `entity.db.skills` directly either.

**Why individual skills level up separately from `magic_level`, and why this is the only reasonable
answer.** 刀術強化 is described as improving through "長年訓練與精靈族十倍學習速度的複合效果" (long-term
training compounded with the elf race's 10× learning speed) — this is a *specific technique* getting
better through *repeated use of that technique*, structurally unrelated to "how much magic-circle theory
this character understands" (`magic_level`). Folding skill proficiency into `magic_level` would mean a
character's raw magical-theory level rises every time they swing a sword, which the setting's own
language never suggests. Keeping the counters separate also means a character with a very high
`magic_level` (deep theoretical understanding) but no practice with a specific weapon skill correctly
shows low proficiency in that skill, and vice versa.

**Why `growth_rate_multiplier()` is excluded here (repeated from D-3 for this decision's own
completeness)**: change 6's `conferred_growth_rate` buff names its target `magic_level_growth`
specifically; folding it into skill practice as well would apply a buff beyond what it was built and
tested for.

**What is not built**: consuming `skill_proficiency_level()` to scale a skill's actual combat effect
(e.g., a higher-proficiency 刀術強化 hitting harder) is a declared seam for change 9 (`dice-combat`) or a
later balance pass, mirroring change 5's own precedent of declaring `TargetSpec`/`SkillKind` for change 8
to consume without wiring them into a resolver itself. This change builds the counter and its growth
function only.

### D-7. Combat-kill XP: per-`MonsterTier` flat awards, a declared seam, calibrated only in relative
order.

```python
# world/rules/rulebook/progression.yaml
combat_kill_xp:
  low: 20        # F-E tier
  mid: 60        # D-C tier
  high: 150      # B-A tier
  calamity: 500  # S-and-above tier

def grant_combat_kill_xp(entity, monster_tier_key: str) -> None:
    """Declared seam: called once per kill by a future combat-completion
    consumer (change 9's run_battle()/change 10's resolve_overwhelm()
    result, or the eventual top-level combat command change 11's own
    settle_combat_result() names as an unbuilt integration point). A plain,
    unconditional data write; no ownership/resource check."""
    base = COMBAT_KILL_XP_TABLE[monster_tier_key]   # KeyError on an unknown
                                                       # tier key -- fails
                                                       # loudly rather than
                                                       # silently granting 0
    entity.db.magic_xp = (entity.db.magic_xp or 0.0) + base * effective_magic_growth_multiplier(entity)
    _apply_level_ups(entity)
```

These four numbers are invented placeholders, not sourced from `world_info.md` — flagged explicitly for
change 9/16's eventual balance pass, the same discipline every prior change in this project has applied
to its own invented combat/economy constants (change 6's poison/fear percentages, change 2's
`body_enhancement_basic` multiplier). Their only asserted property is relative ordering (`low < mid <
high < calamity`), tested directly — a future balance edit that reorders them incorrectly fails
immediately.

**Quest-reward attachment point, declared and not built.** Change 15 (`quest-runtime`) does not exist
yet. `grant_combat_kill_xp()`'s shape — a flat XP award per named category — is mechanically reusable for
a future quest-completion XP reward (a quest blueprint could name an XP amount the same way a monster
tier names one), but this change does not build a `quest_kill_xp` table, a `QuestBlueprint` field, or any
call site for one. This is named as a reusable seam, not a built attachment point, per the task's explicit
instruction not to build quest content.

## Risks / Trade-offs

- **[Risk] `MAGIC_XP_PER_LEVEL = 600` and the ~4-hours/day study-intensity assumption behind it are both
  invented, undocumented-in-source numbers — a different, equally defensible assumption (e.g., 2 or 6
  hours/day) would change the calibrated constant materially.** → Mitigation: D-5 states the assumption
  explicitly rather than presenting the constant as sourced, and shows the same constant independently
  lands the "ordinary human" 30-50 band inside a plausible range under a different, independently-chosen
  effort assumption — two anchors landing in the right neighborhood from one constant is stronger
  evidence than either alone, but neither removes the underlying invented-assumption risk. Flagged for a
  future balance pass, the same discipline every other change's invented numeric constant already
  carries.
- **[Risk] Change 5's `reincarnation_boon_elosia` `SkillDef.effects` string is not pinned by change 5's
  own artifacts, so `_self_magic_growth_multiplier()`'s `magic_growth_multiplier:` convention may not
  match whatever string change 5's actual implementation assigns her.** → Mitigation: D-3 documents this
  explicitly and tests the interpretation function against a synthetic fixture rather than change 5's
  real seed data; named as a coordination item for the coordinator to verify once change 5 is
  implemented (adjust change 5's implementation, not its artifacts, to use this convention) — mirroring
  skills-equipment's own D-10 precedent for its required one-line adjustment to change 4's `loader.py`.
- **[Risk] The divine-arts (神之秘法) 30-fold casual-vs-dedicated anchor cannot be verified against any
  code this change builds**, since no numeric divine-arts trait exists anywhere in the entity model. →
  Accepted and stated plainly (D-5); building such a trait is entity-traits' (change 3, frozen) scope, not
  this change's, and inventing one here would be exactly the kind of unrequested scope expansion this
  project's design docs consistently avoid.
- **[Risk] `accrue_magic_study()`'s gate on `AdvanceSource.SKIP` means a player who never issues `rest`/
  `sleep`/`wait` — who only ever casts single actions or fights — never accrues ambient study XP, relying
  entirely on `grant_combat_kill_xp()` for all magic-level growth.** → Accepted: this matches the
  setting's own logic (a character who never rests never studies) and gives a player a genuine, visible
  choice between playstyles; it is not a bug, though it does mean a purely combat-focused playthrough's
  growth curve depends entirely on D-7's separately-calibrated (and separately flagged as invented)
  combat-kill constants rather than on the anchors D-5 calibrates against.
- **[Risk] `entity.db.skill_proficiency`'s `SKILL_PROFICIENCY_XP_PER_LEVEL`/`SKILL_PRACTICE_XP_PER_USE`
  constants have no calibration anchor at all** — 刀術強化's card language describes the mechanism
  qualitatively ("long-term training × elf's 10× speed") but gives no numeric level or hours figure to
  calibrate against, unlike `magic_level`'s two concrete anchors. → Accepted and stated explicitly: these
  two constants are pure placeholders, flagged for change 9's eventual balance pass once
  `skill_proficiency_level()` actually feeds into a combat formula (not built by this change, per D-6).
- **[Risk] This change's settlement-stage integration (D-2) cannot be verified end-to-end today**, since
  change 11's `_STAGE_ORDER` does not include a `magic_study` entry and this change does not edit change
  11's artifacts to add one. → Accepted per the task's explicit instruction; `accrue_magic_study()` is
  tested standalone (constructed entities, explicit `seconds`/`source` arguments, no `WorldClock`
  present), mirroring exactly how change 6 tested `tick_buffs()` before change 11 existed to call it. The
  proposal's Impact section names the exact stage/gate/position for the coordinator to carry into change
  11 directly.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/progression.py` does not exist yet. The only sequencing concerns are operational:

- This change must land after change 5 (`SKILL_REGISTRY`/`entity.skills`), change 6
  (`growth_rate_multiplier()`/`entity.buffs`), and change 11 (`AdvanceSource` enum) are all importable —
  matching design doc §11 exactly.
- **Change 11 needs one addition this change does not make directly**: a new settlement stage,
  `magic_study`, in `world/rules/clock.py`'s `_STAGE_ORDER`, positioned between `sexual_decay` and
  `daily_resets`, calling this change's `accrue_magic_study(entities, seconds, source)`. Reasoning for
  this exact position: `magic_study` must be skipped for `AdvanceSource.COMBAT` for the same reason
  `buff_ticks`/`sexual_decay` are (D-1/D-2) — ambient study is a downtime concept, not something that
  happens mid-fight — so it belongs grouped with those two combat-skipped stages rather than with the
  always-on `gauge_regen`/`daily_resets`/world-event stages. It has no computed interaction with either
  `buff_ticks` or `sexual_decay` (independent fields, no shared resource, unlike change 11's own
  regen/poison transposition-test pair), so its position *within* the combat-skipped group is
  order-neutral for correctness; placing it last among the three (immediately before `daily_resets`)
  groups "the three quiet per-entity accruals" together and reads as a natural close to the per-entity
  portion of settlement before the world-event seams begin. This is named here, in this change's own
  design, for the coordinator to apply directly to change 11's `design.md`/`specs/settlement-stage-order/
  spec.md`/`tasks.md` — not made by this change, per the task's explicit instruction.
- **Two thin integration edits to already-built implementation files, not their OpenSpec artifacts** —
  the same "downstream change touches upstream code" pattern change 11 already used on
  `commands/action.py::CmdCast`: a call to `grant_combat_kill_xp()` wherever a future combat-completion
  consumer resolves a kill, and a call to `grant_skill_practice_xp()` wherever a future
  `ActionResolver` integration resolves a successful skill use. Neither call site exists yet (changes 8/9/
  10's own combat/action code is not itself edited by this change beyond naming these two integration
  points) — this change only guarantees the two callables exist with the documented signatures, exactly
  the same "guarantee the callable, not the call site" discipline change 6 used for
  `grant_conferred_growth_rate()`/`growth_rate_multiplier()` before this change existed to call them.

## Open Questions

- **Should quest-completion rewards (change 15, not yet proposed) reuse `grant_combat_kill_xp()`'s exact
  shape, or need their own function?** This change names the reuse as plausible (D-7) but does not decide
  it, since change 15 does not exist yet to have an opinion.
- **Exact `CounterTrait` attribute names** (`.value`/`.max` vs. some other accessor) are left to the
  implementer to confirm against the installed Evennia 6.1.0 `evennia.contrib.rpg.traits` package,
  consistent with the verification discipline every prior change in this project has already established.
- **Should a future change give skill proficiency an upper bound?** No lore source specifies one; left
  unbounded (D-6) until a concrete need (a balance pass, or a UI display cap) surfaces one.
