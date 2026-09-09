# Field Combat Initiation Design

Date: 2026-09-10
Status: approved by the project owner in a brainstorming session (sections 1-3)
Change split: one rules-layer change (`field-combat-initiation`, described here) →
a follow-up webclient change for the exploration-side cast surface

## 1. Problem and current state

Overwhelm resolution today fires from inside the ordinary combat loop. The only
production dispatch site is `_submit_request()`
(`world/rules/combat_session.py:1163`): whenever
`classify_overwhelm(battlefield)` equals the player's team, the submission is
routed into `resolve_overwhelm()` and the whole encounter collapses into one
compressed record.

Three things are wrong with that placement.

1. **It fires regardless of what the player actually did.** The dispatch is
   gated only on the power verdict. A pure buff, a heal, a disguise, a
   movement skill, or a consumable item all trigger a full attack-power
   settlement, because `resolve_overwhelm()` runs the round loop with the
   default enemy policy after the commanded first action. A player who cast a
   self-buff against a trivially weak monster watches the monster die.
2. **It fires regardless of who was targeted.** `_submit_request()` never
   inspects the request's targets, so a skill aimed at an ally, at the actor,
   or at nothing at all still collapses the encounter.
3. **It removes agency from the ordinary flow.** Once a player is in a session,
   any submission can silently become a whole-encounter settlement instead of
   the round they asked for.

Meanwhile the exploration side has the opposite gap. Out-of-combat casting
exists (`CmdCast._cast_out_of_combat` → `settle_out_of_combat_cast`,
`world/rules/cast_settlement.py:409`), but:

- no damage skill declares `usable_out_of_combat=True`, so
  `world/rules/action.py:310` rejects every damaging cast outside combat;
- `RoomActionContext` (`world/rules/targeting.py`) treats every co-located
  non-self entity as an **ally**, so out-of-combat targeting cannot express
  hostility at all;
- `explore.engage` is the only way to start a fight, and it starts one without
  performing any action, so the first exchange is always a plain round.

## 2. Goals and hard constraints

- **Overwhelm leaves the ordinary combat loop entirely.** After this change,
  no submission inside an existing session can ever compress an encounter.
  This is enforced by making the non-overwhelm path the *default* of the
  shared submission body, not by a convention held in place by a comment.
- **Overwhelm keeps exactly one production call site**, the new field-combat
  entry.
- **Overwhelm requires a damaging action against an enemy.** The verdict alone
  is no longer sufficient.
- **Targeting a co-located hostile monster from exploration always starts
  combat**, whatever the skill does. Only the damage question decides whether
  the encounter is then settled in one shot.
- **Non-damaging and sexual skills keep working on NPCs out of combat,
  unchanged.** That path is not touched.
- **No new settlement machinery.** Loot, XP, `defeat_aftermath`, world-clock
  charging, transaction rollback, and title notifications must all keep
  running through the existing `_submit_request()` → `_continue_or_settle()` →
  `settle_session()` chain.
- **A rejected field cast costs nothing** — no MP/SP, no world time, no
  persisted session.

## 3. Decisions

**D-1. The first discriminator is the target, not the skill.** A skill used in
exploration against a living, co-located, hostile `Monster` always initiates
combat. `DamageEffect` presence decides only whether the encounter is settled
by `resolve_overwhelm()` or played as ordinary rounds.

**D-2. Damage is decided statically.** "This action will damage that enemy
entity" means: the skill definition's parsed `effects` contain a
`DamageEffect`, **and** at least one resolved target belongs to the opposing
team. `"damage:<element>:<school>"` is the only HP-damage effect handler in the
project (`world/rules/combat.py:349`), so the static read is complete. Indirect
HP movement such as `SexualDrainEffect` is deliberately excluded. No
simulation, no preview round, no dice.

**D-3. A damaging skill aimed at a non-monster is rejected.** Opening combat
against NPCs is out of scope (it would touch quests, dialogue, schedules, and
town order). A new `RejectReason` fires before any resource or clock access.
Non-damaging skills aimed at non-monsters continue through
`settle_out_of_combat_cast` exactly as today.

**D-4. Both branches share one session path.** Overwhelm and ordinary opening
differ only in the first step: `resolve_overwhelm()` versus `run_round()`.
Everything downstream is the existing chain.

**D-5. First strike means round-one ordering, not an extra action.** The
player is forced to the head of round one's initiative list; companions and
enemies still act in that same round, after them. Later rounds use ordinary
`roll_initiative()`.

**D-6. AREA damage pulls the whole room in.** An AREA skill opens the session
against every living hostile monster in the room, matching
`classify_overwhelm()`'s own team-versus-team semantics. A SINGLE skill opens
against the named monster only.

**D-7. `basic_attack` becomes usable from exploration.** Without it, clearing
trivial monsters would require spending MP/SP on a real damage skill, since
`explore.engage` deliberately does not act. `explore.engage` keeps its current
meaning — enter combat without acting — and never overwhelms. This amends the
`universal-action-ownership` capability, whose current requirement states that
`basic_attack` is "unusable outside combat"; that clause is replaced by "usable
from exploration only as a field-combat initiation", so the skill still cannot
resolve outside a battlefield.

**D-8. `usable_out_of_combat` stays the gate and gets audited.** The field
entry validates with a `BattlefieldActionContext`, which would make
`world/rules/action.py:310` moot, so the entry checks the flag explicitly.
Every existing skill is reviewed once and the flag set on the merits; the field
keeps its meaning for skills added later.

**D-9. Items never overwhelm.** With the ordinary loop's branch gone and the
field entry accepting skills only, `submit_player_item_use()` always plays one
round.

## 4. Flow

```
Player casts skill S at target T while in exploration
        │
        ├─ T is not a living, co-located, hostile Monster
        │     │        (NPC, companion, self, no target)
        │     ├─ S has DamageEffect ──► rejected (DAMAGE_REQUIRES_MONSTER_TARGET)
        │     │                          no MP/SP, no clock, no session
        │     └─ S has no DamageEffect ─► settle_out_of_combat_cast, unchanged
        │
        └─ T is a living, co-located, hostile Monster ──► combat always starts
              │
              1. Reject unless S.usable_out_of_combat
              2. Select the enemy line-up
                   SINGLE → {T};  AREA → every living hostile monster in the room
              3. Build a candidate Battlefield in memory (not persisted)
              4. Validate with BattlefieldActionContext:
                   revalidate_submission() + ActionResolver.preflight()
                   → rejected ⇒ return; nothing persisted, nothing spent
              5. engage_group(): persist the session, pull in co-located companions
              6. S has DamageEffect and classify_overwhelm() == player team?
                   ├─ yes ─► resolve_overwhelm(), round 1 runs S, player first
                   │           → _continue_or_settle() settles as usual
                   └─ no  ─► one run_round(), player first, action is S
                               → ordinary combat continues from there
```

Two independent questions, each with one job:

| Question | Decides |
| --- | --- |
| Is the target a co-located hostile monster? | Whether combat starts |
| Does the skill damage an enemy, and does the verdict hold? | One-shot or rounds |

## 5. Module split and API

`world/rules/combat_session.py` is already 1697 lines / 66KB. The
exploration-side routing does not belong in it.

### New: `world/rules/combat_initiation.py`

Single purpose: turn one exploration cast into a combat's opening move.

```python
def field_combat_target(actor, target) -> Monster | None:
    """Return target when it is a living, co-located, hostile Monster.

    Hostility is expressed exactly as engage() already expresses it — being a
    Monster instance — so this predicate introduces no second notion of
    hostility.
    """

def initiate_field_combat(actor, skill_key, target, scale=1.0) -> dict:
    """Open combat with one skill as the player's first action.

    Returns the same shape as submit_player_action ("rejected" / "round" /
    a terminal outcome), so the command layer and a future webclient adapter
    share settle_to_messages().
    """
```

Step 3 reuses `reconstruct_battlefield()` against an unwritten
`CombatSessionRecord`. `engage()` already works as "reconstruct, then
`_persist`"; the candidate battlefield simply stops before the second half.

Step 4's use of `BattlefieldActionContext` is load-bearing.
`RoomActionContext` reports every co-located non-self entity as `Relation.ALLY`,
so validating a hostile opening under it would answer the wrong question. The
combat context is the correct one because this cast *is* the fight's first
action.

Dependency direction: `combat_initiation` → `combat_session` / `overwhelm` /
`action_preview`. Nothing depends on it in reverse; `combat_session` does not
know it exists.

### `world/rules/overwhelm.py` — one new pure query

```python
def commanded_damage_reaches_enemy(
    battlefield, actor_key, skill_key, target_keys
) -> bool:
    """True when the skill carries a DamageEffect and at least one target
    sits on the opposing team."""
```

Side-effect free, rolls nothing, recomputable at any time — the same
discipline as `classify_overwhelm()`. It lives here because it is a
precondition of overwhelm, and this module already imports `SKILL_REGISTRY`.

### `world/rules/combat_session.py`

| Item | Change |
| --- | --- |
| `_submit_request()` | Drop the overwhelm branch. Add keyword-only `opening: Literal["round", "overwhelm"] = "round"` and `first_actor: str \| None = None`. The plain round is now the **default**, so "the ordinary flow has no overwhelm" is the program's default behaviour rather than a convention. |
| `submit_player_action()` / `submit_player_item_use()` | Remove their `classify_overwhelm()` calls; they never pass `opening`. |
| `engage()` | Semantics unchanged. Delegates to a new `engage_group(actor, targets)`; `engage(actor, t) == engage_group(actor, [t])`. Both existing call sites (`commands/combat.py:48`, `_engage_adapter`) are untouched. |
| new `submit_opening_action(actor, skill_key, targets, scale)` | The field entry's narrow public seam. Computes `classify_overwhelm() == player_team and commanded_damage_reaches_enemy(...)`, picks `opening` from it, always passes `first_actor=<player key>`, then calls `_submit_request()`. |

The informational `overwhelming_team` value returned by `engage()` and
`_continue_or_settle()` stays: it is a pure query, spec'd, and free.

### `world/rules/combat.py` — first strike

```python
def run_round(battlefield, provider, *, first_actor: str | None = None, ...)
```

`roll_initiative()` still rolls; `first_actor` is then moved to the head of the
sequence with every other position unchanged. `resolve_overwhelm()` takes the
same argument but forwards it **only for round one**
(`_resolve_overwhelm_raw`'s `rounds == 0`); later rounds use ordinary
initiative. With `first_actor=None` the behaviour is identical to today.

### Supporting edits

- `world/rules/action.py`: new `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`;
  `world/rules/player_messages.py` gains its Traditional Chinese message.
- `commands/action.py`: `_cast_out_of_combat()` asks `field_combat_target()`
  first; a monster routes to `initiate_field_combat()` and renders through
  `settle_to_messages()`, anything else keeps the current path.
  `docs/game/commands.md` and `docs/game/command-reference.md` are updated in
  the same change (command-surface documentation contract).
- `world/skills/registry.py`: audit every skill — the 42 `_skill()`
  definitions, the 75 elemental-spell rows, and the sexual-act catalog — and
  set `usable_out_of_combat` on the merits, marking `False` only where casting
  from exploration is nonsensical.

### Deliberately left alone

`resolve_overwhelm(commanded_action_kind="item")` becomes unreachable from
production once items stop compressing. It is a log-marking argument only,
fully tested, and part of the archived `event-log-compression` capability.
Deleting it would churn an archived spec for no behavioural gain, so it stays
as-is with a note that production passes only `"skill"`.

## 6. Edge cases

| Case | Handling |
| --- | --- |
| Reverse overwhelm (the monster far outclasses the player) | `classify_overwhelm()` returns the enemy team, so `opening="round"`: combat opens normally and the player still gets first strike. This preserves today's guarantee that a player is never compressed into an unavoidable defeat — after seeing round one they can still flee. |
| The verdict flips mid-compression, or `max_rounds` is hit | `resolve_overwhelm()` already stops and reports `verdict_after` / `battle_over=False`. The session survives, `_continue_or_settle()` returns `"round"`, and ordinary combat continues. No extra handling. |
| The player already has a session | The field entry is never reached: `CmdCast.func()` checks `read_session()` first and routes to `_cast_in_session`. Unchanged. |
| `usable_out_of_combat=False` | Rejected before step 2 with the existing `SKILL_NOT_USABLE_OUT_OF_COMBAT`. This check must be explicit, because the deliberate use of `BattlefieldActionContext` makes `world/rules/action.py:310` pass. |
| AREA skill in a room with one monster | Identical to SINGLE. Not special-cased. |
| Companions | `engage_group()` reuses `combat_companions(actor)`; the verdict is already team-versus-team, so companion power counts. |
| Liveness and co-location | Decided once inside `field_combat_target()`, immediately followed by `engage_group()`; there is no observable window between them. |
| Healing a monster | Starts combat and plays the heal as the player's first action. Accepted as the direct consequence of D-1; no special case. |
| A sexual skill aimed at a monster | Starts combat, so coercion is scanned by the in-combat `_scan_sexual_coercion()` rather than `cast_settlement._scan_out_of_combat_sexual_coercion()`. Aimed at an NPC, nothing changes. |

## 7. Transaction safety

`engage_group()` persists the session **before** the opening action runs. If
the opening action's transaction fails and raises, the session would survive
and strand the player in a fight that never started.

`initiate_field_combat()` therefore wraps `engage_group()` and
`submit_opening_action()` in one `transaction.atomic()`, so a failure rolls the
session creation back with it.

This nesting is safe and matches existing intent: `_submit_request()`'s
`transaction.on_commit()` comment already states it waits for "the OUTERMOST
transaction", so the round-boundary event and `settle_session()`'s post-commit
work simply defer to the outer commit, while `_submit_request()`'s own
`atomic()` degrades to a savepoint.

The skip-safety registration performed by `engage_group()`
(`register_active_battlefield()`) joins the same failure boundary: a rollback
must also `unregister_participants()`.

## 8. World clock

The opening cast no longer charges `AdvanceSource.COMMAND` time through
`settle_out_of_combat_cast`. It is folded into the session and charged once as
combat time by `settle_session()`. Charging both would double-bill the same
action, which is now literally the fight's first round.

## 9. Observability

`combat_session.py` already uses the `world.observability` facade. A new
boundary info event `field_combat_initiated` carries `char`, `room`, `tick`,
`skill`, `enemy_count`, and `opening` (`"round"` or `"overwhelm"`) in its
context. It is emitted via `transaction.on_commit` on the outer transaction, so
a rolled-back initiation leaves no record.

## 10. Testing

| Test | Type | Coverage |
| --- | --- | --- |
| `world/rules/tests/test_combat_initiation.py` (new) | `EvenniaTest` | The three routing branches (monster / NPC / companion); a damage skill aimed at an NPC is rejected with zero side effects; AREA expands to every room monster; a failed preflight persists no session; a failing opening transaction rolls the session back |
| `test_overwhelm_threshold.py` (extended) | `unittest.TestCase` | `commanded_damage_reaches_enemy()`: pure buff / heal / debuff return `False`; a composite damage skill returns `True`; a damage skill whose targets are all friendly returns `False` |
| `test_combat_session_flow.py` (modified) | `EvenniaTest` | Ordinary submissions **never** compress — even with `classify_overwhelm()` satisfied, `submit_player_action()` runs exactly one round; same for item use |
| `test_overwhelm_resolution.py` (modified) | existing | The equivalence contract is driven through the field entry; the sole-production-call-site assertion points at `combat_initiation` |
| dice-combat round tests (extended) | `unittest.TestCase` | `run_round(first_actor=...)` puts that key first and leaves every other position unchanged; `first_actor=None` is byte-identical to current behaviour |
| `world/skills/tests/` (extended) | `unittest.TestCase` | Every skill carrying a `DamageEffect` has an explicit `usable_out_of_combat` decision, so a newly added skill cannot silently default |

`world.rules.tests.test_combat_initiation` must be registered in
`.github/evennia-shards.json` (the `test_combat_session_*` shard) in the same
change, or `tests.test_evennia_test_optimization_contract` fails on every
later branch.

## 11. OpenSpec capability deltas

- `overwhelm-threshold` — modified: the damage precondition.
- `single-shot-resolution` — modified: sole production call site becomes the
  field entry; `first_actor` for round one; the reverse-direction requirement
  is restated against the new call site.
- `player-combat-session` — modified: no overwhelm in the ordinary flow;
  `engage_group()`; `submit_opening_action()`.
- `combat-resolution` — modified: `run_round(first_actor=...)`.
- `targeting-validation` — modified: the new reject reason.
- `skill-registry` — modified: the `usable_out_of_combat` audit and its
  coverage contract.
- `universal-action-ownership` — modified: `basic_attack`'s "unusable outside
  combat" clause is replaced per D-7.
- `field-combat-initiation` — new capability.

## 12. Out of scope

- The webclient exploration cast surface. There is no `explore.cast` action
  code today and `SkillBook.vue` is a read-only codex, so the UI entry is a
  follow-up change; this one is verified through the `cast` command.
- Opening combat against NPCs (D-3).
- Any change to `settle_out_of_combat_cast` and the non-damaging /
  sexual-skill-on-NPC path.
