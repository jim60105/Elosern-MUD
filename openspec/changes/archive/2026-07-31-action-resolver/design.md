## Context

This is roadmap item #8 (design doc §11), depending on change 5 (`skills-equipment`) and change 6
(`buffs-rulebook`). No code exists yet for this change's scope — `world/rules/` currently holds
`traits.py` (change 3), `rulebook/schema.py`, `buffs.py`, `combat_modifiers.py` (change 6); nothing
named `action.py`, `targeting.py`, or `event_log.py`. `commands/` is an empty package created by
change 1.

Two changes already left named, unfilled seams for this one to close:

1. **Change 5's D-6** built `ConferredSkillGrant` and
   `world.rules.skill_effects.record_conferred_grant()` for 統御術's
   partial-conferral mechanic but explicitly deferred "the actual *casting* of 統御術 during play —
   entity A selects entity B as a target, `ActionResolver` validates the interaction, and only then
   calls the conferral write" to this change. Change 5's D-7 similarly built `apply_disguise_effect()`
   for 狀態偽裝 but left "when a player actually casts it" unbuilt.
2. **Change 6's D-4** built `blocks_action(entity)` — "declared seam for change 8's `ActionResolver`
   step 4" — and D-5 built `grant_conferred_growth_rate()`, the rate-of-change counterpart to
   `record_conferred_grant()`, with the identical "seam, not the cast" framing.

Design doc §5.2 states the boundary this change exists to enforce: "A skill does not know whether it
is in combat. `ActionResolver` is the sole entry point; the combat turn scheduler and the out-of-combat
command both call it." §6.1 gives the eight-step pipeline; §6.2 gives targeting's four validations;
§3.3 names `EventLog` as "the load-bearing seam" decoupling narration from state, consumed by the
Narrator (§7.3), by combat's overwhelm compression (§6.3), and required to be template-renderable when
the LLM is offline (§7.5, §10).

**Not on this change's dependency list, by roadmap design.** §11 places changes 7 (`sexual-state`) and
7b (`sexual-transition-rules`) in the same phase as this change but does not list either as a
prerequisite — this change's stated dependencies are exactly 5 and 6. Change 7's own design doc
nonetheless states "change 8 (`action-resolver`) is expected to call change 7b's future `apply_event()`
... from its effect-resolution step." Both statements are true simultaneously only if this change's
sexual-magic effect handler degrades gracefully before 7b exists and self-arms once it does — the
identical shape change 6 already used for `entity.sexual` before change 7 landed (see D-7).

## Goals / Non-Goals

**Goals:**
- `world/rules/action.py`: `ActionRequest`, `ActionResolver.resolve()` — the sole entry point for
  every skill invocation, combat or not, implementing design doc §6.1's eight steps with a named
  `RejectReason` for every failure mode.
- A concrete atomicity mechanism — not "deduct last and hope" — that makes "mana spent but the skill
  did nothing" structurally unreachable, proven by a failure-injection test at each of the eight steps
  plus a dedicated commit-rollback test.
- `world/rules/targeting.py`: the four ordered validations (presence → alive → range → faction),
  reading `SkillDef.faction_constraint` (change 5's `FactionConstraint`, added to its own frozen-in-
  spirit-only field list during review), combat-shortcut expansion as pure sugar, and an
  `ActionContext` protocol that lets combat and non-combat callers share one validation code path with
  no special-casing.
- A structural (not documentary) guarantee that neither `action.py`/`targeting.py` nor any skill
  branches on combat state, mirroring change 3's D-9 and change 5's D-11 source-scanning tripwire
  style.
- `world/rules/event_log.py`: `EventEntry`/`EventLog`, designed for all four named consumers (change
  9's per-action emission, change 10's overwhelm compression, change 18's Narrator, and a hand-written
  template renderer), plus `render_plain_text()` proving the no-LLM path works today.
- `commands/action.py::CmdCast`: a minimal out-of-combat command, concretely proving a skill cast
  outside combat and (by construction) inside combat share the identical resolver call.
- An open effect-resolution registry seeded with every handler this change *can* fully build from
  changes 5/6's existing seams (統御術's conferral, 狀態偽裝, a self-arming sexual-magic bridge, buff
  application), with `damage:*` declared — not built — as change 9's extension point.

**Non-Goals:**
- No dice roll, to-hit formula, or damage math (change 9's job entirely). Any skill whose `effects`
  list contains a `damage:*`-prefixed ID rejects today with a named, honest `UNKNOWN_EFFECT_ID` reason
  — this is the correct state until change 9 registers a handler for that prefix, not a bug this change
  needs to work around.
- No overwhelm threshold or `EventLog` compression logic (change 10) — this change produces one
  `EventLog` per `resolve()` call; concatenating or summarizing several across a combat encounter is
  change 10's job against a structure this change guarantees is flat and mergeable.
- No world clock, scheduled events, or settlement order (change 11) — step 8 *reports* a time-cost
  integer; it calls nothing resembling `WorldClock.advance()` and assumes no ordering relative to
  regen, buff ticks, or sexual decay.
- No Narrator, LLM prompt construction, or retry/guardrail machinery (change 18). `render_plain_text()`
  is a minimal, generic join over `EventEntry.text_template` — proof the structure is sufficient for
  offline rendering, not the production narration path. Change 18 may reuse it verbatim or supersede it.
- No battlefield/combat data model. `BattlefieldActionContext` is declared as a protocol conformance
  target for change 9, not built — this change does not invent turn order, initiative, or a roster
  data structure.
- No exhaustive effect-ID catalogue. A representative handler set (統御術's conferral, 狀態偽裝, one
  sexual-magic bridge, buff application, conferred growth-rate) exercises every effect *shape* this
  change's scope can fully resolve; every other effect ID any of change 5's 24 seed skills carries
  (elemental damage, movement, passive-rank markers) is left to reject loudly with `UNKNOWN_EFFECT_ID`
  until its owning change registers a handler — an honest, self-arming gap, not a silent one.
- No command-syntax grammar beyond `cast <skill_key>[=<target_key>]`. No multi-target selection
  language (`all-enemies but not X`), no ambiguous-name disambiguation prompt.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/action.py`/`targeting.py`/`event_log.py` do not exist yet.

## Decisions

### D-1. Atomicity: a staged `PendingEffect` buffer, committed once via explicit snapshot/restore, with
`transaction.atomic()` as a secondary hardening layer — not a DB transaction alone, and not "deduct
last."

**The problem stated precisely.** Design doc §6.1 says resolution is atomic and flags "mana spent but
the skill did nothing" as the unreachable case. Simply moving resource deduction to the *last* step
(the naive "deduct last and hope" reading the task explicitly rejects) only protects against one
narrow failure mode — it does nothing if effect resolution itself partially applies (e.g., an
AREA-target buff application succeeds on the first two targets and raises on the third), or if
`EventLog` construction or time-cost lookup fails *after* effects already mutated state. Real
atomicity means: **either every one of the eight steps' consequences lands, or none of them do** —
including the deduction, the effect(s), and the very act of producing an `EventLog`.

**Decision — three-phase execution:**

```python
# world/rules/action.py
@dataclass(frozen=True)
class PendingEffect:
    entity: "LivingEntity"          # whose state this effect touches; used for snapshot/restore
    description: str                # human-diagnostic label, folded into EventEntry construction
    surfaces: frozenset[str]        # declared mutation surface(s) — see the coverage-boundary fix below
    apply: Callable[[], None]       # zero-argument mutator — the ONLY place real mutation happens

def resolve(request: ActionRequest) -> ActionResult:
    try:
        skill = _step1_ownership(request)                     # pure read
        _step2_resource_check(request.actor, skill)            # pure read
        targets = _step3_targeting(request, skill)              # pure read + targeting.py
        _step4_capability(request.actor)                        # pure read (blocks_action())
        pending = _step5_effect_resolution(request, skill, targets)   # STAGES, never mutates
        pending += _step6_resource_deduction(request.actor, skill)     # STAGES, never mutates
        event_log = _step7_build_event_log(request, skill, pending)     # pure data, from staged effects
        time_cost = _step8_time_cost(request, skill)                     # pure data
    except RejectedAction as rejection:
        return ActionResult.rejected(rejection.reason, rejection.detail)

    try:
        _commit(pending)                     # the ONLY place any PendingEffect.apply() runs
    except CommitFailed as failure:
        return ActionResult.rejected(failure.reason, failure.detail)

    return ActionResult.success(event_log, time_cost)
```

**Phase 1 (steps 1-4): pure reads.** Nothing is staged yet; a rejection here has zero cleanup to do,
by construction — there is nothing to undo.

**Phase 2 (steps 5-8): staging.** Effect resolution (5) and resource deduction (6) never call a
mutating function directly — they build `PendingEffect` closures over the *real* mutators
(`record_conferred_grant(...)`, `entity.traits.mp.value -= cost`, `apply_event(...)`,
`entity.buffs.add(...)`) without invoking them. `EventLog` construction (7) and time-cost lookup (8)
are pure functions of the staged list plus the request/skill data — they do not need any effect to
have actually run, because they describe *what the pending effects represent*, not *what already
happened*. A failure in any of steps 5-8 raises `RejectedAction` before a single `PendingEffect.apply`
has been called anywhere.

**Phase 3: the one and only commit point — now gated by a surface check, closing a coverage boundary
found in coordinator review.**

The first pass of this design had `_commit()` snapshot exactly four sub-handlers with no check that a
staged effect's actual mutation stayed inside that set. That is a latent, not live, gap today — no
effect handler this change builds touches anything else — but the effect registry (D-7) is
deliberately open, and changes 9 (`damage:*`), 15 (`quest-runtime`, plausibly inventory/quest-state
effects), and 21 (`scene-builder`) will all register new handlers into it. The first one that mutates
inventory, room contents, a spawned object, or a quest record would silently escape rollback,
undermining the one guarantee this change exists to provide. **Fix**: every `PendingEffect` carries the
mutation surface(s) it touches, declared once per handler at registration time, and `_commit()` refuses
to run the action at all if any staged effect declares a surface outside what it snapshots — before
touching a single entity.

```python
SNAPSHOTTED_SURFACES = frozenset({"traits", "sexual", "buffs", "skill_grants"})

class UnsnapshottedSurfaceError(Exception):
    """Raised immediately when register_effect_handler() is called with a surface set outside
    SNAPSHOTTED_SURFACES -- fails loudly at registration time (when change 9/15/21's module
    imports and registers its handler), not silently at resolution time when a player happens
    to cast the one skill that exercises it."""

_EFFECT_HANDLER_SURFACES: dict[str, frozenset[str]] = {}

def register_effect_handler(prefix: str, handler: "EffectHandler", surfaces: frozenset[str]) -> None:
    unsupported = surfaces - SNAPSHOTTED_SURFACES
    if unsupported:
        raise UnsnapshottedSurfaceError(
            f"handler for {prefix!r} declares surfaces {sorted(unsupported)} outside "
            f"_commit()'s snapshot set {sorted(SNAPSHOTTED_SURFACES)} -- extend "
            f"_snapshot_entity_state()/_restore_entity_state() first, or use a supported surface"
        )
    _EFFECT_HANDLERS[prefix] = handler
    _EFFECT_HANDLER_SURFACES[prefix] = surfaces

def _commit(pending: list[PendingEffect]) -> None:
    for effect in pending:
        unsupported = effect.surfaces - SNAPSHOTTED_SURFACES
        if unsupported:
            # Defense in depth: register_effect_handler() already refused this surface set at
            # registration time. This second check catches a PendingEffect that somehow reached
            # here without going through that gate -- it should be unreachable in practice, and
            # a test constructs exactly that unreachable case to prove the gate is not decorative.
            raise CommitFailed(
                RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE,
                f"{effect.description}: surfaces {sorted(unsupported)} outside "
                f"{sorted(SNAPSHOTTED_SURFACES)}",
            )
    touched = {effect.entity for effect in pending}
    snapshot = {entity: _snapshot_entity_state(entity) for entity in touched}
    try:
        with transaction.atomic():           # django.db.transaction — secondary hardening, see below
            for effect in pending:
                effect.apply()
    except Exception as exc:
        for entity in touched:
            _restore_entity_state(entity, snapshot[entity])
        raise CommitFailed(RejectReason.COMMIT_FAILED, str(exc)) from exc
```

`_snapshot_entity_state(entity)` captures the complete raw persistent attributes behind every
substate `SNAPSHOTTED_SURFACES` names, including whether each attribute existed before resolution.
This preserves gauge timestamps and configuration, sexual trait data, the full buff cache,
`disguised_stats`, and `skill_grants` without invoking lazy handlers that create missing attributes.
Restoration replaces or removes those attributes exactly and invalidates cached trait/sexual handlers
so later reads rebuild from the restored persistence. Validation reads gauge backing values without
calling the wall-clock-updating `.value` accessor. This is
a **generic, effect-agnostic snapshot** — it does not need updating every time a new effect handler is
registered *as long as that handler's declared surfaces are already in `SNAPSHOTTED_SURFACES`*; the
moment one is not, `register_effect_handler()`'s own check is what forces `SNAPSHOTTED_SURFACES` (and
`_snapshot_entity_state()`/`_restore_entity_state()` alongside it) to be extended deliberately, rather
than the gap being discovered by a bug report. Extending the set is still the future change's own job
to get right — the registration-time check makes the gap **visible and blocking**, it does not
automatically make a new surface's snapshot/restore logic correct; a test registering a handler that
declares an unsupported surface and asserting the action rejects (both at `register_effect_handler()`
time and, separately, via a test that injects a bad entry directly into `_EFFECT_HANDLER_SURFACES` to
exercise `_commit()`'s own independent, defensive check) is part of this change's own suite.

`_step5_effect_resolution` stamps each returned `PendingEffect`'s `surfaces` field from the handler's
own registered declaration (`dataclasses.replace(effect, surfaces=_EFFECT_HANDLER_SURFACES[prefix])`)
rather than trusting each handler author to set it correctly on every `PendingEffect` they construct —
one source of truth (the registration call), not N call sites that could drift from it. Step 6's
resource-deduction effects are constructed directly by this module (not through the registry) and
always declare `surfaces=frozenset({"traits"})`.

**Why this, and not the alternatives:**

| Alternative | Why rejected |
|---|---|
| Deduct resources last, mutate effects as each resolves | Exactly the case the task calls out — protects only against *the very last step* failing; an AREA effect partially applying across targets, or `EventLog`/time-cost construction failing after effects already ran, still leaves the world mutated with nothing logged. Ordering alone is not atomicity. |
| Ad hoc, per-effect-kind compensating rollback code | Does not scale — every new effect kind (and this project already anticipates several: conferral, disguise, sexual events, buffs, eventually damage) would need its own hand-written undo function, which is exactly the kind of scattered special-casing this project's own tripwire tests (change 3 D-9, change 5 D-11) exist to catch in other contexts. |
| Full event-sourcing (rebuild state by replaying a log) | Would require changes 3/5/6/7's already-landed, direct-mutation handler APIs (`TraitHandler`, `BuffHandler`, `SkillHandler`, `SexualState`) to be rewritten as event-sourced projections — a project-wide rearchitecture, not a one-day change, and explicitly not this change's mandate to impose retroactively on four already-shipped changes. |
| `transaction.atomic()` alone, no explicit snapshot/restore | Considered and kept as a *secondary* layer, not the sole mechanism, for two reasons: (1) it is fully verifiable only against a real Evennia/Django database, and this design cannot confirm today whether `TraitHandler`/`BuffHandler`'s in-memory caching (if any) is strictly bounded by the connection's transaction — an unconfirmed contrib assumption is not something to rest the single most safety-critical property of the whole engine on, consistent with this project's established verify-before-trusting discipline (changes 1–7); (2) it cannot be exercised in a fast, DB-optional unit test the way an explicit Python-level snapshot/restore can, which matters for hitting a one-day budget with real test coverage rather than deferring atomicity tests to a slower `EvenniaTest` DB fixture for every case. |

**Chosen**: the explicit snapshot/restore buffer is the *primary*, fully-specified, fully-testable-in-
plain-Python mechanism; `transaction.atomic()` wraps the same commit block as real-world hardening
against a DB-level failure (a crashed process, a constraint violation) that the in-memory snapshot
cannot see. Flagged for implementer verification (consistent with changes 1–7): the exact
`django.db.transaction` import path and whether Evennia's own `AttributeHandler`/contrib caches are
transaction-safe.

**The result.** Resource deduction (step 6) is staged as `PendingEffect` entries in the *same* list,
committed in the *same* `_commit()` call, as the skill's own effects (step 5). There is no code path
where the commit loop applies the deduction thunk and not the effect thunks, or vice versa, other than
one specific thunk raising mid-loop — which triggers a full restore of every touched entity, deduction
included. "Mana spent but the skill did nothing" requires two independent operations to disagree about
whether they ran; this design has exactly one operation (`_commit()`) that either fully succeeds or is
fully undone.

### D-2. `RejectedAction`/`RejectReason`: one exception type, one enum, for every named rejection across
all eight steps.

```python
class RejectReason(StrEnum):
    UNKNOWN_SKILL = "unknown_skill"                             # step 1
    SKILL_NOT_ACTIVE = "skill_not_active"                        # step 1 — a PASSIVE skill cannot be cast
    SKILL_NOT_USABLE_OUT_OF_COMBAT = "skill_not_usable_out_of_combat"  # step 1
    INSUFFICIENT_RESOURCE = "insufficient_resource"              # step 2
    TARGET_SPEC_MISMATCH = "target_spec_mismatch"                # step 3 — wrong target count/shape
    TARGET_NOT_PRESENT = "target_not_present"                    # step 3
    TARGET_DEAD = "target_dead"                                   # step 3
    TARGET_OUT_OF_RANGE = "target_out_of_range"                   # step 3
    TARGET_FACTION_FORBIDDEN = "target_faction_forbidden"        # step 3
    NO_VALID_TARGETS_IN_AREA = "no_valid_targets_in_area"         # step 3 — AREA, all candidates filtered
    ACTION_FORBIDDEN = "action_forbidden"                         # step 4 — blocks_action()
    UNKNOWN_EFFECT_ID = "unknown_effect_id"                       # step 5 — no registered handler prefix
    EFFECT_RESOLUTION_FAILED = "effect_resolution_failed"         # step 5 — handler-level failure
    RESOURCE_DEDUCTION_FAILED = "resource_deduction_failed"       # step 6 — defensive re-check
    EVENT_LOG_CONSTRUCTION_FAILED = "event_log_construction_failed"  # step 7
    TIME_COST_LOOKUP_FAILED = "time_cost_lookup_failed"           # step 8
    UNSNAPSHOTTED_EFFECT_SURFACE = "unsnapshotted_effect_surface"  # the commit point's surface gate (D-1)
    COMMIT_FAILED = "commit_failed"                                # the single commit point (D-1)

class RejectedAction(Exception):
    def __init__(self, reason: RejectReason, detail: str = ""):
        self.reason = reason
        self.detail = detail

class CommitFailed(Exception):
    """Raised only inside _commit() (D-1) -- either the surface-declaration gate refused to run
    the action (UNSNAPSHOTTED_EFFECT_SURFACE) or a staged effect's apply() raised mid-loop
    (COMMIT_FAILED), in which case every touched entity has already been restored from its
    snapshot before this is raised."""
    def __init__(self, reason: RejectReason, detail: str = ""):
        self.reason = reason
        self.detail = detail
```

Every one of the eight pipeline steps' internal functions raises `RejectedAction` with the specific
reason above rather than returning `False`/`None` — `resolve()` catches it exactly once, at the outer
boundary of phase 1+2, and maps it straight to `ActionResult.rejected(reason, detail)`. This is what
makes "inject a failure at step N" a mechanical, uniform test shape regardless of which step: construct
a scenario where step N's precondition fails, call `resolve()`, assert the exact `RejectReason` and
assert no entity touched by the request changed state. `ActionResult` is a plain frozen dataclass with
a `Literal["success", "rejected"]` outcome discriminator — `event_log`/`time_cost_seconds` present iff
success, `reason`/`detail` present iff rejected.

**Rejections never produce an `EventLog`.** A rejected action changed nothing in the world — there is
nothing for the Narrator to narrate and nothing for the template renderer to render. Player-facing
rejection text is a separate, small `REJECTION_MESSAGES: dict[RejectReason, str]` lookup the command
layer (`CmdCast`) consults directly; it is not routed through `EventLog`/`render_plain_text()`, since
those two are specifically for "what changed in the world," not "why nothing did."

### D-3. `ActionResolver.resolve()` is the sole entry point; the single sanctioned combat-context read is
named, isolated, and allow-listed in the tripwire test — everything else is combat-agnostic by
construction, not by convention.

Design doc §5.2's "a skill does not know whether it is in combat" is satisfied trivially — `SkillDef`
(change 5) carries no combat-state field and this change adds none. The harder claim is that
`ActionResolver`/`targeting.py` themselves must not branch on combat state either. There is exactly
**one** place this change's own pipeline legitimately needs to know anything about combat context at
all: `usable_out_of_combat` (a `SkillDef` field change 5 already built specifically for this purpose)
must be checked against *whether the caller supplied a combat context*. This is not scattered branching
— it is a single, named check at step 1, reading a piece of data the calling `ActionContext` already
has to expose for an unrelated reason (target-shorthand expansion, D-5):

```python
def _step1_ownership(request: ActionRequest) -> SkillDef:
    skill = SKILL_REGISTRY.get(request.skill_key)
    if skill is None or skill.key not in request.actor.skills.owned_keys():
        raise RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)
    if skill.kind is not SkillKind.ACTIVE:
        raise RejectedAction(RejectReason.SKILL_NOT_ACTIVE, request.skill_key)
    # The ONE sanctioned combat-context read in this entire module — see design.md D-3.
    # request.context.battlefield already exists for targeting's shortcut expansion (D-5);
    # this reuses it rather than introducing a second, redundant "am I in combat" flag.
    if not skill.usable_out_of_combat and request.context.battlefield is None:
        raise RejectedAction(RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT, request.skill_key)
    return skill
```

Every other pipeline step — target validation, capability check, effect resolution, resource
deduction, `EventLog` construction, time cost — is **100% identical code regardless of what kind of
`ActionContext` was supplied.** None of steps 2, 3 (beyond the shorthand-expansion helper, which reads
`context.battlefield` for the same, single, already-declared reason), 4, 5, 6, 7, or 8 contains any
reference to combat state. The tripwire test (D-6) allow-lists this one line (by its own doctest-style
marker comment) so a *second*, undeclared branch elsewhere in the module still fails the scan —
visibility, not prohibition, is the goal for the one check the design doc itself mandates.

**Why this is not a loophole.** A future author wanting to special-case *behavior* (not castability)
by combat state — e.g., "effect resolution should compute damage differently in combat" — has no
extension point to reach for here: `context.battlefield` is read exactly once, for exactly one
boolean gate, at exactly one line carrying an explicit marker comment. Adding a second read anywhere
else in `action.py`/`targeting.py` is a new, grep-visible line a code reviewer (or the tripwire test,
once extended) catches immediately, rather than a variant hiding inside an already-approved function.

### D-4. `ActionContext` is a protocol implemented differently by combat and non-combat callers; sharing
one validation code path falls out of polymorphism, not a conditional.

```python
class ActionContext(Protocol):
    battlefield: "Battlefield | None"           # None out of combat; change 9's roster in combat
    def is_present(self, actor, target) -> bool: ...
    def relation_to(self, actor, target) -> Relation: ...   # SELF / ALLY / ENEMY
    def is_in_range(self, actor, target, skill: SkillDef) -> bool: ...

class Relation(StrEnum):
    SELF = "self"
    ALLY = "ally"
    ENEMY = "enemy"
```

`world/rules/targeting.py`'s faction-validation step calls `context.relation_to(actor, target)` and
compares the result against the skill's own declared `FactionConstraint` (D-5) — it has no idea, and
does not need to know, whether `context` represents a room or a battlefield.

**Built now**: `RoomActionContext` — the out-of-combat implementation. `is_present()` checks room
co-location; `relation_to()` returns `Relation.SELF` for the actor itself and `Relation.ALLY` for
every *other* present entity (design doc §6.2: "out of combat there is no hostility model, so `SINGLE`
may target anyone present" — this is the literal mechanism that makes that sentence true, not a special
case bolted on top: `ALLY` is simply what "present, not self" always resolves to here); `is_in_range()`
returns `True` unconditionally (see D-5 on range). `battlefield` is always `None`.

**Declared, not built**: `BattlefieldActionContext` — change 9's job. This change specifies the
protocol it must satisfy (the four members above) and does not guess at `Battlefield`'s own roster,
team-assignment, or positioning data model.

**Alternative considered**: a single `ActionContext` class with an `in_combat: bool` field, branching
internally on that flag inside its own methods. Rejected — this just moves the forbidden branch one
file over (from `action.py`/`targeting.py` into `ActionContext` itself) without removing it, and it
would force one class to know both a room's and a battlefield's semantics. Two classes conforming to
one protocol, selected by the *caller* (the command layer picks `RoomActionContext`; change 9's turn
scheduler picks its own `BattlefieldActionContext`), is what makes the branch disappear rather than move.

### D-5. Targeting: four ordered validations, `FactionConstraint` read from `SkillDef` (not the
request), `SINGLE` vs. `AREA` filtering, and shortcuts as pure sugar.

**Corrected during review: `FactionConstraint` lives on `SkillDef`, not on `ActionRequest`.** The
original draft of this design put the constraint on `ActionRequest`, reasoning that design doc §5.2's
seven `SkillDef` fields were frozen by change 5. That reading was wrong on two counts, per coordinator
review: (1) §5.2 is a design document, not an external, frozen contract like `CHARACTER_SCHEMA_V1` —
change 5 was told to flag a felt need for an eighth field, not that the list was immutable, and it has
since added one; (2) the request is the semantically wrong home regardless of field-count concerns:
which factions a skill may legally target is a property of the *skill*, not of whoever happens to
invoke it. Putting it on the request would let a caller declare a fireball `ALLY`-only or a heal
`ENEMY`-only, and the resolver would have no basis to object — it would be validating the caller's own
claim against itself, not against anything the skill's designer decided.

**Decision, now in force**: change 5's `SkillDef` carries an eighth field,
`faction_constraint: FactionConstraint = FactionConstraint.ANY` (change 5's own `FactionConstraint`
enum — `ANY`/`ALLY`/`ENEMY`/`SELF_ONLY` — declared and populated across its seed set by that change).
This change **imports** `FactionConstraint` from `world.skills.registry` rather than defining a second,
competing enum, and validates `skill.faction_constraint` directly — change 5 declares and populates it,
this change validates it, the identical "declare here, validate in change 8" split already established
for `TargetSpec`/`SkillKind` (change 5's own D-2). The default, `ANY`, is what preserves design doc
§6.2's rule that out of combat, with no hostility model present, `SINGLE` may target anyone present:
only skills that genuinely restrict their targets set anything else.

```python
from world.skills.registry import FactionConstraint   # change 5's enum — not redefined here

def validate_faction(relation: "Relation", constraint: FactionConstraint) -> bool:
    if constraint is FactionConstraint.ANY:
        return True
    if constraint is FactionConstraint.SELF_ONLY:
        return relation is Relation.SELF
    if constraint is FactionConstraint.ALLY:
        return relation in (Relation.SELF, Relation.ALLY)   # self counts as its own ally
    if constraint is FactionConstraint.ENEMY:
        return relation is Relation.ENEMY
```

`Relation` (`SELF`/`ALLY`/`ENEMY`) remains this change's own type — it is the *resolver's* live
read of "what is this target to this actor right now," queried from `context.relation_to()` (D-4),
which is a different axis from `FactionConstraint` (the *skill's* static, authored restriction).
Keeping them distinct types, rather than collapsing to one four-value enum used on both sides, is what
keeps `validate_faction()` a simple, total truth table rather than a function that has to reason about
which of its two enum-typed arguments is the "live" one and which is the "declared" one.

**The four validations, in design doc §6.2's exact order**, each a small pure function taking
`(actor, target, skill, context)` and raising the matching `RejectReason` on failure:

1. **Presence** — `context.is_present(actor, target)`; `TARGET_NOT_PRESENT`.
2. **Alive** — `target.traits.hp.value > 0`; `TARGET_DEAD`.
3. **Range** — `context.is_in_range(actor, target, skill)`; `TARGET_OUT_OF_RANGE`. **Judgment call,
   now with a named owner.** No roadmap item this change depends on has introduced a
   positional/distance data model, so `RoomActionContext.is_in_range()` returns `True` unconditionally
   today — a deliberate, named no-op seam (like `combat_modifiers.py`'s duck-typed sexual-state context
   before change 7 existed), not a missing feature. **Owner: change 9 (`dice-combat`).** Combat is
   where distance first has real consequences — melee versus 弓術 versus 瞬影步's burst movement — and
   change 12 (`map-anchor-grid`) is what will supply the coordinates that make range computable at all;
   this change's `RoomActionContext` has no coordinate system to compute against, out of combat, and
   does not invent one. A test constructs a context whose `is_in_range()` is stubbed to return `False`,
   proving the rejection path itself is real and correctly wired even though production code never
   exercises it as a genuine constraint yet — see Open Questions for the explicit hand-off.
4. **Faction** — `validate_faction(context.relation_to(actor, target), skill.faction_constraint)`;
   `TARGET_FACTION_FORBIDDEN`.

**`SINGLE` vs. `AREA` filtering semantics.** For `TargetSpec.SINGLE`, exactly one target is required;
failing *any* of the four validations rejects the whole action with that validation's specific reason.
For `TargetSpec.AREA`, every candidate is validated independently and a candidate failing any check is
silently dropped from the final target list — an AoE heal where one ally already left the room is
normal, not an error — **except** that if zero candidates remain after filtering, the action rejects
with `NO_VALID_TARGETS_IN_AREA` before effect resolution or resource deduction ever runs. This matters
for the same reason atomicity does: an AoE with nothing left to hit spending its resource cost anyway
would be exactly the "spent but did nothing" bug in miniature, for a target-count edge case rather than
a commit failure — catching it at step 3 means it never reaches staging at all. `TargetSpec.SELF`
always resolves to `[actor]` and still runs all four validations against the actor (no special-casing
"you can't target a dead you," even though that's currently unreachable in practice — uniformity over
cleverness). `TargetSpec.NONE` skips targeting entirely: there is nothing to validate, which is the one
legitimate short-circuit, not a bypass.

**Combat shortcuts are pure sugar.** `expand_target_shorthand(actor, context, shorthand)` — for
`"all-enemies"`/`"all-allies"`/`"all"` — queries `context.battlefield`'s roster (a declared member of
`BattlefieldActionContext`, change 9's job) and returns a plain candidate list, which is then handed to
the *identical* `AREA`-filtering logic above. There is no separate "shortcut resolution" code path that
skips any of the four validations — a dead ally still on the battlefield roster gets included in
`all-allies`' initial candidate list and is then filtered out by the alive check, exactly as if the
caller had spelled out that entity's key explicitly. Out of combat, `context.battlefield is None`, so
these three tokens are meaningless and rejected with `TARGET_SPEC_MISMATCH` if supplied — there is no
roster to expand against.

### D-6. The no-combat-branching tripwire: source scan + signature scan + a positive polymorphism proof.

Mirroring change 3's D-9 (`test_no_forbidden_module_reads_disguised_stats`) and change 5's D-11
(`inspect.signature()` parameter-name scan) exactly:

```python
SCANNED_MODULES = ["world/rules/action.py", "world/rules/targeting.py", "world/rules/event_log.py"]
FORBIDDEN_TOKENS = ["in_combat", "is_combat", "combat_state", "isinstance(context, Battlefield"]

def test_no_undeclared_combat_branch():
    for path in SCANNED_MODULES:
        source = pathlib.Path(path).read_text()
        for token in FORBIDDEN_TOKENS:
            assert token not in source, f"{path} contains a forbidden combat-state token: {token}"

def test_no_combat_shaped_parameter_anywhere():
    # mirrors change 5's D-11 inspect.signature() scan
    for func in _every_public_callable(action, targeting, event_log):
        for name in inspect.signature(func).parameters:
            assert name not in {"in_combat", "combat_state", "turn", "is_combat"}
```

This allow-lists exactly D-3's one sanctioned line (`request.context.battlefield is None`, which
contains none of the forbidden tokens above — `battlefield` is not itself forbidden, since it is a
legitimate, declared `ActionContext` member used for two purposes, D-3's gate and D-5's shortcut
expansion) while still catching a future `if in_combat:`-shaped addition anywhere in these three
modules the moment it is written.

**Positive proof, not just an absence-of-tokens check.** A second test calls `ActionResolver.resolve()`
twice with byte-identical `ActionRequest`s (same actor, same `skill_key` for a skill whose
`SkillDef.faction_constraint` is `FactionConstraint.ENEMY`) differing *only* in which concrete
`ActionContext` is supplied: once with `RoomActionContext` (rejects with `TARGET_FACTION_FORBIDDEN`,
since a room has no enemies) and once with a test double satisfying `ActionContext`'s protocol whose
`relation_to()` reports `Relation.ENEMY` for that same target (the call succeeds). The *only* thing
that differs between the two calls is the context object handed in — `action.py`'s and `targeting.py`'s
own source is byte-identical across both runs — which is the concrete, executable demonstration that
combat-vs-non-combat behavior lives entirely in which `ActionContext` the caller chooses, never in a
branch inside the resolver, and — separately — that the *skill*, not the caller, is what decided this
skill needed an enemy in the first place.

### D-7. Effect resolution: an open, prefix-keyed handler registry — every handler declares the
surfaces it mutates — seeded with what changes 5/6 already expose, `damage:*` declared for change 9,
and a self-arming bridge to change 7b.

```python
# world/rules/action.py
EffectHandler = Callable[["LivingEntity", list["LivingEntity"], str, dict], list[PendingEffect]]
_EFFECT_HANDLERS: dict[str, EffectHandler] = {}
# _EFFECT_HANDLER_SURFACES and register_effect_handler(prefix, handler, surfaces) are defined in D-1,
# alongside SNAPSHOTTED_SURFACES and the UnsnapshottedSurfaceError it raises — the registry and the
# atomicity mechanism are one design, not two independent ones that happen to share a dict.

def _step5_effect_resolution(request, skill, targets) -> list[PendingEffect]:
    pending: list[PendingEffect] = []
    for effect_id in skill.effects:
        prefix = effect_id.split(":", 1)[0]
        handler = _EFFECT_HANDLERS.get(prefix)
        if handler is None:
            raise RejectedAction(RejectReason.UNKNOWN_EFFECT_ID, effect_id)
        surfaces = _EFFECT_HANDLER_SURFACES[prefix]   # already validated a subset of
                                                        # SNAPSHOTTED_SURFACES at registration time
        try:
            new_effects = handler(request.actor, targets, effect_id, request.context.event_context)
        except RejectedAction:
            raise
        except Exception as exc:
            raise RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, f"{effect_id}: {exc}") from exc
        # Stamp every effect with its handler's declared surfaces here, in the one place that reads
        # the registry -- a handler author never sets `surfaces` on the PendingEffect instances it
        # constructs; there is exactly one source of truth per prefix, not N call sites that could
        # drift from each other.
        pending.extend(dataclasses.replace(effect, surfaces=surfaces) for effect in new_effects)
    return pending
```

No conditional in this loop distinguishes one effect kind from another beyond the prefix lookup itself
— adding a new effect kind means registering a new handler (declaring its surfaces), never editing this
function, the identical discipline change 6's D-1 already used for `combat_modifiers.py`'s rule
evaluation.

**Handlers this change builds, reusing changes 5/6's public seams verbatim — never reaching into any
private state — each registered with its declared mutation surface:**

- `confer_skill_partial` → 統御術.
  `register_effect_handler("confer_skill_partial", _handle_confer_skill_partial,
  surfaces=frozenset({"skill_grants"}))`. Stages `record_conferred_grant(target, source_key,
  skill_key, trait_keys, scale)` (change 5's landed deterministic write seam) as a thunk.
  `skill_key`/`scale`/`trait_keys` come from
  `request.context.event_context` (the specific skill/scale a given cast confers, since one opaque
  effect ID cannot itself encode a per-cast choice) — required keys missing raises
  `EFFECT_RESOLUTION_FAILED` naming the missing key, not a silent no-op.
- `set_disguise` → 狀態偽裝. `register_effect_handler("set_disguise", _handle_set_disguise,
  surfaces=frozenset({"traits"}))` — `apply_disguise_effect()` writes `entity.db.disguised_stats`,
  which this change treats as covered by the same `traits`-adjacent surface `_snapshot_entity_state()`
  already walks alongside `entity.traits.all()` (both are read/restored via the same trait-handler
  sweep; see task 5.15). Stages `apply_disguise_effect(target, overrides)` (change 5's exact D-7
  function) as a thunk; `overrides` comes from `event_context`.
- `buff_apply:<key>` → any `buffs.yaml` entry. `register_effect_handler("buff_apply", _handle_buff_apply,
  surfaces=frozenset({"buffs"}))`. Stages `target.buffs.add(key, **buff_kwargs)` per target, reusing
  change 6's `BuffHandler` mount directly.
- `confer_growth_rate` → the rate-of-change counterpart to 統御術.
  `register_effect_handler("confer_growth_rate", _handle_confer_growth_rate,
  surfaces=frozenset({"buffs"}))` (change 6's D-5 models this as a `RulebookBuff` instance, so it is a
  `buffs` surface, not `skill_grants`). Calls change 6's `grant_conferred_growth_rate(target, source_key,
  scale)` — the same registry mechanism generalizing to a second conferral shape with no new dispatch
  logic.
- `sexual_event:<name>` → **self-arming, per this change's own dependency boundary (Context).**
  `register_effect_handler("sexual_event", _handle_sexual_event,
  surfaces=frozenset({"sexual", "traits"}))`; the `traits` surface is required because the landed
  transition rulebook includes events that spend `sp`.
  Lazily imports `world.rules.sexual_transitions.apply_event`:

  ```python
  def _handle_sexual_event(actor, targets, effect_id, event_context) -> list[PendingEffect]:
      try:
          from world.rules.sexual_transitions import apply_event
      except ImportError:
          raise RejectedAction(
              RejectReason.EFFECT_RESOLUTION_FAILED,
              "sexual-transition rules not available yet (change 7b not landed)",
          )
      event_name = effect_id.split(":", 1)[1]
      target = _single_target(targets)
      return [PendingEffect(
          entity=target, description=f"apply_event({event_name}) on {target.key}",
          surfaces=frozenset(),   # overwritten by _step5_effect_resolution's stamping, see above
          apply=lambda: apply_event(target, event_name, **event_context.get("sexual", {})),
      )]
  ```

  A guarded test, `pytest.importorskip("world.rules.sexual_transitions")`-gated, asserts a sexual-magic
  skill resolves successfully end-to-end once 7b exists; a companion test (always runs) asserts the
  same skill rejects with `EFFECT_RESOLUTION_FAILED` — not a crash, not a silent no-op — while 7b does
  not exist, mirroring change 6's own self-arming discipline for `entity.sexual` exactly.

**Declared, not built**: `damage:*`. No handler is registered for this prefix. A skill like
`fire_ball` (change 5's own seed registry) whose `effects` include a `damage:fire:magic`-shaped ID
rejects today with `UNKNOWN_EFFECT_ID` naming that exact string — the correct, honest state until
change 9 calls `register_effect_handler("damage", ..., surfaces=...)`, declaring whatever it actually
touches (almost certainly `traits`, for hp/mp/sp changes — already snapshotted — but change 9's own
author decides and the registration call enforces it), at which point the identical skill resolves with
zero change to `action.py`. A test proves the registry itself is genuinely open: registering a
synthetic, test-only handler for a made-up prefix with `surfaces=frozenset({"traits"})` and confirming
a skill using that prefix resolves — proving the extension mechanism works without needing change 9's
real damage math to exist. A second test registers a handler declaring an unsupported surface (e.g.
`surfaces=frozenset({"inventory"})`) and asserts `register_effect_handler()` itself raises
`UnsnapshottedSurfaceError` immediately, before any skill ever tries to use it.

**Effect IDs that produce no `PendingEffect` at all**: `stat_multiply:*` (change 5's own multiplier
convention) is a pure *query*, not a mutating event — `SkillHandler.effective_value()` is read directly
by whichever combat math needs it (change 9), never staged or committed here. `element_mastery_rank:*`
is likewise a marker read by whatever future rulebook interprets it. Neither needs a step-5 handler in
this change.

### D-8. `EventLog`/`EventEntry`: frozen, serializable, entity-key-only data; `render_plain_text()` as
the reference no-LLM path; designed for all four named consumers.

```python
# world/rules/event_log.py
@dataclass(frozen=True)
class EventEntry:
    kind: str                 # open convention, not a closed enum — see below
    actor: str                # entity KEY, never a live reference
    target: str | None        # entity KEY or None
    data: dict                # kind-specific, plain-JSON-compatible payload
    text_template: str        # a hand-authored, str.format()-able template for offline rendering

@dataclass(frozen=True)
class EventLog:
    actor: str
    skill_key: str
    targets: tuple[str, ...]
    entries: tuple[EventEntry, ...]
    time_cost_seconds: int
```

**Why entity keys, never live references.** An `EventLog` must be JSON-serializable and outlive the
entities it describes for the "replayable" contract design doc §3.3 requires — replay here means
*re-rendering a captured record*, not re-simulating world mutation (undo/redo is out of scope; nothing
in this change or any dependency re-applies an `EventLog`'s effects a second time). A live entity
reference would break serialization and would silently go stale the moment that entity's state changed
after the fact — a serialized, self-contained record with keys only cannot go stale, because it never
claims to describe *current* state, only *what happened at commit time*.

**`kind` is an open string convention, not a closed enum — matching `SkillDef.effects`'s own
opaque-string discipline (change 5's precedent).** This change defines and uses exactly:
`"resource_spend"`, `"trait_delta"`, `"sexual_transition"`, `"buff_applied"`, `"skill_granted"`,
`"disguise_set"`. Change 9 is expected to add `"roll"`, `"damage"`, and change 10 an
`"overwhelm_resolution"` kind — each following the identical four-field shape, requiring zero change to
`EventLog`'s own dataclass. This is the concrete answer to "designed for all four consumers":

- **Change 9 (combat)**: emits one `EventLog` per resolved combatant action per round, via the same
  `ActionResolver.resolve()` call this change builds; nothing about `EventLog`'s shape needs to change
  for combat to use it.
- **Change 10 (overwhelm compression)**: "a full `EventLog` is still produced" (design doc §6.3) even
  under overwhelm — compression means concatenating/summarizing multiple `EventLog.entries` tuples
  (flat, ordered, and mergeable by simple concatenation) into fewer, coarser entries (e.g. one
  `"overwhelm_resolution"` entry standing in for what would otherwise be a dozen per-round `"roll"`
  entries) — a transformation over this change's own data shape, not a new one.
- **Change 18 (Narrator)**: a pure function `EventLog → prose` reads `entries` and has everything it
  needs (`kind`, `actor`/`target` keys to resolve into display names, `data` for numbers, and
  `text_template` as a fallback) without ever touching a live entity or a write API.
- **A hand-written template, no LLM present**:

  ```python
  def render_plain_text(event_log: EventLog) -> str:
      """Minimal reference degradation renderer — proves EventEntry's shape is
      sufficient without any LLM call, prompt construction, or retry logic.
      Change 18 may call this directly as its own degradation path (design doc
      S7.5's Narrator row: 'template-render the EventLog') or supersede it with
      richer, archetype-specific templates; either way this function's job is
      proving the seam works, not producing final production prose."""
      return "\n".join(
          entry.text_template.format(actor=entry.actor, target=entry.target, data=entry.data)
          for entry in event_log.entries
      )
  ```

  Worked example: a 統御術 cast stages `EventEntry(kind="skill_granted", actor="elosia",
  target="violet", data={"skill_key": "dominion_art", "scale": 0.1}, text_template="{actor} 對
  {target} 施展了「統御術」的部分效果。")` — `render_plain_text()` produces that exact Traditional
  Chinese sentence with zero model calls, zero prompt, zero network dependency. This is the literal,
  executable proof of design doc §7.5/§10's acceptance criterion ("the game must remain playable with
  the LLM entirely offline") at the one seam this change owns.

**Rejections produce no `EventLog`** (D-2) — there is no "failed action" `EventEntry` kind, since a
rejected action is, by D-1's atomicity guarantee, a pure no-op on the world.

### D-9. Time cost: step 8 *reports*, never advances; a flat default from §6.5 today, with a named,
tested failure mode and an override seam for later per-skill tuning.

```python
DEFAULT_CAST_SECONDS = 6                       # design doc S6.5's flat "cast" default
SKILL_TIME_OVERRIDES: dict[str, int] = {}       # empty seed — no per-skill override authored yet

def _step8_time_cost(request: ActionRequest, skill: SkillDef) -> int:
    seconds = SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)
    if not isinstance(seconds, int) or seconds < 0:
        raise RejectedAction(RejectReason.TIME_COST_LOOKUP_FAILED, f"{skill.key}: {seconds!r}")
    return seconds
```

This function **never calls anything resembling `WorldClock.advance()`** — change 11 does not exist
yet, and design doc §6.5's fixed settlement order (regen → buffs → sexual decay → daily resets → ...)
is explicitly change 11's invention, not this change's to assume or hardcode. `ActionResult.success()`
simply carries `time_cost_seconds` back to the caller; the caller (command layer or change 9's turn
loop) is expected to hand that number to `WorldClock.advance()` once change 11 exists — this change
guarantees only that the number exists and is correct for a "cast," never that anything happens with
it. `SKILL_TIME_OVERRIDES` ships empty (every skill uses the flat default) but exists as the seam a
later balance pass can populate without changing `_step8_time_cost()`'s signature or call sites — the
same "seed empty, seam real" discipline change 5's D-4 used for its own placeholder multiplier.

### D-10. Out-of-combat command: `CmdCast`, deliberately thin.

```python
# commands/action.py
class CmdCast(Command):
    key = "cast"
    # syntax: cast <skill_key>[=<target_key>]

    def func(self):
        skill_key, _, target_key = self.args.partition("=")
        targets = [self.caller.search(target_key.strip())] if target_key.strip() else []
        request = ActionRequest(
            actor=self.caller, skill_key=skill_key.strip(), targets=targets,
            context=RoomActionContext(
                room=self.caller.location,
                event_context={"disguise": dict(self.caller.db.disguised_stats or {})}
                if skill_key.strip() == "status_disguise" else {},
            ),
        )
        result = ActionResolver.resolve(request)
        if result.outcome == "success":
            self.caller.msg(render_plain_text(result.event_log))
        else:
            self.caller.msg(REJECTION_MESSAGES.get(result.reason, "That didn't work."))
```

The stored `disguised_stats` value is the deterministic preset for a context-free
`status_disguise` cast, ensuring the stock registry has a successful command path. This is the
entire out-of-combat integration surface this change builds — no target-string
disambiguation beyond Evennia's own `caller.search()`, no multi-target syntax. Its only job is proving
that an out-of-combat cast and a (declared, not built) combat cast are the same
`ActionResolver.resolve()` call with a different `ActionContext` — the concrete instance of D-3/D-4's
claim, not a parallel implementation of anything `action.py` already does.

## Risks / Trade-offs

- **[Risk, mitigated during review] The snapshot/restore commit mechanism (D-1) originally had a
  silent coverage boundary**: `_commit()` snapshots exactly `entity.traits`, `entity.sexual`,
  `entity.buffs`, and `entity.db.skill_grants`, but the effect-handler registry (D-7) is deliberately
  open — changes 9 (damage), 15 (quest-runtime, likely inventory/quest-state effects), and 21
  (scene-builder) will all register handlers into it. The first one that mutates a surface outside that
  set (inventory, room contents, a spawned object, a quest record) would silently escape rollback,
  defeating this change's entire reason for existing, and nothing in the original design would have
  caught it — the gap was latent, not live, since no such handler exists yet. → **Fixed, not merely
  flagged**: D-7 now requires every registered effect handler to declare, at registration time, the
  exact set of surfaces it mutates, and `register_effect_handler()` itself raises immediately if a
  declared surface is not one `_commit()` already knows how to snapshot — a handler needing a new
  surface fails loudly the moment it is registered (dev-time, before any player can hit it), forcing its
  author to either extend `_snapshot_entity_state()`/`_restore_entity_state()` or justify an exemption
  in review, never to add it silently. `_commit()` itself re-asserts the same constraint defensively
  against every staged `PendingEffect` immediately before touching any entity, as a second, independent
  layer in case a handler was ever registered by a path bypassing `register_effect_handler()`. A test
  registers a handler declaring an unsupported surface and asserts the action rejects rather than
  running partially observed.
- **[Risk] `transaction.atomic()`'s exact interaction with Evennia's `TraitHandler`/`BuffHandler`
  internals is unverified** — if either contrib caches state outside the connection's transaction
  boundary, the secondary DB-hardening layer would not actually roll back an in-flight write the way
  the explicit snapshot/restore layer already does independently. → Accepted and flagged for
  implementer verification, consistent with changes 1–7's identical discipline for every other
  Evennia-contrib assumption; the *primary* mechanism (explicit snapshot/restore) does not depend on
  this being true, which is exactly why it is the primary mechanism and not `transaction.atomic()` alone.
- **[Risk] `is_in_range()` always returning `True` (D-5) means "range" is not a real constraint in this
  change's shipped behavior** — any skill can hit any present target regardless of a distance concept
  this project has not yet built. → Accepted, named, and now assigned an explicit owner: change 9
  (`dice-combat`), once change 12 (`map-anchor-grid`) supplies the coordinates that make range
  computable — see D-5 and Open Questions. No roadmap item this change depends on introduces
  positional combat data, and inventing one here would be scope creep against a one-day change; the
  rejection path itself is tested via a stubbed context, so wiring in a real range model later requires
  no change to `targeting.py`'s call sites — only a new `BattlefieldActionContext.is_in_range()`
  implementation change 9 supplies.
- **[Risk] `EFFECT_HANDLERS`' seed set leaves every damage-shaped effect ID unresolved until change 9
  lands, meaning no skill exercising actual combat math can be cast through this change alone.** →
  Accepted and stated as a Non-Goal explicitly; `UNKNOWN_EFFECT_ID` is the correct, honest, and tested
  response, not a placeholder that silently no-ops or fabricates a number.
- **[Risk] The `sexual_event:*` handler's lazy import (D-7) means a malformed or renamed function in a
  future `sexual_transitions.py` would surface as a generic `EFFECT_RESOLUTION_FAILED` with an
  `ImportError`'s message, not a more specific reason.** → Accepted; this mirrors change 6's own
  degrade-on-`None` treatment of `entity.sexual` exactly, and a self-arming integration test (D-7)
  proves the successful path once change 7b lands, independent of this generic failure text.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/action.py`/`targeting.py`/`event_log.py`, plus `commands/action.py`, do not exist yet. The
only sequencing concerns are operational:

- This change must land after change 5 (`SkillDef`/`SkillHandler`, `record_conferred_grant()`,
  `apply_disguise_effect()`) and change 6 (`blocks_action()`, `entity_active_buffs()`,
  `grant_conferred_growth_rate()`), matching design doc §11 exactly.
- This change does **not** need change 7/7b to land first — the `sexual_event:*` handler self-arms
  (D-7); a guarded integration test confirms it reports skipped, not passed, until 7b exists, the same
  verification discipline change 6's own task list applied to its own self-arming test.
- Change 9 (`dice-combat`) is expected to: implement `BattlefieldActionContext` conforming to this
  change's `ActionContext` protocol (D-4); call `ActionResolver.resolve()` from its turn loop; register
  `damage:*` effect handlers via `register_effect_handler()`, declaring whatever mutation surfaces they
  touch (D-7) — extending `SNAPSHOTTED_SURFACES`/`_snapshot_entity_state()` first if damage touches
  anything beyond `entity.traits`; and replace `RoomActionContext`'s always-`True` `is_in_range()` with
  a real, coordinate-based implementation once change 12 (`map-anchor-grid`) exists (D-5). None of
  these calls, registrations, or implementations exist yet — this change only guarantees the protocol,
  the registry function, and the surface-declaration gate exist with the documented shape.
- Change 10 (`overwhelm-resolution`) is expected to compress multiple `EventLog`s this change produces;
  change 11 (`world-clock`) is expected to read `ActionResult.success().time_cost_seconds` and decide
  how to advance; change 18 (`narrator`) is expected to consume `EventLog` and may reuse
  `render_plain_text()` directly.

## Open Questions

- **Resolved during coordinator review: `FactionConstraint` lives on `SkillDef` (change 5), not
  `ActionRequest`.** No longer open — see D-5's full account of the correction. Change 5 declares and
  populates `faction_constraint`; this change validates it.
- **Resolved during coordinator review: `is_in_range()`'s real implementation is change 9's job.** No
  longer unowned — see D-5 and the Migration Plan. Change 9 (`dice-combat`) inherits this seam
  explicitly rather than rediscovering an unconditional `True` and wondering whether it was deliberate;
  change 12 (`map-anchor-grid`) is the dependency that makes a real implementation possible at all.
- **Should `SNAPSHOTTED_SURFACES` eventually grow beyond `traits`/`sexual`/`buffs`/`skill_grants`
  proactively, ahead of any handler actually needing a new surface?** Not done here — D-7's
  registration-time assertion means a future handler needing (say) `inventory` fails loudly and
  visibly the moment it is registered, which this change treats as the correct forcing function rather
  than speculatively snapshotting surfaces nothing yet touches. Left to whichever change (9, 15, or 21)
  first needs one.
- **Exact `django.db.transaction` import path and whether Evennia 6.1.0's `TraitHandler`/`BuffHandler`
  bypass the ORM's transaction boundary via an in-memory cache** — left to the implementer to confirm
  against the installed package, consistent with the verification discipline changes 1–7 already
  established; the primary atomicity mechanism (D-1's explicit snapshot/restore) does not depend on the
  answer.
