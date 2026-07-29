## 1. Package layout and shared types

- [ ] 1.1 Confirm `world/rules/` exists with changes 3/6's `traits.py`/`rulebook/`/`buffs.py`/
      `combat_modifiers.py`; create `world/rules/tests/__init__.py` if missing (it should already exist
      from change 6). Create empty `world/rules/action.py`, `world/rules/targeting.py`,
      `world/rules/event_log.py` with module docstrings referencing design doc §6.1/§6.2/§3.3 and this
      change.
- [ ] 1.2 Confirm `commands/` exists as an empty package (change 1); create `commands/action.py` as an
      empty module.
- [ ] 1.3 Confirm the exact import paths for `world.skills.registry.{SkillDef, SkillKind, TargetSpec,
      FactionConstraint, SKILL_REGISTRY}` (change 5 — `FactionConstraint` and `SkillDef.
      faction_constraint` were added to change 5's design during this change's own review; confirm they
      landed as documented), `world.skills.handler.{grant_conferred, apply_disguise_effect}` (change 5,
      exact function names/module location — confirm against how change 5 actually landed), and
      `world.rules.buffs.{blocks_action, entity_active_buffs, BLOCKING_BUFF_KEYS,
      grant_conferred_growth_rate}` (change 6) — no code in this change should assume an unconfirmed
      symbol name before this step.
- [ ] 1.4 Confirm the `django.db.transaction` import path against the installed Django version Evennia
      6.1.0 pins, per design.md D-1's secondary hardening layer.

## 2. Named rejection reasons and the ActionRequest/ActionResult shape

- [ ] 2.1 In `world/rules/action.py`, define `RejectReason(StrEnum)` with every value listed in
      design.md D-2 (one per pipeline step, plus the four target sub-reasons,
      `UNSNAPSHOTTED_EFFECT_SURFACE`, and `COMMIT_FAILED`).
- [ ] 2.2 Define `RejectedAction(Exception)` and `CommitFailed(Exception)`, both carrying
      `reason: RejectReason` and `detail: str`, per design.md D-2.
- [ ] 2.3 Define `ActionRequest` (frozen dataclass): `actor`, `skill_key: str`,
      `targets: list[LivingEntity] | Literal["all-enemies", "all-allies", "all"]`,
      `context: ActionContext`. **No `faction` field** — `FactionConstraint` is read from the resolved
      `SkillDef` (change 5), never supplied by the caller; see design.md D-5's corrected account.
- [ ] 2.4 Define `ActionResult` (frozen dataclass) with `outcome: Literal["success", "rejected"]`,
      `event_log: EventLog | None`, `time_cost_seconds: int | None`, `reason: RejectReason | None`,
      `detail: str | None`, plus `ActionResult.success(event_log, time_cost)` and
      `ActionResult.rejected(reason, detail)` constructors enforcing the field-presence invariant (task
      3.10's test checks this).

## 3. Targeting (`world/rules/targeting.py`)

- [ ] 3.1 Import `FactionConstraint` from `world.skills.registry` (change 5 — do **not** redefine a
      competing enum in this module). Define `Relation(StrEnum)`: `SELF`/`ALLY`/`ENEMY` — this change's
      own type, distinct from `FactionConstraint` — per design.md D-5.
- [ ] 3.2 Define `ActionContext` as a `Protocol` (or ABC) with `battlefield: Battlefield | None`,
      `is_present(actor, target) -> bool`, `relation_to(actor, target) -> Relation`,
      `is_in_range(actor, target, skill) -> bool`, per design.md D-4.
- [ ] 3.3 Implement `RoomActionContext` (out-of-combat, built now): `is_present()` checks room
      co-location; `relation_to()` returns `Relation.SELF` for the actor and `Relation.ALLY` for every
      other present entity, never `Relation.ENEMY`; `is_in_range()` returns `True` unconditionally
      (owned going forward by change 9 once change 12 supplies positional data — see design.md D-5's
      Open Questions); `battlefield` is always `None`.
- [ ] 3.4 Implement `validate_faction(relation: Relation, constraint: FactionConstraint) -> bool` per
      design.md D-5's exact truth table (`ANY` always true; `SELF_ONLY` requires `SELF`; `ALLY` accepts
      `SELF` or `ALLY`; `ENEMY` requires `ENEMY`).
- [ ] 3.5 Implement the four ordered per-candidate validation functions (`_validate_presence`,
      `_validate_alive`, `_validate_range`, `_validate_faction`), each raising the matching
      `RejectReason` from task 2.1. `_validate_faction` reads its constraint from `skill.
      faction_constraint`, never from the request.
- [ ] 3.6 Implement `resolve_targets(request, skill, candidates) -> list[LivingEntity]`: for
      `TargetSpec.SINGLE`/`SELF`, any candidate failing any validation rejects the whole action with
      that validation's reason; for `TargetSpec.AREA`, each candidate is validated independently,
      failures are dropped silently, and an empty result after filtering raises
      `RejectReason.NO_VALID_TARGETS_IN_AREA`; for `TargetSpec.NONE`, returns `[]` with no validation
      run at all. Faction validation reads `skill.faction_constraint` (change 5's field) — `resolve_
      targets()` takes no separate faction argument from `request`.
- [ ] 3.7 Implement `expand_target_shorthand(actor, context, shorthand: str) -> list[LivingEntity]` for
      `"all-enemies"`/`"all-allies"`/`"all"`, reading `context.battlefield`'s roster (declared shape
      only, per change 9's future `BattlefieldActionContext`); raises
      `RejectReason.TARGET_SPEC_MISMATCH` if `context.battlefield is None`. Confirm the expanded
      candidate list is handed to the exact same `resolve_targets()` from task 3.6 — no parallel
      validation path.
- [ ] 3.8 Declare (docstring/type-only, no implementation) `BattlefieldActionContext`'s expected shape
      as the protocol-conformance target for change 9 — do not implement combat roster/team logic. Note
      in the docstring that change 9 also owns replacing `is_in_range()`'s always-`True` behavior with a
      real, coordinate-based check once change 12 (`map-anchor-grid`) exists.

## 4. EventLog (`world/rules/event_log.py`)

- [ ] 4.1 Define `EventEntry` (frozen dataclass): `kind: str`, `actor: str`, `target: str | None`,
      `data: dict`, `text_template: str`, per design.md D-8.
- [ ] 4.2 Define `EventLog` (frozen dataclass): `actor: str`, `skill_key: str`,
      `targets: tuple[str, ...]`, `entries: tuple[EventEntry, ...]`, `time_cost_seconds: int`.
- [ ] 4.3 Implement `render_plain_text(event_log: EventLog) -> str` per design.md D-8: joins every
      entry's `text_template.format(actor=..., target=..., data=...)` with newlines. No import of any
      `world/ai/` module anywhere in this function or this module.
- [ ] 4.4 Confirm `EventEntry`/`EventLog` round-trip through `dataclasses.asdict()` → `json.dumps()` →
      `json.loads()` with no loss and no live entity reference anywhere in the structure.

## 5. ActionResolver pipeline (`world/rules/action.py`)

- [ ] 5.1 Implement `_step1_ownership(request) -> SkillDef` per design.md D-3: looks up
      `SKILL_REGISTRY[request.skill_key]`, checks the actor's `skills.owned_keys()`, checks
      `skill.kind is SkillKind.ACTIVE`, and performs the ONE sanctioned combat-context read
      (`not skill.usable_out_of_combat and request.context.battlefield is None`) with an explicit
      marker comment matching design.md D-3/D-6's allow-listed line exactly.
- [ ] 5.2 Implement `_step2_resource_check(actor, skill) -> None`: for every `(resource_key, amount)`
      in `skill.cost`, raises `RejectReason.INSUFFICIENT_RESOURCE` if
      `getattr(actor.traits, resource_key).value < amount`.
- [ ] 5.3 Implement `_step3_targeting(request, skill) -> list[LivingEntity]`: expands shorthand (task
      3.7) if `request.targets` is a shorthand string, then calls `resolve_targets(request, skill,
      candidates)` (task 3.6) — `skill.faction_constraint` is read inside targeting, not passed by this
      caller as a separate value.
- [ ] 5.4 Implement `_step4_capability(actor) -> None`: raises `RejectReason.ACTION_FORBIDDEN` if
      `blocks_action(actor)` (change 6's exact seam) is `True`.
- [ ] 5.5 Implement `SNAPSHOTTED_SURFACES = frozenset({"traits", "sexual", "buffs", "skill_grants"})`,
      `UnsnapshottedSurfaceError`, the `_EFFECT_HANDLERS`/`_EFFECT_HANDLER_SURFACES` registries, and
      `register_effect_handler(prefix, handler, surfaces)` per design.md D-1/D-7:
      `register_effect_handler()` raises `UnsnapshottedSurfaceError` immediately if `surfaces` is not a
      subset of `SNAPSHOTTED_SURFACES`. Implement `_step5_effect_resolution(request, skill, targets) ->
      list[PendingEffect]` dispatching purely by effect-ID prefix, raising `RejectReason.
      UNKNOWN_EFFECT_ID` for an unregistered prefix, wrapping any other handler exception as
      `RejectReason.EFFECT_RESOLUTION_FAILED`, and stamping every returned `PendingEffect`'s `surfaces`
      field from `_EFFECT_HANDLER_SURFACES[prefix]` via `dataclasses.replace()` — a handler never sets
      its own `surfaces` value.
- [ ] 5.6 Implement the `confer_skill_partial` handler, registered with
      `surfaces=frozenset({"skill_grants"})`: stages `target.skills.grant_conferred(source_key,
      skill_key, trait_keys, scale)` (change 5's exact seam) as a `PendingEffect`, reading
      `confer_skill_key`/`confer_scale`/`confer_trait_keys` from `request.context.event_context`; raises
      `EFFECT_RESOLUTION_FAILED` naming any missing key.
- [ ] 5.7 Implement the `set_disguise` handler, registered with `surfaces=frozenset({"traits"})`: stages
      `apply_disguise_effect(target, overrides)` (change 5's exact D-7 function) as a `PendingEffect`.
- [ ] 5.8 Implement the `buff_apply:<key>` handler, registered with `surfaces=frozenset({"buffs"})`:
      stages `target.buffs.add(key, **buff_kwargs)` per target (change 6's `BuffHandler` mount, one
      `PendingEffect` per target for `AREA`).
- [ ] 5.9 Implement the `confer_growth_rate` handler, registered with `surfaces=frozenset({"buffs"})`
      (change 6's D-5 models this as a `RulebookBuff` instance): stages
      `grant_conferred_growth_rate(target, source_key, scale)` (change 6's exact seam).
- [ ] 5.10 Implement the self-arming `sexual_event:<name>` handler, registered with
      `surfaces=frozenset({"sexual"})`, per design.md D-7: lazily imports
      `world.rules.sexual_transitions.apply_event` inside a `try/except ImportError`, raising
      `RejectReason.EFFECT_RESOLUTION_FAILED` with a message naming change 7b when the module is not
      yet importable; stages `apply_event(target, event_name, **event_context.get("sexual", {}))` as a
      `PendingEffect` when it is.
- [ ] 5.10a Add a test-only synthetic handler registration exercising an unsupported surface (e.g.
      `surfaces=frozenset({"inventory"})`) and confirm `register_effect_handler()` raises
      `UnsnapshottedSurfaceError` immediately, before any skill references that prefix — per hard
      requirement 1's "no undeclared handler defeats atomicity" fix.
- [ ] 5.11 Implement `_step6_resource_deduction(actor, skill) -> list[PendingEffect]`: for every
      `(resource_key, amount)` in `skill.cost`, re-checks the current value defensively and raises
      `RejectReason.RESOURCE_DEDUCTION_FAILED` if it no longer covers `amount` (unreachable in today's
      single-threaded staging discipline but wired and tested per hard requirement 1), then stages a
      `PendingEffect` (constructed directly by this module, `surfaces=frozenset({"traits"})`, not via
      the registry) decrementing `entity.traits.<key>.value` by `amount`.
- [ ] 5.12 Implement `_step7_build_event_log(request, skill, pending) -> EventLog` per design.md D-8:
      builds one `EventEntry` per `PendingEffect` (using each effect's `description` and a
      kind/text_template pair appropriate to the effect it represents — `resource_spend` for step 6's
      deduction effects, `skill_granted`/`disguise_set`/`buff_applied`/`sexual_transition` for step 5's
      handlers), from staged data only, before any `PendingEffect.apply()` runs. Raises
      `RejectReason.EVENT_LOG_CONSTRUCTION_FAILED` on malformed entry data (fault-injectable for
      testing).
- [ ] 5.13 Implement `_step8_time_cost(request, skill) -> int` per design.md D-9:
      `SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)`, validated as a non-negative int,
      raising `RejectReason.TIME_COST_LOOKUP_FAILED` otherwise. Confirm this function calls nothing
      resembling `WorldClock.advance()` anywhere.
- [ ] 5.14 Implement `PendingEffect` (frozen dataclass: `entity`, `description: str`,
      `surfaces: frozenset[str]`, `apply: Callable[[], None]`) per design.md D-1. Effect-handler
      authors construct instances with a placeholder `surfaces` value (e.g. `frozenset()`) — task 5.5's
      `_step5_effect_resolution` overwrites it from the registry before it is ever staged into the
      pending list returned to `resolve()`.
- [ ] 5.15 Implement `_snapshot_entity_state(entity) -> dict` and `_restore_entity_state(entity,
      snapshot) -> None` per design.md D-1: snapshot captures `entity.traits.all()` values (including
      `entity.db.disguised_stats`, treated as part of the `traits` surface — see design.md D-7's
      `set_disguise` entry), `entity.sexual`'s public field values when not `None`, `entity.buffs`'s
      active-key set, and `entity.db.skill_grants`; restore writes traits/sexual fields back via their
      own public setters and reconciles the buff set via `.add()`/`.remove()` set-difference.
- [ ] 5.16 Implement `_commit(pending: list[PendingEffect]) -> None` per design.md D-1: **first**,
      iterates every `PendingEffect` and raises `CommitFailed(RejectReason.
      UNSNAPSHOTTED_EFFECT_SURFACE, ...)` if any declares a surface outside `SNAPSHOTTED_SURFACES`,
      before touching any entity (defense in depth alongside task 5.5's registration-time check); only
      then snapshots every touched entity, applies every `PendingEffect.apply()` inside one
      `django.db.transaction.atomic()` block, and on any exception restores every touched entity from
      its snapshot before re-raising `CommitFailed(RejectReason.COMMIT_FAILED, ...)`.
- [ ] 5.17 Implement `ActionResolver.resolve(request: ActionRequest) -> ActionResult` per design.md
      D-1: runs steps 1–8 inside one `try/except RejectedAction` block returning
      `ActionResult.rejected(rejection.reason, rejection.detail)`, then calls `_commit(pending)` inside
      a second `try/except CommitFailed` returning `ActionResult.rejected(failure.reason,
      failure.detail)`, otherwise returns `ActionResult.success(event_log, time_cost)`.

## 6. Out-of-combat command (`commands/action.py`)

- [ ] 6.1 Implement `CmdCast` per design.md D-10: parses `cast <skill_key>[=<target_key>]`, resolves
      the target via `self.caller.search()`, constructs an `ActionRequest` with a `RoomActionContext`,
      calls `ActionResolver.resolve()`, and renders success via `render_plain_text()` or rejection via
      a `REJECTION_MESSAGES: dict[RejectReason, str]` lookup.
- [ ] 6.2 Confirm `REJECTION_MESSAGES` covers every `RejectReason` value defined in task 2.1, with a
      generic fallback for any value it does not explicitly name.

## 7. Tests

- [ ] 7.1 `world/rules/tests/test_action_pipeline_rejections.py` — one test per named rejection
      covering every `RejectReason` from task 2.1: fault-inject a scenario for each of the eight
      pipeline steps (unknown skill, passive skill, out-of-combat-forbidden skill, insufficient
      resource, each of the four target-validation failures plus the AREA-empty case, action-forbidden
      buff, unknown effect ID, effect-handler exception, resource-deduction defensive failure,
      malformed EventLog entry, malformed time-cost override) and assert the exact `RejectReason` and
      that no entity's `traits`/`sexual`/`buffs`/`db.skill_grants` changed.
- [ ] 7.2 `world/rules/tests/test_action_pipeline_atomicity.py` — the centerpiece: stage three
      `PendingEffect`s with the second one's `apply()` raising a test-injected exception; assert
      `resolve()` returns `RejectReason.COMMIT_FAILED` and the first effect's mutation is fully
      reversed; a companion test stages a skill's own effect plus its resource-deduction effect and
      asserts a failure in the effect's `apply()` leaves the actor's `mp`/`sp` completely undeducted;
      a third test injects a bad entry directly into `_EFFECT_HANDLER_SURFACES` (bypassing
      `register_effect_handler()`'s own check) and asserts `_commit()`'s independent defensive
      assertion still rejects with `RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE` before touching any
      entity.
- [ ] 7.3 `world/rules/tests/test_targeting.py` — per the `targeting-validation` capability: each of the
      four validations in isolation; `SINGLE` hard-rejects on one invalid target; `AREA` silently drops
      one invalid candidate among several valid ones; `AREA` rejects with `NO_VALID_TARGETS_IN_AREA`
      when every candidate is filtered; `FactionConstraint` truth table (`ANY`/`ALLY`/`ENEMY`/
      `SELF_ONLY`, change 5's enum) against each `Relation` value; confirm two different callers casting
      the identical `skill_key` cannot produce two different faction outcomes (the constraint lives on
      `SkillDef`, not the request); `RoomActionContext.relation_to()` never returns `Relation.ENEMY`;
      shorthand expansion feeds the identical validation path and rejects with `TARGET_SPEC_MISMATCH`
      out of combat.
- [ ] 7.4 `world/rules/tests/test_event_log.py` — per the `event-log` capability: `EventEntry`/
      `EventLog` JSON round-trip with no live reference; `render_plain_text()`'s worked 統御術 example
      renders the exact expected string with no `world/ai/` import; multi-entry ordering; a rejected
      `resolve()` call produces `event_log is None`; concatenating two `EventLog.entries` tuples
      produces a validly renderable combined sequence.
- [ ] 7.5 `world/rules/tests/test_effect_handlers.py` — per the `action-resolution-pipeline`
      capability's registry requirement: a synthetic test-only prefix registered (with a supported
      `surfaces` value) and resolved end-to-end; a synthetic registration with an unsupported `surfaces`
      value asserted to raise `UnsnapshottedSurfaceError` immediately; 統御術's conferral committing
      atomically with its resource cost (`entity.db.skill_grants` gains exactly one matching
      `ConferredSkillGrant`); 狀態偽裝's `set_disguise` handler touching only `entity.db.disguised_stats`;
      `buff_apply:` applying to every `AREA` target; `confer_growth_rate` calling change 6's exact seam.
- [ ] 7.6 `world/rules/tests/test_sexual_event_self_arming.py` — always-runs test asserting a
      `sexual_event:`-effect skill rejects with `EFFECT_RESOLUTION_FAILED` (not a crash) while
      `world.rules.sexual_transitions` is not importable; a `pytest.importorskip`-gated companion test
      asserting the same skill resolves successfully and mutates `entity.sexual` once change 7b lands —
      expected to report **skipped**, not passed, until then. A verification task (7.9) confirms this.
- [ ] 7.7 `world/rules/tests/test_no_combat_branching.py` — per design.md D-6: the forbidden-token
      source scan across `action.py`/`targeting.py`/`event_log.py`; the `inspect.signature()` scan for
      combat-shaped parameter names; the positive polymorphism proof (identical `ActionRequest`, same
      skill whose `faction_constraint` is `FactionConstraint.ENEMY`, two different `ActionContext`
      implementations, different outcomes).
- [ ] 7.8 `world/rules/tests/test_cmd_cast.py` — `CmdCast` end-to-end: a successful cast renders via
      `render_plain_text()`; a rejected cast renders the matching `REJECTION_MESSAGES` entry.

## 8. Verification

- [ ] 8.1 Run the full `world/rules/tests/` suite added by this change and confirm every test passes,
      except `test_sexual_event_self_arming.py`'s guarded integration test, which is expected to report
      **skipped** at this point in the roadmap (before changes 7/7b land).
- [ ] 8.2 Confirm no function in `world/rules/action.py`, `world/rules/targeting.py`, or
      `world/rules/event_log.py` mutates any entity's `traits`/`sexual`/`buffs`/`db.*` state outside of
      `PendingEffect.apply()` calls made from within `_commit()` (grep-based check, mirroring change
      3's task 7.5 and change 5's task 8.2 discipline).
- [ ] 8.3 Confirm `ActionResolver.resolve()` is the only function in `world/rules/` or `world/skills/`
      that constructs an `EventLog` (grep-based check).
- [ ] 8.4 Confirm this change modifies no file authored by any earlier change **other than change 5's
      own design.md**, which the coordinator has already amended directly to add `FactionConstraint`/
      `SkillDef.faction_constraint` — `git diff --stat` against the pre-change tree shows only new files
      under `world/rules/`, `commands/`, and their `tests/` subdirectories, plus that one pre-existing
      edit to change 5's design.
- [ ] 8.5 Confirm every effect handler registered by this change (task 5.6–5.10) declares a `surfaces`
      value that is a genuine subset of `SNAPSHOTTED_SURFACES`, and that `register_effect_handler()`
      itself is the only place in `action.py` that writes to `_EFFECT_HANDLERS`/
      `_EFFECT_HANDLER_SURFACES` (grep-based check).
- [ ] 8.6 Run `openspec validate action-resolver --strict` and confirm it passes.
