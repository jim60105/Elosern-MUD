## Context

`_apply_rate_modifier` (`world/rules/buffs.py:81-96`) applies a damaging buff's
rate tick by mutating `entity.traits.hp` directly and returning nothing;
`tick_buffs` (`world/rules/buffs.py:253-273`) drives those ticks from explicit
game seconds and is called by `_end_of_round_upkeep`
(`world/rules/combat.py:546-552`) after every round's actions. A lethal tick
leaves the foe team non-living, `_terminal_outcome`
(`world/rules/combat_session.py:990-1018`) returns victory from pure HP checks,
but the tick produced no `EventLog`, no `target_defeated` entry, no kill XP
(the action-local staging `_step6_combat_kill_xp`,
`world/rules/action.py:612-642`, never runs), and no quest DEFEAT progress (the
quest planner consumes only `target_defeated` entries,
`world/quests/planner.py:26-43`). Rounds are 6 seconds
(`world/rules/rulebook/combat.yaml:22-23`); the 10-second rate ticks
(`world/rules/rulebook/buffs.yaml:6-14,129-135`) therefore land on the second
upkeep accumulation.

The single-writer boundary must be preserved: `world/rules/` owns all state
mutation; `world/quests/` only plans (returns `PendingEffect` values). The
production composition root is `submit_player_action`
(`world/rules/combat_session.py:892-956`), which wraps `run_round` (or
`resolve_overwhelm`) plus settlement in one outer `transaction.atomic()` with
snapshot/restore of every touched entity surface. `_commit`
(`world/rules/action.py:1068-1098`) stages `PendingEffect` values through the
same snapshot/restore discipline and is already invoked inside that outer
transaction (savepoint semantics).

## Goals / Non-Goals

**Goals:**
- Persist validated effect-source identity (caster dbref) on damaging rate
  buffs at apply time.
- Route lethal rate ticks through a deterministic event-producing boundary so
  HP change, defeat attribution, kill XP, DEFEAT quest progress, and EventLog
  entries commit in the same combat-round transaction.
- Policy parity with direct damage: simulated exams grant no credit; companion
  nonlethal protection floors and marks knocked out; unattributed ticks fail
  closed; no double counting with the applying action.

**Non-Goals:**
- Changing tick math, durations, or the round clock (rulebook values are
  untouched).
- Emitting tick credit outside combat (the world-clock settlement path keeps
  today's event-free behavior).
- Backward-compatibility layers or data migrations for pre-existing buff cache
  entries lacking `source_pk` (unreleased project; such entries settle as
  unattributed).
- Changing the terminal-outcome detection or the session outer-transaction
  seam (`fix-combat-settlement-recovery` remains the owner of that seam).

## Decisions

**D1 — Source identity is authoritative-actor-derived and stored as `source_pk`
in the buff cache.** `_handle_buff_apply` (`world/rules/action.py:350-372`)
computes `source_pk = int(actor.pk)` for any definition whose `rate` modifier
damages HP (`target == "hp"` and `delta < 0`; the catalog's `poisoned`,
`fire_scorch`, `dark_corrosion`), validates it as a positive int, and passes it
into `_add_buff`'s cache data (which `BaseBuff` already exposes as buff
attributes — the `conferred_growth_rate` buff's `source_key`/`scale` are the
precedent). A caller-supplied `source_pk` in `buff_kwargs` is popped and never
trusted: attribution always comes from the resolving actor, so it cannot be
spoofed. An actor without a resolvable dbref rejects the action (fail closed).
Direct `_add_buff` calls outside the handler simply omit `source_pk`, and such
buffs tick as unattributed (D6). Refresh semantics are the Evennia
`BuffHandler.add` contract (verified in
`evennia/contrib/rpg/buffs/buff.py:497-515`): re-applying the same buffkey
replaces keys present in the new cache, so the latest caster owns the DoT; a
refresh whose new cache omits `source_pk` *retains* the prior cached value, so
attribution never silently flips to a deleted caster. *Alternatives
considered:* storing the actor's display `key` (collides across entities; the
quest planner already keys on dbrefs), and trusting `buff_kwargs`
(spoofable, rejected).

**D2 — `tick_buffs` keeps its apply-on-tick contract and additionally returns
an ordered tuple of damaging `TickRecord` values.** A `TickRecord` is a frozen
dataclass in `world/rules/buffs.py`: `definition_key`, `source_pk (int | None)`
(from the buff cache, via `getattr(buff, "source_pk", None)`), `delta`, and
`hp_before` (the entity's HP immediately before that tick applied, so the
settlement can detect the crossing deterministically after the fact). Records
are collected inside the existing accumulation loop, in application order,
only for rate ticks targeting `hp` with negative delta; marker and
growth-rate buffs apply as today and yield no records. The world-clock callers
(`world/rules/clock.py:181-185`) ignore the return value and observe exactly
today's behavior (D6's "no events outside combat"). `_end_of_round_upkeep`
collects only tuple returns (`tick_buffs` always returns a tuple; a non-tuple
return is treated as no ticks), which keeps existing tests that patch
`world.rules.combat.tick_buffs` green.

**D3 — A new `world/rules/upkeep.py` settlement consumes the records and
stages everything through the existing `PendingEffect`/`_commit` machinery.**
`settle_upkeep(battlefield, records_by_key, *, simulated, nonlethal_keys)`
runs after `_end_of_round_upkeep` inside `run_round`. For each record in
application order it: (a) emits a `damage` EventLog entry reporting the *actual
applied* amount (`min(-delta, hp_before)`, matching the action path, whose
gauge clamp means a -5 tick on a target at 2 HP really removes 2 HP); (b)
detects the lethal crossing from `hp_before > 0 and hp_before + delta <= 0`;
(c) emits exactly one defeat entry per target (shared per-target
`defeated_ids`, same shape as `_defeated_entry`'s output — `data["target_id"]`
int dbref, `data["monster_tier"]`, optional `data["simulated"]`), so
`_defeated_targets` (`world/quests/planner.py:26-43`) and every kill-credit
consumer work unchanged; (d) for attributed lethal ticks on `Monster` targets
with a registry tier, stages one `grant_combat_kill_xp` effect mirroring
`_step6_combat_kill_xp`'s commit-time guard; (e) builds one `EventLog` per
attributed source (actor = source key, `skill_key = "combat_upkeep"`) and runs
every registered event-effect planner in `_EVENT_EFFECT_PLANNERS` — only for
sources whose entry set contains a defeat entry (mirroring the planner's own
early return) — with a request-shaped object carrying the source as `actor`
and the battlefield in `context.battlefield`, so the quest planner's
actor/companion/protected-entity logic applies unchanged. All staged mutations
(nonlethal floors, `knocked_out` marks, XP, quest effects) are `PendingEffect`
values committed in one `_commit` call — inside the session's outer
transaction this is the same unit as the round; a failure aborts the round and
the session restore rolls back every surface. The upkeep `damage` entries join
the round logs, so the session's existing `_scan_friendly_fire`
(`world/rules/combat_session.py:925`) evaluates a player's own DoT landing on
an ally exactly like direct damage (a deliberate consequence of the boundary,
not a new rule). *Alternatives considered:* reusing `ActionResolver.resolve`
with a synthetic skill (invents fake skills and rolls), and reusing
`_step6_combat_kill_xp` directly (its staging-time `hp <= 0` skip is wrong for
post-tick staging).

**D4 — `run_round` owns the settlement and takes keyword-only policy flags.**
`run_round(battlefield, action_provider, *, simulated=False,
nonlethal_keys=frozenset())` runs actions, then `_end_of_round_upkeep`, then
the upkeep settlement. Owning the settlement inside `run_round` (rather than
in the session) makes ordinary rounds and overwhelm compression rounds behave
identically — `resolve_overwhelm` gains the same keyword flags and forwards
them to `combat.run_round` **only when they differ from the defaults**, so
default-mode callers (every existing test caller and `run_battle`) observe a
byte-identical call signature; the session's `submit_player_action` passes
explicit values (`simulated=(record.mode == "guild_exam")` and the companion
`nonlethal_keys` derived from `record.player_ids`). The session's
`_context_for` (`world/rules/combat_session.py:423-443`) already computes the
same policy; a small shared helper derives both. The two overwhelm test stubs
that patch `world.rules.overwhelm.combat.run_round` with positional-only
side-effects (`test_overwhelm_resolution.py:86,111`,
`test_monster_behaviour_integration.py`) additionally accept `**kwargs` so an
exam-mode session can never surprise them.

**D5 — No double counting.** Upkeep already skips non-living roster members
(`_end_of_round_upkeep`, `world/rules/combat.py:549`), so a target killed by
the applying action (or an earlier tick round) never ticks again. Within one
upkeep, the settlement processes records in application order with one shared
defeated set per target, so several DoTs firing in one tick (e.g. `poisoned`
and `fire_scorch` at the same 10-second boundary) produce exactly one
`target_defeated` entry and the kill credit goes to the lethal record's
source. Nonlethal policy mirrors `_handle_damage`
(`world/rules/combat.py:246-328`): a protected (companion) crossing floors HP
at 1, stages a battlefield `knocked_out` mark, and emits the same
`target_knocked_out` entry shape the action path emits for a nonlethal
crossing (`_defeated_entry(nonlethal=True)`) — no defeat entry, no kill
credit; simulated rounds tag entries `simulated=True` (the quest planner's
existing skip) and stage no XP. Knockout asymmetry follows the action
pipeline deliberately: kill-XP staging never checks the source's own knockout
state (mirroring `_step6_combat_kill_xp`), while quest credit for a companion
source follows the planner's own `_bound_defeat_owner` knockout rule
(`world/quests/planner.py:150-168`) — a knocked-out companion's tick still
earns the companion magic XP but advances no owner quest, exactly as a
knocked-out companion's direct kill behaves today.

**D6 — Unattributed ticks fail closed.** A lethal tick whose buff cache has no
`source_pk` or whose `source_pk` does not resolve (deleted/absent entity) still
applies its HP damage — the deterministic HP semantics never depend on
attribution — but produces no EventLog entries, no kill XP, and no quest
effects. This is deliberately conservative: with no authoritative actor there
is nobody to credit and nobody whose quests should advance or fail. The world
clock's out-of-combat `tick_buffs` calls are the same unattributed path (they
discard records entirely).

## Risks / Trade-offs

- **More work inside `run_round`** → The production path is always wrapped by
  the session's outer transaction; standalone `run_round`/`run_battle` callers
  (tests and golden fixtures only) get the settlement's own `_commit` atomic
  but not a pre-tick snapshot of the HP mutation. Documented; the golden tests
  patch `tick_buffs` and are unaffected. Mitigation: the settlement stages its
  own mutations through `_commit`, and the session restore covers the tick HP.
- **Pre-existing buff cache entries lack `source_pk`** → They settle as
  unattributed (no credit, no events). No migration per project policy; the
  finding's scenario reproduces only via spells cast after this change.
- **Quest planner failure during upkeep aborts the round** → Matches the
  action pipeline's reject-on-planner-failure contract; in the session the
  whole round rolls back rather than committing a half-credited kill.
- **Overwhelm compression runs many rounds** → Each compressed round settles
  its own ticks (one `_commit` per round); the compressed log summary includes
  upkeep logs like any other round log. No XP or quest effect is skipped or
  duplicated. The positional-only `run_round` side-effect stubs in
  `test_overwhelm_resolution.py`/`test_monster_behaviour_integration.py` are
  widened to accept `**kwargs` (D4).
- **EventLog shape parity is load-bearing** → The settlement must reproduce
  `_defeated_entry`'s data keys exactly; a parity test asserts the upkeep
  defeat entry matches the action-path entry shape that
  `_defeated_targets` and kill-credit consumers parse, and that the `damage`
  entry reports the clamped applied amount.

## Open Questions

- None blocking: the session policy helper's exact placement
  (`combat_session.py` vs. `combat.py`) is an implementation detail for tasks.
