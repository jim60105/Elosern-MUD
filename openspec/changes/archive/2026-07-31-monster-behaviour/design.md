## Context

This is roadmap item #10b (design doc §11), depending on change 9 (`dice-combat`) and change 10
(`overwhelm-resolution`). Both named this change by number as the owner of real monster combat AI:

- Change 9's design.md D-9 built `default_attack_policy(entity, battlefield) -> ActionRequest | None`
  as an explicitly-labelled placeholder — "selects a living, non-fled enemy (the lowest-hp one, for a
  deterministic and testable choice) and returns an `ActionRequest` for whichever `damage:*`-effect
  skill the entity owns, or `None` if it owns none" — and its own Risks section states plainly: "always
  targets the lowest-hp living enemy — a predictable, exploitable pattern if it were ever mistaken for
  production monster behaviour... the coordinator has since added change 10b (`monster-behaviour`,
  depends on 9, 10) to the roadmap as its named owner."
- Change 10's design.md and Migration Plan both state: "change 10b (`monster-behaviour`, depends on 9,
  10) is expected to supply the `action_provider` `resolve_overwhelm()` calls for non-player combatants
  once it exists, in place of change 9's own placeholder... this change's own signature already accepts
  any `action_provider`, so change 10b needs no edit to this change's code, only a different callable
  passed in by whatever orchestrates combat."
- Change 3's design.md declared `Monster.behaviour_tree` as a typed placeholder attribute — "present but
  carr[ying] only a default placeholder value" — with no owner named until the coordinator added this
  change to the roadmap specifically to fill it.

**What already exists for this change to build on, unmodified.** `world/rules/combat.py` (change 9,
public): `Battlefield` (two teams, `roster`, `fled`), `BattlefieldActionContext`, `effective_power(entity)
-> float`, `default_attack_policy(entity, battlefield) -> ActionRequest | None`, and `world/rules/dice.py`'s
`roll_d100()`. `world/rules/overwhelm.py` (change 10, public): `resolve_overwhelm(battlefield,
action_provider, max_rounds) -> OverwhelmResult`, which accepts and calls whatever `action_provider` its
caller supplies with no inspection of its identity. `world/rules/action.py` (change 8, public):
`ActionRequest`, `ActionResolver.resolve()`. `world/skills/registry.py` (change 5, public): `SkillDef`,
`SkillKind`, `TargetSpec`, `SKILL_REGISTRY`. `world/lore/monsters.py` (change 2, public):
`MONSTER_TIER_REGISTRY: dict[str, MonsterTier]` with `static_band`/`hp_band`/`example_monsters_zh`.
`typeclasses/monsters.py` (change 3, public): `Monster.threat_tier: str | None` (a real `MonsterTier`
key) and `Monster.behaviour_tree` (declared, defaulting to a placeholder value this change treats as
"unset").

**No code exists yet for this change's own scope.** Nothing named `world/rules/monster_behaviour.py` or
`world/rules/rulebook/monster_behaviour.yaml` exists.

**What this change explicitly does not touch.** `action.py`, `targeting.py`, `event_log.py` (change 8's
scanned, no-combat-branching modules), `combat.py`, `dice.py`, `rulebook/combat.yaml` (change 9),
`overwhelm.py`, `rulebook/overwhelm.yaml` (change 10). This change is purely additive against all of
their existing public surfaces, matching the discipline changes 8/9/10 already established for each
other.

## Goals / Non-Goals

**Goals:**
- `world/rules/rulebook/monster_behaviour.yaml`: a tier→archetype default mapping and a small archetype
  table, every tunable number/string as data, per design doc D9.
- `resolve_behaviour_profile(monster) -> BehaviourProfile`: reads `Monster.threat_tier` for a tier
  default and `Monster.behaviour_tree` for an optional per-instance override, giving that seam (change
  3's, unbuilt since Phase 1) its first real, consumed meaning.
- `monster_behaviour_policy(entity, battlefield) -> ActionRequest | None`: a fully deterministic decision
  tree — single-target vs. area-target, which enemy (or enemies), which owned skill — that differs
  observably across `MonsterTier`s and across the named `world_info.md` archetypes within a tier, using
  only data already available on the acting entity and the battlefield (no new entity state, no new
  effect handler).
- Drop-in `action_provider` conformance: this function's signature and behaviour must work unmodified as
  the `action_provider` passed to change 9's `run_round()`/`run_battle()` and change 10's
  `resolve_overwhelm()` — no edit to either module.
- Deterministic tie-breaking through change 9's seeded `dice.roll_d100()`, never Python's `random`
  module, so a fixed seed reproduces an exact decision sequence for golden tests.
- Golden, fixed-seed tests covering all four tier-default archetypes on an identical battlefield and
  showing the required low-versus-calamity target difference; a seeded tie-break reproducibility test;
  a non-`Monster`-entity delegation test; an integration test proving this policy works unmodified
  inside both `run_round()` and `resolve_overwhelm()`.

**Non-Goals:**
- **No LLM, no generative layer, no call into `world/ai/`.** Hard requirement 1. A source-scan test
  proves `world/rules/monster_behaviour.py` imports nothing from `world/ai/` and calls nothing resembling
  an HTTP client — the identical discipline design doc §7.5's offline-playability acceptance criterion
  demands everywhere else in the deterministic core.
- **No new `ActionResolver` effect handler, `RejectReason`, or targeting rule.** This change's policy
  only ever selects among skills the acting entity already owns and lets change 8's existing pipeline
  (ownership, resource, targeting, capability, effect resolution, deduction, event log, time cost) do
  everything else exactly as it would for a player's `cast` command. No edit to `action.py`,
  `targeting.py`, or `event_log.py` — this change never touches the modules change 8's no-combat-
  branching tripwire scans, so it cannot trip it by construction.
- **No `actions_per_turn`/combat-modifier handling of any kind.** Change 9's `run_round()` already reads
  `evaluate_combat_modifiers(entity)` and skips a zeroed-actions combatant's entire turn **before**
  `action_provider` is ever called (change 9 design.md D-9). This change's function is simply never
  invoked for such a combatant — there is no gate here to duplicate, bypass, or get wrong, and this
  change adds no code that reads `combat_modifiers.yaml`, `entity.buffs`, or `entity.sexual` at all.
- **No monster `SexualState` baselines.** Design doc §6.4 assigns bestiary-sourced `SexualState`
  baselines (most monsters at 普通 sensitivity, `shame` clamped to 無) to whichever change builds the
  bestiary/spawn data — not named on the roadmap yet, and not this change. This change's decision tree
  never reads or writes `entity.sexual`.
- **No flee/disengage mechanic.** Design doc §6.3 lists "flee" as one of three ways a combat encounter
  ends, but no change in this change's dependency chain (8, 9, or 10) ever adds an entity key to
  `Battlefield.fled` — the field is declared and *checked* (`is_present()`, `is_in_range()`) but nothing
  populates it anywhere in the built system. Building a flee-execution mechanic (a new effect ID, a new
  handler, a decision for when a monster "chooses" to disengage) would require inventing a capability no
  dependency owns or has scoped, which is a materially different, larger problem than "which owned skill
  does this monster cast this round." Named explicitly in Risks and Open Questions, not silently
  dropped — downstream change 10c (`combat-disengage`) is the named mechanism owner, and change 10d
  (`monster-flee-decision`, depending on 10b and 10c) owns the later archetype-driven policy branch.
- **No buff/support/conferral skill usage by monsters.** The decision tree selects only from owned
  `ACTIVE` skills whose `effects` include a `damage:`-prefixed ID, mirroring change 9's own
  `default_attack_policy` scope exactly. No named `world_info.md` monster example calls for monster-cast
  buffs, disguises, or conferrals, and modelling "when should a monster buff itself instead of
  attacking" is a materially larger AI problem than this change's one-day budget affords. Flagged as a
  natural next enhancement, not a gap silently left undocumented.
- **No loot tables, crystal drops, world clock, quests, or NPC dialogue behaviour.** Named explicitly
  out of scope by the task brief; this change owns combat decisions only.
- **No spawning, bestiary population, or assignment of `threat_tier`/`behaviour_tree` values to any
  concrete monster instance.** This change reads whatever values already sit on a `Monster` instance; it
  does not decide what a "goblin" NPC's stats or archetype key should be, and it does not build any
  spawn/prototype system. That is scene-builder's (change 21) territory, itself far downstream and out
  of this change's dependency chain.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/monster_behaviour.py`/`rulebook/monster_behaviour.yaml` do not exist yet.

## Decisions

### D-1. `Monster.behaviour_tree` is finally given consumed meaning: an optional archetype-key override
on top of a `MonsterTier`-driven default — no edit to `typeclasses/monsters.py` required.

Change 3 declared `behaviour_tree` on `Monster` but built no behaviour for it — the field exists, typed
loosely, defaulting to a placeholder value (documented as `None`-equivalent). This change is the first to
*read* it, and defines exactly what a non-placeholder value means: a key into this change's own
`monster_behaviour.yaml["archetypes"]` table, naming which behaviour profile that specific monster
instance uses **instead of** its tier's default. `Monster.threat_tier` (already built, change 3) is the
mandatory fallback input — every `Monster` has one, since change 3's own derivation of initial traits
requires it (`build_initial_traits_for_monster_tier()`).

```python
# world/rules/monster_behaviour.py
def resolve_behaviour_profile(monster) -> "BehaviourProfile":
    """Reads Monster.behaviour_tree (change 3's declared, previously-unbuilt seam) as an optional
    per-instance archetype-key override, falling back to the tier's own default archetype keyed by
    Monster.threat_tier (change 2's MonsterTier key). This is the entirety of what 'filling'
    behaviour_tree means for this change -- it does not become a tree data structure of its own;
    the decision *structure* is this module's Python code (D-2/D-3), and behaviour_tree is simply
    which named, YAML-tunable parameter set that structure runs with."""
    override_key = getattr(monster, "behaviour_tree", None)
    if override_key:
        archetype_key = override_key
    else:
        tier_key = monster.threat_tier
        archetype_key = MONSTER_BEHAVIOUR_YAML["tier_default_archetype"][tier_key]
    return BEHAVIOUR_PROFILES[archetype_key]
```

**Why an override on top of a tier default, not one archetype per tier.** `world_info.md`'s own 高階
(B-A) example list — 雙頭龍 (twin-headed dragon), 魔法生物 (magical construct), 巨魔 (troll) — names
three creatures that are not behaviourally interchangeable even though they share a `MonsterTier`: a
魔法生物 is explicitly magical in nature where a 巨魔 is a brute. A single tier→archetype mapping with no
override would force every B-A monster to fight identically, reproducing exactly the "史萊姆 and 古龍
fight the same way" problem this change exists to fix, just moved one level up (now "every B-A monster
fights the same way" instead of "every monster fights the same way"). The override is optional and cheap
— `Monster.threat_tier` alone already produces a sensible, tier-grounded default for any monster nobody
has bothered to flag differently, satisfying hard requirement 4 on its own; the override is what lets a
specific named example (魔法生物) diverge from its tier's modal behaviour without inventing a fifth tier
or a parallel classification axis change 2 does not have.

**Why not make `behaviour_tree` hold a richer structure (an actual tree/graph) that this change
executes.** A generic tree-interpreter would be Python code with no more expressiveness than the
decision function this change writes directly (D-2), for a monster roster this project's own scope (four
tiers, roughly a dozen named examples) does not need. Building a general behaviour-tree *engine* — nodes,
composites, blackboards — for four archetypes is solving a problem one order of magnitude larger than
this change's actual data, and the resulting engine would still need per-archetype leaf parameters
supplied as data (D9) — the YAML table this change already builds. A string key selecting a named,
tested Python function is the simplest thing that satisfies "monsters decide differently by tier," and is
consistent with this project's established discipline of preferring flat, testable data over speculative
generality (e.g. change 2's rejection of deriving one stat axis from another, change 9's rejection of
positional combat before change 12 exists).

### D-2. The decision tree: one Python function, three YAML-tuned leaves (target strategy, skill-choice
strategy, area preference) — structure in code, tuning in data, per design doc D9.

```python
# world/rules/rulebook/monster_behaviour.yaml
tier_default_archetype:
  low: instinctive        # F-E: 史萊姆, 哥布林, 巨鼠 — world_info.md: "初級冒險者能處理的魔獸"
  mid: pack_hunter         # D-C: 狼型魔獸, 食人魔, 地龍 — "一般冒險者數人能對付"，需要組隊
  high: brute              # B-A: 雙頭龍, 魔法生物, 巨魔 — "人類頂尖戰力能敵"
  calamity: apex_predator  # S+: 古龍, 魔神, 災獸 — "已超出人類尺度，落在精靈區間之上"

archetypes:
  instinctive:                          # low tier default
    target_strategy: lowest_hp
    skill_choice: first_owned
    prefer_area_when_multiple_enemies: false
  pack_hunter:                          # mid tier default
    target_strategy: lowest_hp
    skill_choice: highest_expected_damage
    prefer_area_when_multiple_enemies: true
  brute:                                # high tier default
    target_strategy: highest_effective_power
    skill_choice: highest_expected_damage
    prefer_area_when_multiple_enemies: false
  tactical_caster:                      # named-example override for 魔法生物 within "high"
    target_strategy: highest_effective_power
    skill_choice: highest_expected_damage
    prefer_area_when_multiple_enemies: true
  apex_predator:                        # calamity tier default
    target_strategy: highest_effective_power
    skill_choice: highest_expected_damage
    prefer_area_when_multiple_enemies: true
```

```python
@dataclass(frozen=True)
class BehaviourProfile:
    target_strategy: str    # "lowest_hp" | "highest_effective_power"
    skill_choice: str        # "first_owned" | "highest_expected_damage"
    prefer_area_when_multiple_enemies: bool

def monster_behaviour_policy(entity, battlefield) -> "ActionRequest | None":
    if not hasattr(entity, "threat_tier"):
        # Not a Monster (e.g. an NPC ally with no input source wired up yet). This change only
        # changes monster decision quality -- every other entity type keeps change 9's original
        # placeholder behaviour, unmodified, so a mixed battlefield never crashes on a non-Monster
        # turn even before a real player-input dispatcher exists (see D-5).
        return combat.default_attack_policy(entity, battlefield)

    enemies = _living_enemies(battlefield, entity)
    if not enemies:
        return None

    profile = resolve_behaviour_profile(entity)
    owned_damage_skills = _owned_damage_skills(entity)
    single_skills = [s for s in owned_damage_skills if s.target_spec is TargetSpec.SINGLE]
    area_skills = [s for s in owned_damage_skills if s.target_spec is TargetSpec.AREA]

    use_area = (
        profile.prefer_area_when_multiple_enemies
        and len(enemies) > 1
        and bool(area_skills)
    ) or (not single_skills and bool(area_skills))   # fallback: only owns an area skill

    if use_area:
        skill = _choose_skill(entity, area_skills, profile.skill_choice, target=None)
        return ActionRequest(
            actor=entity, skill_key=skill.key, targets="all-enemies",
            context=BattlefieldActionContext(battlefield),
        )

    if not single_skills:
        return None   # owns no usable damage skill at all -- same honest None as change 9's own policy

    target = _choose_target(entity, enemies, profile.target_strategy)
    skill = _choose_skill(entity, single_skills, profile.skill_choice, target=target)
    return ActionRequest(
        actor=entity, skill_key=skill.key, targets=[target],
        context=BattlefieldActionContext(battlefield),
    )
```

`_living_enemies(battlefield, entity)` mirrors change 10's own `_living_members()` helper exactly: the
entity's own team via `battlefield.team_of(entity.key)`, the other team's roster keys, filtered to
`hp.value > 0` and not in `battlefield.fled`. `_owned_damage_skills(entity)` reads
`entity.skills.owned_keys()`, resolves each key through `SKILL_REGISTRY`, and keeps affordable
`SkillKind.ACTIVE` entries whose `effects` contain at least one `damage:`-prefixed ID — the identical
ownership, resource, and prefix reasoning change 9's `default_attack_policy` already uses, made
explicit and reusable here. Filtering before the area-versus-single decision lets an unaffordable area
skill fall back to an affordable single skill instead of producing a resolver rejection every round.

**Why "single-vs-area" is decided before target/skill selection, not after.** Deciding the shape of the
action first means target selection (D-3) only ever runs for the `SINGLE` branch — an `AREA` skill's
targets are the `"all-enemies"` shorthand change 8 already built (`expand_target_shorthand()`), so this
function never computes an area target list itself, and never risks disagreeing with `ActionResolver`'s
own `AREA`-filtering semantics (change 8 D-5: dead/fled candidates silently dropped, empty-after-filter
rejects). Reusing the shorthand is simpler and more correct than re-deriving the same roster this change
already has access to.

### D-3. Target selection and skill selection: two named strategies each, both readable from change 9's
`effective_power()` and change 5's `effective_value()` with no new stat computation invented.

```python
def _choose_target(entity, enemies, strategy: str):
    if strategy == "lowest_hp":
        key_fn = lambda e: e.traits.hp.value                 # current hp -- mirrors default_attack_policy
    elif strategy == "highest_effective_power":
        key_fn = lambda e: -combat.effective_power(e)          # reuse change 9's own function, unmodified
    else:
        raise ValueError(f"unknown target_strategy: {strategy!r}")
    ranked = sorted(enemies, key=key_fn)
    tied = [e for e in ranked if key_fn(e) == key_fn(ranked[0])]
    if len(tied) == 1:
        return tied[0]
    # Deterministic, seed-driven tie-break -- see D-4. Never Python's random module.
    return tied[dice.roll_d100() % len(tied)]
```

- `lowest_hp` (低階/instinctive, 中階/pack_hunter): go for the easiest kill. This is the identical metric
  change 9's own `default_attack_policy` already used — deliberately preserved as the *low-tier* default
  rather than invented anew, since `world_info.md` frames 史萊姆/哥布林/巨鼠 as exactly the unsophisticated
  threat a "novice can handle" (world_info.md: "初級冒險者能處理的魔獸"), and a 狼型魔獸 pack canonically
  singles out the weakest target — the same metric, for a different, lore-grounded reason (opportunism
  vs. coordinated predation), which is why both tiers share this strategy while differing on skill choice
  and area preference instead.
- `highest_effective_power` (高階/brute, 高階/tactical_caster override, 災厄級/apex_predator): go for the
  biggest threat first. Reuses change 9's own `effective_power()` verbatim — no new "how dangerous is
  this enemy" metric is invented; the same function change 10 already trusts for its own team-power
  aggregation is reused here at the individual-target level. Grounded in `world_info.md`'s own framing of
  high/calamity-tier monsters as at or beyond the human ceiling ("與人類頂尖戰力相當", "已超出人類尺度") —
  a monster that powerful has no reason to fear any single party member and every reason to remove the
  most dangerous one first, rather than mopping up stragglers the way a low-tier pack does.

```python
def _choose_skill(entity, candidates: list["SkillDef"], strategy: str, target) -> "SkillDef":
    if strategy == "first_owned":
        return candidates[0]                       # entity.skills.owned_keys()' own deterministic order
    if strategy == "highest_expected_damage":
        def expected(skill: "SkillDef") -> float:
            school = _damage_school(skill)          # parses the skill's own "damage:<school>[:elem]" id
            stat_key = "atk_phys" if school == "physical" else "magic_level"
            atk_stat = entity.skills.effective_value(stat_key)
            if target is not None:
                atk_stat -= target.skills.effective_value("defense")   # target-aware for SINGLE
            return atk_stat
        ranked = sorted(candidates, key=expected, reverse=True)
        tied = [s for s in ranked if expected(s) == expected(ranked[0])]
        if len(tied) == 1:
            return tied[0]
        return tied[dice.roll_d100() % len(tied)]     # same seeded tie-break, D-4
    raise ValueError(f"unknown skill_choice: {strategy!r}")
```

- `first_owned` (低階/instinctive only): no comparison at all — whichever damage skill happens to be
  first in the entity's own owned-skill order. This is deliberately the least sophisticated option,
  reserved for the tier `world_info.md` itself frames as unsophisticated.
- `highest_expected_damage` (every other archetype): compares owned skills by a **no-dice** expected-
  damage figure — `effective_value()` for the attacking stat, minus the target's `effective_value()`
  defense when a single target is already known. This mirrors change 10's own `_expected_damage_per_attack()`
  discipline exactly (a conservative, dice-free estimate used for a decision, not for resolution) —
  reusing an established pattern rather than inventing a third way to estimate damage. No roll is
  consumed by this comparison; the actual to-hit roll and damage roll happen only once, inside
  `ActionResolver.resolve()` → `_handle_damage()`, exactly as they would for any other actor's action.

### D-4. Every tie-break draws from change 9's seeded `dice.roll_d100()`, never Python's `random` module
— the concrete mechanism satisfying hard requirement 2.

Both `_choose_target()` and `_choose_skill()` fall back to `dice.roll_d100() % len(tied)` only when two
or more candidates are genuinely, exactly tied on the relevant metric (equal current hp, equal
`effective_power()`, or equal expected damage) — the common case (a clear lowest-hp or clear
highest-power enemy) never touches the roller at all, keeping the decision path cheap and the RNG stream
undisturbed for the overwhelming majority of turns. When a tie-break does consume a roll, it is the
identical `roll_d100()` wrapper change 9's own to-hit/damage/initiative math already draws from — no
second, parallel RNG source exists anywhere in this change's code, and a fixed-seed golden test can
therefore assert the *exact* tie-broken choice a given seed produces, the same discipline change 9's own
D-10 golden tests already established for combat resolution itself.

**Why a modulo pick, not a re-roll loop or a different tie-break rule.** `tied[dice.roll_d100() % len(tied)]`
is a single roll, always terminates, and is trivially reproducible under a fixed seed — no loop, no
retry, nothing that could behave differently across otherwise-identical runs. A slight non-uniformity
when `len(tied)` does not evenly divide 100 (e.g. 3-way ties are not perfectly 33/33/34) is accepted and
named here rather than silently ignored: ties are rare (most rosters do not have two enemies at exactly
equal current hp or exactly equal `effective_power()`), and this decision's job is determinism and
testability, not statistically perfect fairness among tied candidates — a materially smaller claim than
change 9's own to-hit calibration (D-2 of that change), which does require exact fairness and gets it
from a much larger sample space.

### D-5. Non-`Monster` entities delegate to change 9's `default_attack_policy` unmodified — this change
narrows scope to monster decision quality only, and names the real integration gap honestly.

`run_round()` (change 9) and `resolve_overwhelm()` (change 10) both accept exactly **one**
`action_provider` callable, invoked for every acting combatant regardless of side or type — there is no
dispatch layer anywhere in the built system that routes a player's turn to an input queue and a monster's
turn to an AI function. Building that dispatcher is a real, necessary piece of eventually running a live
combat session with a human player, but it is not named as any change's job on the roadmap today (not
change 9's, not change 10's, not this one's) — it is a composition point for whatever future change wires
up an actual, playable combat command.

```python
def monster_behaviour_policy(entity, battlefield):
    if not hasattr(entity, "threat_tier"):
        return combat.default_attack_policy(entity, battlefield)
    ...
```

This one-line check is what lets this change's function be handed to `run_round()`/`resolve_overwhelm()`
as a single, complete `action_provider` **today**, in every test fixture and in any future integration,
without waiting for that dispatcher to exist: a mixed battlefield (a `Monster` roster fighting a
`PlayerCharacter`/`NPC` roster in a test, or in a future scripted encounter with no live human attached)
gets tier-driven decisions for every `Monster` and the identical, unmodified placeholder behaviour change
9 already ships for anything else. `hasattr(entity, "threat_tier")` — rather than `isinstance(entity,
Monster)` — avoids importing `typeclasses.monsters` into `world/rules/` purely for a type check, matching
this project's existing preference for duck-typed, capability-based checks over import-coupling to
`typeclasses/` from `world/rules/` (the same shape change 6's `combat_modifiers.py` already uses for
`entity.sexual` before change 7 exists).

## Risks / Trade-offs

- **[Risk] `Monster.behaviour_tree`'s override mechanism (D-1) is only as good as whatever assigns it —
  and nothing in this change's dependency chain assigns it to any concrete monster instance.** A
  `Monster` with no bestiary/spawn system ever setting `behaviour_tree` simply always uses its tier
  default, which is a fully correct and tested behaviour, but the "named example gets its own flavour"
  payoff (e.g. 魔法生物 → `tactical_caster`) only manifests once some future change (bestiary/spawn,
  unassigned on the roadmap) actually stamps that key onto the monster instances it creates. → Accepted
  and named explicitly: this change's job is to make the override *consumed* and *correct* the moment it
  is set, not to build the system that sets it — the identical "declare/consume vs. populate" split
  change 5's `ConferredSkillGrant`/`grant_conferred()` already used relative to change 8's cast-time
  write path.
- **[Risk] No flee/disengage behaviour exists, so every monster fights to the death or until the
  encounter otherwise ends (wipe or `max_rounds`/round-bound exit).** A calamity-tier monster at 5% hp
  still presses the attack exactly as it did at 100% hp, which may read oddly for lower tiers that
  `world_info.md` does not frame as suicidally aggressive (a 巨鼠 fighting to the death is less plausible
  than a 古龍 doing so). → Accepted; building flee requires an execution mechanism (a `Battlefield.fled`
  writer) that does not exist anywhere in this change's dependency chain (change 9/10 declare and check
  the field but never populate it) — inventing one here would be a materially larger, unscoped addition
  to change 8's effect-handler registry or change 9's turn loop, neither of which this change is
  chartered to extend. Downstream change 10c owns that execution mechanism; named change 10d
  (`monster-flee-decision`) adds the policy branch after 10c lands.
- **[Risk] `highest_expected_damage`'s target-aware defense subtraction, when comparing `SINGLE` skills,
  assumes the same target already chosen by `_choose_target()` — it does not jointly optimize target and
  skill together.** A monster could in principle do slightly better by picking a *different* target for a
  *different* skill (e.g. a fire-vulnerable target for its fire skill) — this change has no elemental-
  matchup data to make that trade-off (no `world_info.md` source names elemental resistances at the
  per-monster level), so it is not attempted. → Accepted; sequential target-then-skill selection is the
  simplest structure that already produces materially different, tier-grounded decisions, and joint
  optimization over an elemental-matchup axis this project's lore does not yet encode would be
  speculative scope, not a documented gap in the source material.
- **[Risk] The tie-break's slight non-uniformity for tie groups whose size does not evenly divide 100
  (D-4) is a known, accepted imprecision.** → Accepted and named; this signal's job is determinism and
  testability under a fixed seed, not statistically perfect fairness among rare exact ties — a
  categorically smaller claim than change 9's own to-hit calibration, which does require exact fairness
  and achieves it over a much larger sample space (agility deltas across the full `1..100` roll range,
  not a handful of tied candidates).
- **[Risk] `hasattr(entity, "threat_tier")` (D-5) is a duck-typed check that a future `NPC` subclass could
  accidentally satisfy** (e.g. if a later change adds a `threat_tier`-named field to `NPC` for an
  unrelated reason), silently routing that NPC's turns through monster-tier logic instead of the
  placeholder. → Accepted as a low-probability, easily-caught-in-review risk; `threat_tier` is a
  specific, already-namespaced concept (a `MonsterTier` registry key) unlikely to be reused by coincidence,
  and the alternative (`isinstance(entity, Monster)`) would require `world/rules/` to import
  `typeclasses.monsters`, a coupling direction this project's own layering (design doc §3.1) does not
  otherwise require of the deterministic core's rule modules.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/monster_behaviour.py`/`rulebook/monster_behaviour.yaml` do not exist yet. The only
sequencing concerns are operational:

- This change must land after change 9 (`dice-combat`, for `Battlefield`, `BattlefieldActionContext`,
  `effective_power()`, `dice.roll_d100()`, `default_attack_policy`) and change 10
  (`overwhelm-resolution`, for `resolve_overwhelm()`'s `action_provider` contract), and transitively after
  change 8 (`action-resolver`) and change 5 (`skills-equipment`), matching design doc §11 exactly.
- Whoever eventually assigns `Monster.behaviour_tree` values to concrete monster instances (a
  bestiary/spawn system, not on the roadmap under any number yet) needs no edit to this change's code —
  `resolve_behaviour_profile()` already treats any string matching an `archetypes` key as a valid
  override and anything falsy as "use the tier default."
- Whoever eventually builds a live, player-input-driven combat command needs no edit to this change's
  code either — `monster_behaviour_policy()` is a complete `action_provider` today; that future change
  only needs to compose it with a real input source for player turns (e.g. `lambda e, b:
  monster_behaviour_policy(e, b) if hasattr(e, "threat_tier") else player_input_queue.get(e)`), a
  one-line composition this change's own D-5 delegation already anticipates.
- Change 10c (`combat-disengage`) builds the flee-execution mechanism and `Battlefield.fled` writer
  after this change lands. Change 10d (`monster-flee-decision`, depends on 10b and 10c) then extends
  this decision tree with an archetype-driven flee branch without reversing the roadmap dependency.

## Open Questions

- **Resolved downstream: monster flee decisions belong to change 10d.** They are not built here
  (Non-Goals), because no dependency this change has access to provides the execution mechanism.
  Change 10c supplies that mechanism; change 10d then owns the archetype thresholds, top-of-turn
  decision, and retry-by-next-turn behavior.
- **Should monsters ever choose a buff/support skill over a damage skill?** Not built here (Non-Goals) —
  no named `world_info.md` example calls for it, and modelling "when to buff vs. attack" is a materially
  larger AI problem than the one-day budget for tier-grounded target/skill selection. Left to a future
  balance/AI-depth pass if playtesting finds monster combat too simplistic once real party compositions
  exist (mirroring the same "flagged for a future balance pass" disclosure changes 5/6/9/10 already use
  for their own invented placeholder numbers).
- **Who assigns `Monster.behaviour_tree` override values to specific named monsters (e.g. tagging a
  魔法生物 instance `tactical_caster`)?** Not resolved here — no bestiary/spawn system exists yet on the
  roadmap under any number. This change guarantees the override is correctly *consumed* the moment it is
  set; deciding which future change *sets* it is left to whoever eventually builds monster
  spawning/prototyping (plausibly change 21, `scene-builder`, or an unassigned bestiary change).
