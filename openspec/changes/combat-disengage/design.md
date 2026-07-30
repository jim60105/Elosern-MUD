## Context

This is roadmap item #10c (design doc §11), depending on changes 9 (`dice-combat`), 10
(`overwhelm-resolution`), and 10b (`monster-behaviour`). All three named this change, by number, as
the owner of the one thing they refused to build:

- Change 9's `Battlefield` (D-6) declares `fled: set[str] = field(default_factory=set)` and reads it in
  `is_present()`/`is_in_range()` (both treat a fled key as "not a valid target") and in `run_round()`'s
  own initiative loop (`key in battlefield.fled` skips that combatant's turn). **Nothing in change 9
  adds a key to it.**
- Change 10's `team_effective_power()`/`hit_rate_verdict()` both filter `key not in battlefield.fled`
  when aggregating a team, and its Migration Plan states plainly that `fled` is populated "once change
  10c lands." **Nothing in change 10 adds a key to it either.**
- Change 10b's own Non-Goals name this exactly: "no dependency this change has access to provides the
  execution mechanism... a future change (unassigned) is the right owner once a flee-execution
  mechanism exists anywhere in the dependency chain for a behaviour tree to call into," and its Open
  Questions ask "should a flee/disengage decision be added once some future change builds a
  `Battlefield.fled` writer?" — deferred to this change by name.
- Change 11 (`world-clock`), landed after all three, went further: its D-6 explicitly **rejected**
  reading `fled` as a danger signal for its skip-safety gate, reasoning that `fled` means "got away
  safely" — the opposite of "in danger" — and stated this in writing specifically so "change 10c's own
  author" would not read the field's *existence* as license to redefine its *meaning*. This design
  does not redefine it: every key this change ever adds to `fled` is added only when the fleeing
  entity has genuinely, mechanically succeeded at leaving the fight — never as a "flee attempted" or
  "flee in progress" marker.

**What already exists for this change to build on, unmodified.** `world/rules/combat.py` (change 9,
public): `Battlefield` (`teams`, `roster`, `fled`), `BattlefieldActionContext`, `effective_power()`,
`COMBAT_YAML["to_hit"]["defender_constant"]` (51 — the recalibrated to-hit constant, dice-combat D-2),
`dice.roll_d100()`, `run_round()` (already skips fled/dead combatants' turns), `is_battle_over()`.
`world/rules/overwhelm.py` (change 10, public): `classify_overwhelm()`, `resolve_overwhelm()` — both
already treat a fled combatant as removed from their team's aggregate, with zero change needed here.
`world/rules/action.py` (change 8, public): `ActionResolver.resolve()`, `RejectedAction`/`RejectReason`,
`PendingEffect`, `register_effect_handler()`, `SNAPSHOTTED_SURFACES`, `_commit()`. `world/skills/
registry.py`/`handler.py` (change 5, public): `SkillDef`, `SkillKind`, `TargetSpec`,
`FactionConstraint`, `SKILL_REGISTRY`, `SkillHandler.owned_keys()`/`effective_value()`. `world/rules/
monster_behaviour.py` (change 10b, public): `monster_behaviour_policy()` — a complete, drop-in
`action_provider`, with no flee branch.

**No code exists yet for this change's own scope.** Nothing named `world/rules/disengage.py` exists.

**What this change explicitly does not touch.** `world/rules/combat.py`, `world/rules/overwhelm.py`,
`world/rules/monster_behaviour.py`, `world/rules/targeting.py`, `world/rules/event_log.py`, and every
`rulebook/*.yaml` file another change already owns (`combat.yaml`, `overwhelm.yaml`,
`monster_behaviour.yaml`). This change is additive against all of their existing public surfaces —
except for two small, named, additive edits to already-landed *implementation* files (not OpenSpec
artifacts) belonging to changes 5 and 8, detailed in D-3 and D-5 below, matching the identical
"downstream change touches upstream code" pattern every change in this roadmap already uses (change 9
registering into change 8's effect registry; change 11 adding one line to `CmdCast`).

## Goals / Non-Goals

**Goals:**
- A `flee` `SkillDef`, registered into change 5's `SKILL_REGISTRY`, castable through the completely
  unmodified `ActionResolver.resolve()` pipeline — ownership, targeting (all four validations, against
  the actor), the `usable_out_of_combat` gate, atomicity, `EventLog` emission, and time cost — with no
  new pipeline step, no new `RejectReason` category beyond what already exists, and no branch anywhere
  in `action.py`/`targeting.py` keyed on "is this a flee attempt."
- A flee-success formula that is the *same* agility-difference formula and the *same* recalibrated
  constant (`51`) dice-combat's own to-hit check already uses — proven, by the identical saturation
  arithmetic dice-combat's own D-2 already worked out, to make escape from a sufficiently
  agility-superior opponent mathematically impossible without any conditional on "is this fight
  overwhelming."
- `Battlefield.fled`'s first-ever writer: a `disengage` effect handler, registered into change 8's open
  effect registry exactly like every other effect handler this project has registered so far.
- A concrete answer to "does fleeing cost anything": the existing turn-loop mechanics (one action per
  round, resolved or not) already make a failed attempt costly with zero new mechanism; this is stated
  and justified, not assumed.
- A named, concrete extension point for change 10b to consume in a future, separate change — not built
  here, not an edit to 10b's artifacts.
- A concrete, one-day-sized extension to `ActionResolver`'s atomicity mechanism covering the one
  mutation surface no effect handler has needed before: a `Battlefield`-level set, not an entity
  substate.
- Golden, fixed-seed tests: a genuine escape (comparable agility), a saturated impossible escape (human
  fleeing an elf), a saturated guaranteed escape (elf fleeing a human), a failed-attempt cost check, a
  rollback-on-injected-failure check for the new `"battlefield"` surface, and an integration test
  proving a fled entity is skipped by `run_round()`'s initiative loop and excluded from
  `classify_overwhelm()`'s team aggregate with zero code change to either function.

**Non-Goals:**
- **No pursuit, re-engagement, or chase mechanic.** Once fled, a combatant simply is no longer a valid
  target or actor in that `Battlefield` — there is no "the monster gives chase" roll, no "return to
  combat" command. Named explicitly per the task's own constraint against building this.
- **No map layers, room relocation, or exit topology** (changes 12-14). A successful flee removes the
  entity from the `Battlefield`'s active contest only; it does not move the entity's Evennia
  `location`. See D-6 for the full account of what this means and what is deliberately left as a seam.
- **No new player-facing command.** `flee` is cast through the already-built `CmdCast` (`cast flee`)
  exactly like any other skill — no `CmdFlee`, no special syntax.
- **No monster decision-making.** This change owns the mechanism `monster_behaviour_policy()` (or any
  future `action_provider`) can call into; it does not decide *when* a monster should flee. That
  remains change 10b's charter, and this change's own contribution to that future work is a named,
  precise follow-up (D-7), not an implementation.
- **No new debuff/buff mechanism.** A failed flee attempt costs exactly what a missed attack already
  costs — a spent turn, nothing more. A supplementary "vulnerable for one round" penalty was considered
  and rejected for this change's scope (D-4) rather than silently omitted.
- **No changes to `run_round()`, `resolve_overwhelm()`, `classify_overwhelm()`, `is_battle_over()`, or
  any `rulebook/*.yaml` file another change owns.** Every one of these already treats a fled combatant
  correctly (skipped in turn order, excluded from team-power sums, excluded from hit-rate saturation
  checks) — this change's only job is populating the set they already all read correctly.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/disengage.py` does not exist yet.

## Decisions

### D-1. `flee` is an ordinary `SkillDef`: `target_spec=SELF`, `faction_constraint=SELF_ONLY`, no
resource cost, not usable out of combat — every field chosen so the existing pipeline does the real
work.

```python
# world/rules/disengage.py
FLEE_SKILL_KEY = "flee"

SKILL_REGISTRY[FLEE_SKILL_KEY] = SkillDef(
    key=FLEE_SKILL_KEY,
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    faction_constraint=FactionConstraint.SELF_ONLY,
    cost={},                        # see below for why zero, not an invented mp/sp price
    usable_out_of_combat=False,
    element=None,
    effects=["disengage:self"],
)
```

Adding one entry to `SKILL_REGISTRY` (a module-level dict change 5 populates but does not close off) is
the identical "later change adds an entry to an already-open registry" pattern this project already
uses everywhere else — change 9 registering `damage:*` handlers into change 8's registry is the direct
precedent; this is the same move one level up, against the skill table itself rather than the effect
table.

**Why `target_spec=SELF`, not `NONE` — this is what makes "gets targeting validation like anything
else" literally true, not merely asserted.** `TargetSpec.NONE` skips targeting entirely (action-resolver
D-5: "the one legitimate short-circuit, not a bypass") — a flee skill built that way would get *zero*
of the four validations, contradicting the hard requirement that fleeing is targeted and validated like
any other action. `SELF` resolves to `[actor]` and, per action-resolver's own D-5, "still runs all four
validations against the actor... uniformity over cleverness": presence (the actor must still be an
active `Battlefield` roster member — rejects a second flee attempt by an already-fled entity with
`TARGET_NOT_PRESENT`), alive (`TARGET_DEAD` — a corpse cannot flee), range (`is_in_range()`, trivially
true for a live, non-fled self), and faction (`SELF_ONLY` accepts only `Relation.SELF`, which
`relation_to(actor, actor)` always returns). This is not decorative: an actor at 0 hp or already in
`battlefield.fled` genuinely cannot cast `flee` again, for free, through the identical mechanism that
already stops them casting anything else — no new check invented.

**Why `faction_constraint=SELF_ONLY`, not `ANY`.** Fleeing is not something one entity does *to*
another; there is no sensible reading of "cast flee on an ally." `SELF_ONLY` is the one existing
`FactionConstraint` value that expresses this without inventing a new one.

**Why `usable_out_of_combat=False` — reusing action-resolver's one sanctioned combat-context read with
zero modification.** Action-resolver's D-3 already checks, at step 1, `if not skill.usable_out_of_combat
and request.context.battlefield is None: reject`. `flee` sets this flag to `False` and needs nothing
else: outside combat there is no `Battlefield` to leave, so `cast flee` correctly and automatically
rejects with `SKILL_NOT_USABLE_OUT_OF_COMBAT` through a check this change does not touch, add to, or
special-case in any way. This is the concrete mechanism behind hard requirement 1's "do not give it a
privileged path" — `flee` doesn't need a privileged path because the ordinary path already does the
right thing for a skill flagged this way.

**Why `cost={}` — zero resource price, not an invented mp/sp number.** Every other `SkillDef` in the
seed registry either costs a resource because it represents trained technique (spells, weapon arts) or
costs nothing because it represents an innate capacity (statically, `status_disguise`, `cost={}` per
change 5's own D-4 seed). Fleeing is the latter category: it requires no training, no mana, no stamina
reserve — only the time to attempt it and the risk of failing. Charging mp/sp for it would need an
invented number with no source in `world_info.md`, and this change's own cost story (D-4) is entirely
about *time* and *opportunity*, not resource depletion — inventing a resource cost on top would be an
unjustified second cost with no distinct rationale.

**No new time-cost override.** `SKILL_TIME_OVERRIDES` (action-resolver D-9) ships empty; `flee` is not
added to it. It uses the same `DEFAULT_CAST_SECONDS` (6) every other unlisted skill uses — a flee
attempt costs exactly one combat round, identical to an attack, a cast, or anything else. No new
constant is invented for this.

### D-2. `INNATE_SKILL_KEYS`: a small, additive extension to `SkillHandler.owned_keys()` so `flee` is
ownable by every `LivingEntity`, regardless of import or spawn data.

**The problem this solves.** `ActionResolver`'s step 1 rejects with `UNKNOWN_SKILL` unless `skill.key in
request.actor.skills.owned_keys()` (action-resolver D-2/D-3). `owned_keys()` (change 5, D-5) currently
returns exactly `entity.db.skills["active"] + entity.db.skills["passive"]` — data populated by the
import loader (players) or, eventually, a bestiary/spawn system (monsters, not built by any change
through 10b). Requiring every character card and every future monster prototype to explicitly list
`"flee"` among owned skills would (a) need edits to change 4's frozen import examples and reference
data, which this change cannot make, and (b) be actively wrong in spirit — fleeing is not a trained
technique some characters have and others lack, it is a universal capacity of anything alive.

**Decision.** A new module-level constant, `INNATE_SKILL_KEYS = frozenset({"flee"})`, and a one-line
addition to `SkillHandler.owned_keys()`:

```python
# world/skills/handler.py — one additive line, change 5's already-landed function
def owned_keys(self) -> list[str]:
    return [*self._raw.get("active", []), *self._raw.get("passive", []), *INNATE_SKILL_KEYS]
```

`INNATE_SKILL_KEYS` is imported from `world.rules.disengage` (this change's own module) — a forward
reference from `world/skills/` into `world/rules/`, the opposite of `world/skills/`'s usual dependency
direction (`world/rules/` depends on `world/skills/`, not the reverse). To avoid inverting the project's
own layering, `INNATE_SKILL_KEYS` is instead **declared in `world/skills/handler.py` itself** (seeded
with exactly `{"flee"}`) and imported *by* `world/rules/disengage.py` when it registers the `flee`
`SkillDef` — the same direction every other cross-reference in this codebase already flows
(`world/rules/` reads from `world/skills/registry.py`, never the other way). This keeps `world/skills/`
free of any dependency on `world/rules/`, matching design doc §3.2's own layering.

**Why this is not a "combat-state branch" and does not need tripwire allow-listing.** Action-resolver's
D-6 tripwire scans `action.py`/`targeting.py`/`event_log.py` for combat-state tokens; `world/skills/
handler.py` is not one of the scanned files, and this addition contains no combat-state concept at
all — it broadens *what an entity owns*, uniformly, regardless of whether a `Battlefield` exists. A
regression test confirms `owned_keys()` includes `"flee"` for a freshly constructed entity with an
empty `entity.db.skills`, proving the grant is unconditional and universal, not combat-gated.

**Why not instead require the import loader / a future bestiary to grant it.** No bestiary/spawn system
exists on the roadmap through change 10b (monster-behaviour's own Non-Goals name this gap explicitly).
Making `flee`'s availability depend on data nothing yet populates would make the mechanism this change
is chartered to build unusable for every `Monster` test fixture and every future monster instance until
some unrelated, unscheduled change lands — a much larger, unjustified dependency for a one-day change to
take on.

### D-3. The `disengage` effect handler: registered exactly like every other effect handler, computing
the flee attempt as a pure staging step (per action-resolver's own D-1 boundary between staging and
committing).

```python
# world/rules/disengage.py
def _handle_disengage(actor, targets, effect_id, event_context) -> list[PendingEffect]:
    battlefield = event_context.get("battlefield")
    if battlefield is None:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "flee: event_context missing required 'battlefield' key",
        )
    success, detail = _attempt_flee(actor, battlefield)   # D-4 — the pure roll, no mutation
    description = (
        f"{actor.key} attempts to flee: succeeds" if success
        else f"{actor.key} attempts to flee: fails"
    )
    return [PendingEffect(
        entity=battlefield,             # see D-5 — deliberately a Battlefield, not a LivingEntity
        description=description,
        surfaces=frozenset(),           # stamped by register_effect_handler()'s own caller, per
                                          # action-resolver D-1/D-7 — never set meaningfully here
        apply=(lambda: battlefield.fled.add(actor.key)) if success else (lambda: None),
    )]

register_effect_handler("disengage", _handle_disengage, surfaces=frozenset({"battlefield"}))
```

This is the identical shape dice-combat's own `_handle_damage` already established for a
roll-then-maybe-mutate effect: the roll happens inside the handler (a pure computation advancing the
RNG stream, touching no entity state, per action-resolver D-1's staging boundary), and the actual
mutation is a zero-argument thunk that only ever runs inside `_commit()`. A failed attempt's thunk
(`lambda: None`) is a genuine no-op, mirroring dice-combat D-5's own miss-case `apply=(lambda: None)` —
not a special case, the same pattern already in production for a different effect kind.

**Why `event_context["battlefield"]` is a required key, not read from `request.context.battlefield`
directly.** Effect handlers registered into action-resolver's registry receive exactly `(actor,
targets, effect_id, event_context)` — a plain dict, not the full `ActionContext` (action-resolver D-7).
This is the same convention 統御術's own handler already uses for its cast-specific parameters
(`confer_skill_key`/`confer_scale`/`confer_trait_keys`, all read from `event_context`) — this change
follows the identical, already-established convention rather than inventing a second way for a handler
to reach caller-supplied data. Whatever constructs the `ActionRequest` for a flee attempt — a future
top-level combat command, or `monster_behaviour_policy()`'s eventual flee branch (D-7) — is responsible
for populating `event_context={"battlefield": battlefield}`, exactly as 統御術's caller is responsible
for populating its own three keys. A missing key rejects with `EFFECT_RESOLUTION_FAILED`, naming the
problem — not a crash, not a silent no-op, mirroring D-7's own established failure mode for a missing
required key.

**Why the returned `PendingEffect.entity` is the `Battlefield`, not the fleeing actor.** The only state
this effect can possibly mutate is `Battlefield.fled` — a fact about the encounter, not about the
actor's own traits, sexual state, buffs, or skill grants. Naming the `Battlefield` as the
`PendingEffect`'s `entity` field is what lets `_commit()`'s existing "build a `touched` set, snapshot
each member, restore on failure" logic (action-resolver D-1) cover this mutation with the smallest
possible extension — see D-5.

### D-4. The flee success check: the *same* agility-difference formula and the *same* recalibrated
constant dice-combat's own to-hit math already uses — the saturation is what makes an overwhelming
opponent unescapable, with no conditional written anywhere for that case.

**The formula, restated from dice-combat's own D-2, applied to a different pair of roles.**
Dice-combat's to-hit check is `hit iff roll_d100() + attacker_agility >= defender_constant +
defender_agility`, which reduces to `hit_rate(Δ) = clamp((50 + Δ)/100, 0, 1)` where `Δ = attacker_agility
− defender_agility` (dice-combat D-2, using the recalibrated `defender_constant = 51`). This change
reuses that exact closed form, substituting "the fleeing entity" for "attacker" and "the fastest living,
non-fled opposing combatant" for "defender":

```python
# world/rules/disengage.py
def _fastest_pursuer_agility(battlefield, actor) -> float | None:
    """The single most dangerous (highest effective agility, after combat
    modifiers) living, non-fled member of the opposing team. See below for
    why the fastest, not the average or the weakest."""
    own_team = battlefield.team_of(actor.key)
    enemies = [
        battlefield.roster[k]
        for team, members in battlefield.teams.items() if team != own_team
        for k in members
        if k in battlefield.roster
        and battlefield.roster[k].traits.hp.value > 0
        and k not in battlefield.fled
    ]
    if not enemies:
        return None   # nothing left to escape from
    return max(_adjusted_agility(e) for e in enemies)

def _adjusted_agility(entity) -> float:
    # Reuses change 5's effective_value() and change 6's evaluate_combat_modifiers() exactly as
    # dice-combat's own to-hit formula (D-5's _handle_damage) already does for agility. Deliberately
    # does NOT apply an 'accuracy' modifier -- accuracy represents precision landing a blow, which has
    # no bearing on outrunning one; only agility (speed/mobility) modifiers transfer to this check.
    from world.rules.combat_modifiers import evaluate_combat_modifiers
    base = entity.skills.effective_value("agility")
    pct = evaluate_combat_modifiers(entity).get("agility")
    return base * (1 + pct / 100) if pct else base

def _attempt_flee(actor, battlefield) -> tuple[bool, dict]:
    pursuer_agi = _fastest_pursuer_agility(battlefield, actor)
    if pursuer_agi is None:
        return True, {"reason": "no_living_pursuer"}   # nothing left to escape from -> trivial success
    actor_agi = _adjusted_agility(actor)
    roll = dice.roll_d100()
    c = combat.COMBAT_YAML["to_hit"]["defender_constant"]   # 51 -- dice-combat's own constant, reused
                                                              # verbatim, never re-declared here
    success = (roll + actor_agi) >= (c + pursuer_agi)
    return success, {"roll": roll, "actor_agility": actor_agi, "pursuer_agility": pursuer_agi}
```

**The hit-rate-style analysis, showing an elf cannot be escaped, without any special-casing.** This is
the identical `hit_rate(Δ) = clamp((50 + Δ)/100, 0, 1)` closed form dice-combat's D-2 already derived and
proved, evaluated at the same reference points that formula's own saturation table used:

| Scenario | `Δ = fleeing_agility − pursuer_agility` | escape rate |
|---|---|---|
| human elite (9) flees human elite pursuer (9) | 0 | **50%** — a genuine coin flip, matching D-2's own parity case |
| human novice (6) flees a low-tier monster (agility 3-8) | +3 to −2 | 48%-53% — contested, matching D-2's adjacent-tier band |
| human elite (9) flees a mid-tier monster (agility 12-20) | −3 to −11 | 39%-47% — contested, harder but not hopeless |
| human elite (9) flees Yuka-tier elf (agility 92) | **−83** | **0%, saturated** — Δ ≤ −50, no roll changes it |
| Yuka-tier elf (92) flees a human elite (9) | **+83** | **100%, saturated** — Δ ≥ +50, always escapes |
| elf (92) flees a stronger elf pursuer (Elosia, 70 — reverse direction) | +22 | 72% — contested, same band D-2's own elf-vs-elf case used |

The human-flees-elf row is exactly dice-combat's own D-2 saturation boundary (`Δ ≤ −50` → guaranteed
miss), reached here with **zero new arithmetic and zero new constant** — it is a direct corollary of
the fact that a human's largest plausible agility (22, `STATIC_TIER_REGISTRY`'s ceiling) minus an elf's
smallest plausible agility (70, the same registry's floor) is `−48`, and every real human/elf pairing
this project's own reference data produces sits at or beyond that gap (dice-combat D-2's own "smallest
possible human/elf gap" language, reused verbatim here). **This is the concrete answer to hard
requirement 2**: a human cannot walk away from an elf that wants them dead, and the reason is the
identical agility-saturation fact that already makes the human unable to land a hit on that elf in the
first place — not a second, independently-invented rule that happens to agree with the first. There is
no `if effective_power_ratio >= threshold: return False` anywhere in `_attempt_flee()` — the function
never reads `effective_power()`, `classify_overwhelm()`, or any overwhelm-threshold concept at all; it
reads exactly two `agility` values and one already-published constant, the same three inputs the to-hit
check itself reads.

**Why the comparison is against the *fastest* living opposing combatant, not the average or a
player-chosen target.** A flee attempt has `target_spec=SELF` — there is no explicit "flee from
entity X" target to name (D-1). If the comparison instead used the *average* agility of all living
opposing combatants, a group containing one very fast, very dangerous pursuer alongside several slow
ones could be escaped merely because the slow ones drag the average down — narratively wrong (a single
fast pursuer is sufficient to prevent escape) and a real loophole in the same shape hard requirement 2
warns against, just relocated to a multi-enemy fight instead of a 1v1 one. Comparing against the single
fastest living, non-fled opponent is the conservative, honest reading of "can this entity actually get
away," and mirrors overwhelm-resolution's own discipline for its hit-rate signal (D-1 of that change:
"a team is only unambiguously hit-rate-overwhelmed if *every* member relationship is saturated" — the
same "the worst case governs, not the average" judgment, applied here to a single fleeing individual
rather than a whole team's verdict).

**Why `evaluate_combat_modifiers()` is reused for agility but not for accuracy.** Design doc §6.4 states
buffs/sexual-state effects "share one modifier pipeline with poison and paralysis — no special-case
branches" (D8). A highly-aroused or poisoned entity's *agility* modifier (design doc's own worked
example: `arousal >= 高度` → `agility: -20%`) is exactly as relevant to outrunning a pursuer as it is to
landing or dodging a blow, so this change reuses the identical `evaluate_combat_modifiers()` call
dice-combat's own to-hit formula already makes for agility. `accuracy` (also part of that same bundle)
represents precision in striking a target and has no bearing on footspeed, so it is deliberately never
read here — the one place this change's reuse of the shared modifier bundle is partial, and this is
recorded explicitly rather than silently reading (and misapplying) the whole bundle.

**No auto-success/auto-failure on a natural roll.** Dice-combat's D-2 explicitly rejected a
natural-100-always-hits/natural-1-always-misses override for the to-hit formula, on the grounds that it
would reintroduce exactly the kind of unearned chance this project's calibration work exists to remove.
This change inherits that reasoning without re-deriving it: `_attempt_flee()`'s `success` check is the
plain `roll + actor_agi >= c + pursuer_agi` comparison, with no natural-roll special case layered on
top.

### D-5. Extending `ActionResolver`'s atomicity mechanism with one new mutation surface,
`"battlefield"` — answering action-resolver's own Open Question about who needs one first.

**The gap this closes.** Action-resolver's `SNAPSHOTTED_SURFACES` (D-1) covers exactly four surfaces —
`traits`, `sexual`, `buffs`, `skill_grants` — all of them **entity** substates, snapshotted and restored
per touched `LivingEntity`. `Battlefield.fled` is not an entity substate at all; it is a plain, mutable
Python `set` living on the `Battlefield` object itself. Registering the `disengage` handler with
`surfaces=frozenset({"battlefield"})` against the *unmodified* `SNAPSHOTTED_SURFACES` would trip
`register_effect_handler()`'s own registration-time gate (`UnsnapshottedSurfaceError`) — correctly, per
its own design, since nothing in `_commit()` today knows how to snapshot or restore a `Battlefield`.
Action-resolver's own design doc named this possibility explicitly and left it open: "should
`SNAPSHOTTED_SURFACES` eventually grow beyond `traits`/`sexual`/`buffs`/`skill_grants`... left to
whichever change (9, 15, or 21) first needs one." It turned out to be this change, not any of the three
named guesses — recorded here as the answer to that question, not a silent override of it.

**Decision — add `"battlefield"` to `SNAPSHOTTED_SURFACES`, and one duck-typed branch to the
snapshot/restore dispatch, alongside the existing per-entity path:**

```python
# world/rules/action.py — additive edit, change 8's already-landed implementation
SNAPSHOTTED_SURFACES = frozenset({"traits", "sexual", "buffs", "skill_grants", "battlefield"})

def _is_battlefield_like(obj) -> bool:
    """Duck-typed, not isinstance-based -- action.py must not import world.rules.combat.Battlefield
    (the opposite dependency direction: combat.py depends on action.py's registry, not vice versa).
    Mirrors this project's established preference for capability checks over import-coupling (e.g.
    monster-behaviour's own hasattr(entity, 'threat_tier') check for the identical reason)."""
    return hasattr(obj, "fled") and hasattr(obj, "roster")

def _snapshot_touched(obj):
    if _is_battlefield_like(obj):
        return {"fled": frozenset(obj.fled)}
    return _snapshot_entity_state(obj)   # existing, unmodified, per-entity path

def _restore_touched(obj, snapshot) -> None:
    if _is_battlefield_like(obj):
        obj.fled = set(snapshot["fled"])
        return
    _restore_entity_state(obj, snapshot)   # existing, unmodified, per-entity path

# _commit()'s existing snapshot/restore calls are redirected through these two new dispatch
# functions in place of calling _snapshot_entity_state()/_restore_entity_state() directly; their
# own bodies are otherwise untouched.
```

**Why this is not a combat-state branch, and does not need tripwire allow-listing.** Action-resolver's
D-6 tripwire polices whether `resolve()`/targeting *behaves differently* depending on combat context —
its forbidden-token list (`in_combat`, `is_combat`, `combat_state`, `isinstance(context, Battlefield`)
targets exactly that concept. `_is_battlefield_like()` dispatches on **the shape of the object a commit
happens to be touching** — a generic, effect-agnostic question `_commit()` already had to answer for
entities (D-1's own language: "a generic, effect-agnostic snapshot") — not on whether the *request*
originated from combat. `resolve()`'s own eight steps, `targeting.py`'s four validations, and the
positive polymorphism proof (D-6's own "identical source, different `ActionContext`, different
outcome" test) are untouched by this addition; a regression test re-runs that exact test unmodified
after this change lands and asserts it still passes, and the source-scan test is re-run against the
edited `action.py` to confirm none of the forbidden tokens were introduced.

**Why a duck-typed shape check, not a new `PendingEffect` field carrying an explicit "kind" tag.** An
earlier alternative considered here added a second `PendingEffect` field (`target_kind: Literal["entity",
"battlefield"]`) so `_commit()` would not need to guess. Rejected: it would require every existing
effect handler (統御術, 狀態偽裝, buff application, conferred growth rate, damage) to be revisited to
set the new field explicitly, for a distinction `_commit()` can already make correctly and cheaply by
inspecting the object it was actually handed — the same "infer from shape, don't demand a new
declaration from every existing caller" preference this project already applied when it chose
duck-typing (`hasattr(entity, "threat_tier")`) over `isinstance` in monster-behaviour D-5, for the
identical reason (avoiding a new coupling or a retroactive edit to already-correct code).

**Why the `Battlefield` snapshot only needs to cover `fled`.** This change's own effect handler (D-3) is
the only registered handler anywhere in the project that declares the `"battlefield"` surface, and it
only ever mutates `.fled`. `_snapshot_touched()`'s `Battlefield` branch snapshots exactly that one
field — not `.teams` or `.roster`, which nothing in this change's scope, or any handler registered so
far, ever mutates. A future handler needing to mutate a different `Battlefield` field would need to
widen this snapshot, exactly the same "the registration-time gate forces a deliberate extension, not a
silent gap" discipline D-1 of action-resolver already established for entity surfaces.

**Rollback proof.** A test stages two `PendingEffect`s in one resolved flee attempt's commit list — the
disengage effect (surface `battlefield`) and a synthetic, test-only second effect on the same entity
whose `apply()` deliberately raises — and asserts that after `_commit()` catches the exception,
`battlefield.fled` does not contain the fleeing entity's key, exactly as if the flee had never been
attempted. This is the direct analog of action-resolver's own "a failure inside the commit operation
rolls back every already-applied effect" scenario, now exercised against the new surface.

### D-6. Where a fleeing combatant goes: removed from the `Battlefield`'s active contest only; the
Evennia room location is untouched, and relocation is named as a seam for changes 12-14.

**What is implementable today.** `Battlefield.fled` (change 9) is a set of entity keys, entirely
independent of any room, coordinate, or exit concept — it already fully determines "is this entity a
valid target or actor in this encounter," which is the *entire* mechanical meaning of "left the fight"
that this project's combat engine (changes 8-10b) actually consumes anywhere. Adding a key to it is
sufficient, on its own, to make `is_present()`, `is_in_range()`, `run_round()`'s turn skip,
`team_effective_power()`, and `hit_rate_verdict()` all immediately and correctly treat the fled entity
as gone from the fight — every one of those consumers is already built and already correct; this change
supplies only the write.

**What this change deliberately does not do.** It does not call anything that moves the entity's
Evennia `location` — no `move_to()`, no exit traversal, no `InstanceRoom` spawn. `Monster`/`PlayerCharacter`
instances remain physically co-located in the same room they occupied when combat began, for both the
fled entity and whoever they fled from. This is not an oversight; it is the honest boundary of what a
coordinate-free, exit-free world can express (changes 12-14 have not landed, mirroring dice-combat's own
D-7 refusal to fake a positional range model before change 12 exists).

**Why this does not read as "they didn't actually get away."** Two already-built mechanisms independently
make the distinction real without any new code:
1. Mechanically, inside combat: a fled entity cannot be targeted, cannot act, and does not count toward
   either side's strength — the fight, for all engine purposes, no longer involves them. This is the
   literal meaning `is_present()`/`is_in_range()`/`run_round()` already give the field.
2. Narratively, outside combat: change 11's `evaluate_skip_safety()` (its own D-6) treats a living
   `Monster` sharing the actor's room as `HOSTILE_PRESENT` **independent of any `Battlefield` at all** —
   so a player who fled the *fight* but is still standing in the same room as the monster they fled
   remains correctly barred from `sleep`/`rest`/`wait`. This is not a contradiction between this change
   and change 11; it is the two changes' scopes fitting together exactly as change 11's own D-6
   anticipated: `fled` means "disengaged from the exchange," never "relocated to safety" — the room
   check is what still guards the latter, and always did.

**The named seam.** A real "flee to an adjacent room" mechanic — one where a successful escape actually
relocates the entity, changing what `evaluate_skip_safety()`'s room check sees — needs a room/exit
topology this project does not have until change 12 (`map-anchor-grid`) at the earliest, and a policy
decision (which adjacent room, chosen how) no change through 10c has been asked to make. This is named
here as future scope for whichever change first has both a room graph and a reason to revisit fleeing's
physical consequences — plausibly change 12's own author, or a later balance pass — not built,
approximated, or guessed at in this change.

### D-7. The extension point for change 10b, and precisely what its archetype table would need — named
as a follow-up, not built here, not an edit to 10b's artifacts.

**The extension point this mechanism exposes today.** Any `action_provider` — `monster_behaviour_policy()`
included — can choose to flee for the entity it is deciding for by returning:

```python
ActionRequest(
    actor=entity,
    skill_key="flee",
    targets=[entity],
    context=BattlefieldActionContext(battlefield),
)
```

with the caller separately populating `context.event_context = {"battlefield": battlefield}` (D-3) for
`ActionResolver.resolve()`'s effect-resolution step to read. This is a complete, already-functional
capability the moment this change lands — no change to `monster_behaviour.py`, `combat.py`, or
`overwhelm.py` is needed for a *decision* to flee to actually execute correctly; only a decision-making
caller choosing to construct this request is missing, and that caller is change 10b's (or a future
change's) to write.

**What change 10b's `monster_behaviour.yaml` and `monster_behaviour_policy()` would need, stated
precisely for the coordinator to carry forward:**
1. **A new per-archetype tunable**, e.g. `flee_hp_fraction: float | None` in each `archetypes` entry —
   the fraction of current-to-max hp at or below which that archetype attempts to flee instead of
   attacking, with `None` (or an unreachable value) meaning "this archetype never flees." A single
   boolean would not fit `world_info.md`'s own framing of differentiated self-preservation instinct
   across tiers (a 巨鼠 fleeing readily; a 古龍 almost never) — a threshold value does, following the
   same "structure in code, tuning in data" discipline change 10b's own D-2 already established for
   `target_strategy`/`skill_choice`.
2. **One new branch in `monster_behaviour_policy()`, evaluated before its existing single-vs-area
   decision**: if `entity.traits.hp.value / entity.traits.hp.max <= profile.flee_hp_fraction` (guarded
   against `None`), return the `ActionRequest` shape shown above instead of proceeding to target/skill
   selection. This slots into change 10b's own decision tree at the same point its existing
   area-vs-single check already sits (10b's own D-2: "single-vs-area is decided before target/skill
   selection"), as one more decision made *before* that one, not a replacement for it.
3. **A policy question 10b's own author must resolve, not answered here**: whether `flee_hp_fraction`
   should be checked once at the top of a monster's turn (this change's own recommendation, since it
   mirrors the existing "decide shape, then act" structure exactly) or interleaved with target/skill
   selection in some other way. This design takes no position beyond naming the tunable and the natural
   insertion point.

This is reported to the coordinator as the concrete shape of a follow-up amendment to change 10b — this
change does not edit `monster_behaviour.yaml`, `monster_behaviour.py`, or any of change 10b's OpenSpec
artifacts to add it.

## Risks / Trade-offs

- **[Risk] `INNATE_SKILL_KEYS` living in `world/skills/handler.py` but seeded specifically for this
  change's own `"flee"` key means a future reader of change 5's file could be confused about which
  change owns that constant.** → Mitigated by an explicit module comment in `handler.py` naming this
  change (10c) as the value's origin and rationale, the same "declare here, attribute the reason"
  discipline this project already uses for cross-change constants (e.g., dice-combat's `51` constant
  carrying its own derivation comment inline in `combat.yaml`).
- **[Risk] The flee-success formula's "compare against the single fastest living opposing combatant"
  rule (D-4) means a fleeing entity facing a large, uniformly slow-but-still-individually-fast-enough
  group could still find escape harder than intuition suggests, if even one member is fast.** → Accepted
  as the correct, conservative reading (D-4's own justification): a single fast pursuer being sufficient
  to prevent escape is the honest mechanical consequence of "you must outrun whoever can catch you," not
  an arbitrary harshness; flagged explicitly rather than silently chosen.
- **[Risk] The new `"battlefield"` mutation surface (D-5) is a duck-typed dispatch inside `_commit()`,
  the single most safety-critical function in the deterministic core — a mistake here risks the
  atomicity guarantee action-resolver exists to provide.** → Mitigated by the explicit rollback test
  (D-5's own "rollback proof") exercising exactly this surface, plus re-running action-resolver's own
  existing atomicity and tripwire test suites unmodified after this change lands, per this change's own
  task list.
- **[Risk] No supplementary "vulnerable for one round" debuff on a failed flee (D-4/proposal Non-Goals)
  means the entire cost of failure is opportunity cost — a wasted turn — which some future playtesting
  could find too mild for the "or players will spam it risk-free" concern this change was asked to
  address.** → Accepted for this change's one-day scope; the opportunity-cost analysis (D-1's time-cost
  discussion) is a real, mechanically-enforced cost identical in kind to a missed attack, and adding a
  new debuff would require either extending change 6's `buffs.yaml` (whose exact `BaseBuff`/
  `BuffHandler.add()` registration signature this change's author has not verified against the
  installed contrib) or inventing a parallel penalty-tracking mechanism outside `BuffHandler` — real
  scope growth for a marginal reinforcement. Flagged explicitly as a candidate for a future balance
  pass, not silently omitted.
- **[Risk] `flee`'s comparison excludes the `accuracy` combat modifier by design (D-4) — a future reader
  extending `evaluate_combat_modifiers()`'s bundle with a new agility-adjacent key could reasonably
  wonder why it isn't read here too.** → Mitigated by an explicit inline comment and D-4's own written
  rationale (accuracy governs landing a blow, not outrunning a pursuer); any future modifier key should
  be evaluated against that same distinction before being added to `_adjusted_agility()`.
- **[Risk] This change's Evennia-side verification is unconfirmed** — whether `Battlefield` (a plain
  Python dataclass, not a Django model) behaves correctly under `transaction.atomic()`'s secondary
  hardening layer (action-resolver D-1) is not something this design can confirm without an installed
  Evennia package. → Flagged for implementer verification, consistent with this project's established
  discipline (changes 1-11) for every Evennia/Django-adjacent assumption; the *primary* atomicity
  mechanism (explicit snapshot/restore, D-5) does not depend on the answer, for the identical reason
  action-resolver's own D-1 gives for entity-state rollback.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/disengage.py` does not exist yet. The only sequencing concerns are operational:

- This change must land after change 9 (`Battlefield`, `COMBAT_YAML`, `dice.roll_d100()`), change 10
  (for its own tests to exercise `classify_overwhelm()`/`resolve_overwhelm()` correctly excluding a fled
  entity — no code from change 10 is called by this change's own production code, only by its
  integration tests), and change 10b (for its own tests to exercise `monster_behaviour_policy()`
  continuing to work unmodified alongside a fled entity), matching design doc §11 exactly. Transitively
  requires changes 5, 6, and 8.
- **Two small, named, additive edits to already-landed implementation files, carried by the
  coordinator**: one line in `world/skills/handler.py::SkillHandler.owned_keys()` (D-2), and the
  `SNAPSHOTTED_SURFACES` constant plus the snapshot/restore dispatch functions in `world/rules/action.py`
  (D-5). Neither touches those changes' OpenSpec artifacts (proposal/design/specs/tasks) — only their
  implementation output, the same pattern change 11 already used for `commands/action.py::CmdCast`.
- **Named follow-up for change 10b** (D-7): a `flee_hp_fraction` tunable and one new decision-tree
  branch in `monster_behaviour_policy()`. Not built here; reported to the coordinator as a precise,
  carriable amendment.
- **Named seam for changes 12-14** (D-6): a real room-relocation consequence of fleeing, once a room/
  exit topology exists. Not built here.
- Change 11 (`world-clock`) is not edited by this change and does not need to be — its own D-6 already
  correctly anticipated this change's semantics for `fled` and explicitly built its skip-safety gate to
  not read `fled` as a danger signal. This change satisfies, rather than needs to update, that design.

## Open Questions

- **Should `flee_hp_fraction` (D-7) vary the *check timing* — top-of-turn only, versus re-evaluated
  mid-decision if a monster's hp changes between its own turn and the moment it would otherwise act?**
  Not resolved here; this change only names the tunable and the natural insertion point, leaving the
  exact mechanics to change 10b's own author, consistent with this change's charter (mechanism, not
  decision).
- **Should a future balance pass add a supplementary failed-flee penalty beyond the opportunity cost
  this change relies on?** Not built here (Risks); left to whoever revisits combat balance once real
  monster movesets and party compositions exist (change 16's territory, mirroring every other invented
  or deliberately-omitted constant's disclosure in this roadmap).
- **Exact `django.db.transaction`/`Battlefield`-under-`transaction.atomic()` interaction** — left to the
  implementer to confirm, consistent with the verification discipline every prior change in this
  roadmap already established; the primary snapshot/restore mechanism (D-5) does not depend on the
  answer.
