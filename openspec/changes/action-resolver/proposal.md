## Why

Design doc §6.1 names `ActionResolver` as the single deterministic gateway through which every skill
use — combat or not — must pass, and §5.2 states plainly "a skill does not know whether it is in
combat." Today nothing enforces that: change 5 (`skills-equipment`) built `SkillDef`/`SkillHandler`
as pure data and query functions with zero cast-time behavior, change 6 (`buffs-rulebook`) built
`blocks_action()` and the combat-modifier/rulebook engine but explicitly deferred "when an action is
forbidden" to this change, and change 5's own `grant_conferred()` (統御術's partial-conferral write)
and change 6's `grant_conferred_growth_rate()` exist purely as seams with no caller. Without this
change, there is no code path by which a player or an AI-controlled NPC actually invokes a skill —
combat (change 9) and out-of-combat commands would each have to invent their own resolution logic,
guaranteeing the exact "special-cased per context" outcome design doc §5.2 forbids. This change is
also the sole owner of `EventLog`, the structure design doc §3.3 calls "the load-bearing seam" between
deterministic state and every future narration/compression consumer (changes 9, 10, 18) and the
acceptance criterion that the game stays playable with the LLM offline (§7.5, §10).

## What Changes

- Add `world/rules/action.py`: `ActionRequest`, `ActionResolver.resolve()` — the sole entry point
  implementing design doc §6.1's eight-step pipeline (skill ownership → resource check → target
  resolution → action capability → effect resolution → resource deduction → EventLog emission → time
  cost reporting), where every step rejects with a named `RejectReason`, never a bare boolean.
- **Atomicity by construction, not by discipline.** Steps 1-4 are pure reads that either pass or
  reject before anything is staged. Steps 5-6 never mutate state directly — they append
  `PendingEffect` thunks to an in-memory buffer. Steps 7-8 build the `EventLog` and the time-cost
  report from that buffer as pure data, still before any mutation. Only after all eight steps succeed
  does a single `_commit()` call apply every staged effect, wrapped in an explicit snapshot/restore
  transaction (plus a `django.db.transaction.atomic()` hardening layer, since Evennia persists via
  Django ORM per design doc §3.1) — any exception during commit restores every touched entity to its
  pre-commit snapshot and the whole call rejects. "Mana spent but the skill did nothing" has no code
  path: resource deduction is just another item in the same commit as the skill's own effects.
- Add `world/rules/targeting.py`: the four ordered validations (presence → alive → range → faction),
  reading `SkillDef.faction_constraint` — change 5's `FactionConstraint` enum (`ANY`/`ALLY`/`ENEMY`/
  `SELF_ONLY`), added to `SkillDef` during coordinator review as the property of the *skill*, not of
  whoever casts it — and `expand_target_shorthand()` for the combat shortcuts
  `all-enemies`/`all-allies`/`all` — sugar that expands to an explicit list and re-enters the identical
  four validations, bypassing nothing. Combat-vs-non-combat behavior is expressed entirely through an
  `ActionContext` protocol supplied by the caller (a built `RoomActionContext` for out-of-combat use; a
  declared seam, `BattlefieldActionContext`, for change 9) — `targeting.py` and `action.py` contain no
  `if in_combat`-shaped branch anywhere, enforced by a source-scanning regression test in the style
  already established by changes 3 (D-9) and 5 (D-11).
- Add `world/rules/event_log.py`: `EventEntry`/`EventLog` — frozen, JSON-serializable dataclasses with
  no live entity references (entity keys only), and `render_plain_text()`, a minimal reference
  degradation renderer proving the structure is consumable with zero LLM involvement. Designed for all
  four downstream consumers named in design doc §3.3/§6.3/§7.3/§10: change 9 emits one per resolved
  action, change 10 compresses a run of them for overwhelm resolution, change 18's Narrator reads them
  as a pure function, and a hand-written template can render them today.
- Add `commands/action.py`: `CmdCast`, a minimal out-of-combat command (`cast <skill>[=<target>]`)
  demonstrating the same `ActionResolver.resolve()` call combat's future turn scheduler will use —
  proof that a skill's own code never learns which caller invoked it.
- A small, open effect-resolution registry (`EFFECT_HANDLERS`) that this change seeds with the
  handlers it can fully build now (統御術's `confer_skill_partial`, 狀態偽裝's `set_disguise`, a
  self-arming `sexual_event:*` bridge to change 7b's `apply_event()`, and `buff_apply:*`) and declares,
  by name, as the extension point change 9 will register `damage:*` handlers into later — an
  unregistered effect-ID prefix rejects loudly with a named reason today, exactly the same "self-arms
  once its dependency lands" pattern changes 4 and 6 already established. **Every registered handler
  declares the entity-state surfaces it mutates**, checked against exactly what the commit mechanism's
  snapshot/restore covers — a handler declaring an unsupported surface fails loudly at registration,
  before any player can reach it, rather than silently escaping rollback.

## Capabilities

### New Capabilities
- `action-resolution-pipeline`: `ActionRequest`/`ActionResolver.resolve()`, the eight named-reason
  pipeline steps, the staged-effect/commit atomicity mechanism, the effect-handler registry, and the
  structural (source-scanned) guarantee that neither the resolver nor any skill branches on combat
  state.
- `targeting-validation`: the four ordered target validations (reading change 5's
  `FactionConstraint` off `SkillDef`), `SINGLE` vs. `AREA` filtering semantics, combat-shortcut
  expansion as pure sugar, and the `ActionContext` protocol that lets combat and non-combat callers
  share one validation code path with zero special-casing.
- `event-log`: `EventEntry`/`EventLog`'s structure, its serializable/replayable contract, and
  `render_plain_text()` as the reference no-LLM degradation path.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (changes 1–7b have not been archived yet).

## Impact

- **New files**: `world/rules/action.py`, `world/rules/targeting.py`, `world/rules/event_log.py`,
  `commands/action.py`, `world/rules/tests/` (new test modules for this change's scope).
- **Modified files**: none. This change adds no attribute or method to any typeclass another change
  authored — every handler it calls (`entity.skills`, `entity.buffs`, `entity.sexual`,
  `entity.traits`) already exists as a mounted, public seam from changes 3/5/6/7.
- **Depends on**: change 5 (`skills-equipment`) for `SkillDef`/`SkillKind`/`TargetSpec`/
  `FactionConstraint` (the eighth `SkillDef` field, added during review — a skill's legal targets are
  the skill's own property, not the caster's claim), `SkillHandler.grant_conferred()`, and
  `apply_disguise_effect()`; change 6 (`buffs-rulebook`) for `blocks_action()`, `entity_active_buffs()`,
  `BLOCKING_BUFF_KEYS`, and `grant_conferred_growth_rate()`. Matches design doc §11's stated dependency
  (5, 6) exactly.
- **Not a hard dependency, but self-arming**: change 7 (`sexual-state`) and 7b
  (`sexual-transition-rules`) are not on this change's dependency list per §11's roadmap ordering (this
  change is designed to be buildable in parallel with them), so the `sexual_event:*` effect handler
  imports `world.rules.sexual_transitions.apply_event` lazily and rejects with a named, non-crashing
  reason if that module does not exist yet — mirroring change 6's own treatment of `entity.sexual`
  before change 7 landed. A guarded, `pytest.importorskip`-style test proves this transitions from
  skipped to passing once 7b lands, with no edit to this change's code required.
- **Consumers deferred to later changes**: change 9 (`dice-combat`) is expected to call
  `ActionResolver.resolve()` from its turn loop, supply `BattlefieldActionContext`, register `damage:*`
  effect handlers into this change's open registry (declaring their mutation surfaces), and — assigned
  explicitly during this review — replace `RoomActionContext`'s always-`True` `is_in_range()` with a
  real, coordinate-based implementation once change 12 (`map-anchor-grid`) supplies positional data;
  change 10 (`overwhelm-resolution`) is expected to compress multiple `EventLog`s produced by this
  change into one; change 11 (`world-clock`) is expected to read this change's reported time-cost value
  and decide how to advance; change 18 (`narrator`) is expected to consume `EventLog` as a pure function
  and may reuse `render_plain_text()` directly as its own degradation path.
