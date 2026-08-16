## 1. Confirm the dependency surface this change reads and extends

- [x] 1.1 Re-read `world/rules/combat_session.py::_scan_sexual_coercion` in full and confirm it still
  has its documented shape (forced-outcome filter using `is False` on both `resisted` and
  `auto_comply`, `battlefield.roster.get(entry.target)` resolution, `isinstance(target, NPC)` guard,
  nested `transaction.atomic()` around `apply_affinity_change`, and the
  `party_before`/`members_before`/`relations_before` snapshot triple with
  `restore_membership_surfaces`/`restore_relations_surfaces` in its except block). This is the
  pattern design.md Decision 1 mirrors line-for-line for the out-of-combat scan.
- [x] 1.2 Re-read `world/rules/cast_settlement.py::settle_out_of_combat_cast` in full and confirm the
  outer `transaction.atomic()` still wraps `ActionResolver.resolve` and the clock advance exactly as
  design.md Decision 2 describes, including the early `return CastSettlement(result, ())` on
  rejection. If this shape has moved, re-derive the wiring point before writing section 3.
- [x] 1.3 Confirm `world/rules/affinity.py::AffinitySource.SEXUAL_FORCED`,
  `apply_affinity_change`, `restore_relations_surfaces` and
  `world/rules/affinity_config.py::get_config().sexual_forced_penalty` are unchanged from what
  `sexual-resist-turn-cost` shipped — this proposal reuses every one of them without modification.
- [x] 1.4 Confirm `world/rules/party.py::restore_membership_surfaces`, `is_companion`, `leave_party`,
  and `AUTO_LEAVE_MESSAGE` still have their documented shapes (reached only transitively, through
  `apply_affinity_change`'s own `run_auto_leave_recheck` call — this proposal does not call any of
  them directly except `restore_membership_surfaces` in its own except block).
- [x] 1.5 Confirm `world/rules/event_log.py::EventEntry`/`EventLog` still have fields `kind`, `actor`,
  `target`, `data`, `text_template` / `actor`, `entries` — the contract this proposal's scan consumes.
- [x] 1.6 Confirm `world/rules/action.py::_step4b_sexual_resist_gate` still emits
  `EventEntry(kind="sexual_resist", data={"resisted": bool, "auto_comply": bool, "roll": int | None})`
  for every non-actor target of a `resistible=True` act, unconditionally of combat/out-of-combat
  caller — the contract this proposal's scan reacts to. Do not change this function.

## 2. `world/rules/cast_settlement.py`: the out-of-combat coercion scan

- [x] 2.1 Implement `_scan_out_of_combat_sexual_coercion(actor, targets, event_log) ->
  tuple[tuple[str, ...], _CoercionRestoreState | None]` per design.md Decision 1's shape (amended:
  the snapshot is returned as a frozen `_CoercionRestoreState` with a `restore(actor)` method so the
  settlement can also restore it when a later step fails — see task 3.5):
  - Return `((), None)` immediately if `event_log.actor != str(actor.key)`.
  - Build `by_key = {str(target.key): target for target in targets}`.
  - Collect every `EventEntry` in `event_log.entries` where `entry.kind == "sexual_resist"`,
    `isinstance(entry.data, dict)`, `entry.data.get("resisted") is False`, and
    `entry.data.get("auto_comply") is False` — use `is False`, not falsy-truthiness.
  - For each qualifying entry, resolve `target = by_key.get(entry.target)`; skip (no penalty, no
    write) if `target is None` or not `isinstance(target, NPC)`.
  - For each qualifying, resolved target, call `apply_affinity_change(target, actor,
    AffinitySource.SEXUAL_FORCED, -get_config().sexual_forced_penalty)` inside one
    `transaction.atomic()`, collecting `outcome.auto_leave_notification` when not `None`.
  - Before that block, build the `_CoercionRestoreState` from
    `party_before = list(actor.db.party or ())`,
    `members_before = {int(t.pk): t.db.party_member for t in forced}`,
    `relations_before = {int(t.pk): t.db.relations_data for t in forced}` for the forced-target list
    only (never the full `targets` list); on any exception, call
    `restore_state.restore(actor)` (which runs `restore_membership_surfaces` then
    `restore_relations_surfaces`) before re-raising.
  - Return `(tuple(notifications), restore_state)`; return `((), None)` early if the forced-target
    list is empty (no snapshot, no transaction opened).
- [x] 2.2 Add the necessary imports to `cast_settlement.py`: `typeclasses.npcs.NPC`,
  `world.rules.affinity.AffinitySource`, `world.rules.affinity.apply_affinity_change`,
  `world.rules.affinity_config.get_config` (module-level or function-lazy — match whichever import
  style `cast_settlement.py`'s existing imports already use for its other `world.rules.*` deps).

## 3. Wiring into `settle_out_of_combat_cast` and `CastSettlement`

- [x] 3.1 Add `notifications: tuple[str, ...] = ()` as a third field on the `CastSettlement`
  dataclass, after `events`, with a default so existing construction sites keep compiling.
- [x] 3.2 In `settle_out_of_combat_cast`, immediately after the `if result.outcome != "success":`
  rejection branch, update that branch's return to `CastSettlement(result, (), ())`.
- [x] 3.2b Add the duplicate-entity-key rejection (rubber-duck finding): when the cast skill is a
  resistible sexual act (`SEXUAL_ACT_REGISTRY.get(request.skill_key)` with `resistible=True`), reject
  with `ValueError` a target list whose `str(entity.key)` values repeat — the `sexual_resist` entry
  contract is key-keyed and cannot distinguish two same-key entities, so fail closed before any
  snapshot or clock access. Non-resistible acts must not be affected (they never emit
  `sexual_resist` entries).
- [x] 3.3 Immediately after the rejection check (before the clock-advance block), call
  `notifications, coercion_restore = _scan_out_of_combat_sexual_coercion(request.actor,
  request.targets, result.event_log)`.
- [x] 3.4 Update the function's final `return CastSettlement(result, events)` to
  `return CastSettlement(result, events, notifications)`.
- [x] 3.5 Restore wiring for post-scan failures (design.md Decision 1 amendment): initialize
  `coercion_restore: _CoercionRestoreState | None = None` before the outer `try`, and in the existing
  `except Exception:` block run `coercion_restore.restore(request.actor)` after
  `_restore_settlement_state(snapshot, clock)` and before `raise`. Confirm the scan's own exception
  path (task 2.1's restore-then-raise) still propagates correctly: for an in-scan failure the scan's
  own restore runs first (innermost), `coercion_restore` stays `None` (the assignment never
  completed), then the outer settlement restore runs on top, and the original exception (not a masked
  one) reaches the caller.

## 4. `commands/action.py`: deliver the notification

- [x] 4.1 In `CmdCast._cast_out_of_combat`, after `self.caller.msg(render_plain_text(settlement.
  result.event_log))` on the success branch, send each line in `settlement.notifications` to
  `self.caller` (one `self.caller.msg(line)` per notification, matching how `_cast_in_session`
  delivers `lines` from `settle_to_messages`).

## 5. Tests

- [x] 5.1 Add a new test module or extend `world/rules/tests/test_cast_settlement.py` — inspect that
  file's existing class organization (`OutOfCombatCastSettlementTests`,
  `CastSettlementRestoreTests`, etc.) first and place the new tests in whichever class or new class
  best matches its structure.
- [x] 5.2 One test per spec scenario in `specs/sexual-resist-out-of-combat/spec.md` — enumerate them
  explicitly and apply `covers_requirement` per `AGENTS.md`'s OpenSpec test-traceability section once
  requirement IDs are resolvable via `uv run --locked python -m tools.spec_traceability list` after
  the change validates; do not guess an ID before then.
- [x] 5.3 A forced-outcome test: cast a resistible act out of combat on a present `NPC`, force the
  resist roll to fail (`resisted=False, auto_comply=False`), and assert the target's affinity toward
  the actor decreased by exactly `sexual_forced_penalty` after the settlement commits.
- [x] 5.4 A compliance test and a successful-resistance test, each asserting no affinity change.
- [x] 5.5 A multi-target `AREA` test mirroring `sexual-resist-cast-wiring`'s own
  `test_area_act_rolls_one_independent_contest_per_target` shape: two `NPC` targets, one forced and
  one resisting or complying, asserting exactly one penalty applies to the forced target only.
- [x] 5.6 A non-NPC-target test: a `kind="sexual_resist"` entry whose target resolves to a
  `PlayerCharacter` applies no penalty and does not raise.
- [x] 5.7 A rollback test: force an exception after the scan applies at least one penalty but before
  the outer `settle_out_of_combat_cast` transaction commits (for example by making the clock-advance
  step raise), and assert the target NPC's `relations_data` is unchanged both via a fresh database
  read and via the in-process idmapper-cached object — mirror however
  `test_combat_session_sexual_coercion`'s (or wherever `_scan_sexual_coercion`'s own tests live)
  rollback test verifies both surfaces.
- [x] 5.8 An auto-leave test: a companion `NPC` forced past the invite threshold out of combat ends
  the party, and the player's message stream includes the auto-leave notification line alongside the
  rendered `EventLog`.
- [x] 5.9 A no-auto-leave test: a forced act on a non-companion (or a companion whose affinity stays
  above threshold) sends only the rendered `EventLog`, with no extra notification line.
- [x] 5.10 A malformed-payload test: a `kind="sexual_resist"` entry with a non-mapping `data` applies
  no penalty and does not raise.
- [x] 5.11 A rejected-cast test: an out-of-combat cast that `ActionResolver.resolve` rejects never
  calls `_scan_out_of_combat_sexual_coercion` and applies no affinity change (patch or spy the scan
  function to assert it is not called).
- [x] 5.12 An absent-target-key test: a `kind="sexual_resist"` entry whose `target` key matches none of
  the entities in the `targets` list passed to the scan applies no penalty and does not raise — distinct
  from 5.6's "wrong type" branch, this exercises the `target is None` branch of `by_key.get(...)`.
- [x] 5.13 A magnitude/source parity test: assert the out-of-combat penalty call site uses the exact
  same `get_config().sexual_forced_penalty` value and `AffinitySource.SEXUAL_FORCED` source the
  in-combat `_scan_sexual_coercion` uses — no separate out-of-combat constant or source.
- [x] 5.14 A foreign-actor `EventLog` test: a synthetically-constructed `EventLog` whose `actor` does
  not match the scanning actor's own key applies no penalty for any entry it carries (defensive/
  structural-parity coverage with `_scan_sexual_coercion`'s own equivalent test — not reachable through
  the current `settle_out_of_combat_cast` call site, since `result.event_log.actor` is always
  `request.actor`'s own key; see design.md's Risks section).
- [x] 5.15 A non-`sexual_resist`-kind entry test: an `EventLog` whose entries include other kinds (for
  example `"skill_practice"`) alongside or instead of any `"sexual_resist"` entry applies no penalty
  attributable to those entries.
- [x] 5.16 A non-`dict` mapping payload test (rubber-duck finding): a `kind="sexual_resist"` entry whose
  `data` is a read-only `MappingProxyType` carrying a forced outcome is accepted (the contract says
  "mapping", not strictly `dict`) and penalizes.
- [x] 5.17 A duplicate-target-key rejection test (rubber-duck finding): an explicit target list
  containing two distinct entities with the same `key` is rejected with `ValueError` by
  `settle_out_of_combat_cast` before resolution, with no affinity change and no clock advance.
- [x] 5.18 A world-clock-acquisition failure test (rubber-duck suggestion): with `clock` not supplied,
  `get_world_clock()` raising after a successful resolution and scan rolls back the penalty through the
  settlement-side restore, leaving relations unchanged in-process and in the database.

## 6. Validation

- [x] 6.1 Run `uv run --locked python -m compileall -q world commands` to catch syntax errors early.
- [x] 6.2 Run the new/extended test module directly, e.g.
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py world.rules.tests.test_cast_settlement`
  (confirm the exact module path matches wherever section 5's tests actually landed).
- [x] 6.3 Run the full existing `world.rules.tests.test_cast_settlement` module (plus
  `commands`' own test package if `CmdCast` has dedicated tests) to confirm no existing out-of-combat
  cast behavior regressed.
- [x] 6.4 Run `uv run --locked python -m tools.spec_traceability check` and address any reported gap.
- [x] 6.5 Run `openspec validate sexual-resist-out-of-combat --strict` and resolve every finding.
- [x] 6.6 Run `uv run --locked -m unittest discover -s tests -t .` to confirm no repository-wide
  contract regressed.
- [x] 6.7 Run the full Evennia suite
  (`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 commands server typeclasses world web.webclient`)
  before archiving, per `AGENTS.md`'s guidance that the full suite is the pre-archive bar.
