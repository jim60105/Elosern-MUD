## 1. Target classification

- [x] 1.1 Create `world/rules/combat_initiation.py` with a module docstring stating its single purpose: turning one exploration cast into a combat's opening move, and that exploration-side routing deliberately does not live in `world/rules/combat_session.py`
- [x] 1.2 Add `field_combat_target(actor, target)` returning `target` when it is a living `Monster` in the actor's own room, else `None`, documenting that hostility means being a `Monster` instance exactly as `engage()` already treats it
- [x] 1.3 Cover the `None` cases explicitly: NPC, companion, the actor itself, an object, a monster in another room, a monster at zero hp, and `None`

## 2. Entry-point validation order

- [x] 2.1 Add `initiate_field_combat(actor, skill_key, target, scale=1.0)` returning the `submit_player_action()` result shape
- [x] 2.2 Check `SkillDef.usable_out_of_combat` first and reject with `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT`, with a comment explaining that the check must be explicit because validation deliberately supplies a battlefield context
- [x] 2.3 Select the enemy line-up from the skill's `TargetSpec`: `SINGLE` yields the named monster; `AREA` yields every living `Monster` in the room as an explicit concrete list in deterministic order, never a shorthand
- [x] 2.4 Build the candidate `Battlefield` by passing an unpersisted `CombatSessionRecord` to `reconstruct_battlefield()`, using the same record-construction path `engage_group()` uses
- [x] 2.5 Validate through `revalidate_submission()` and `ActionResolver.preflight()` with a `BattlefieldActionContext` over the candidate; return the rejection unchanged and touch nothing on failure

## 3. Routing rejection for damaging skills

- [x] 3.1 In the cast routing, reject a skill carrying a `DamageEffect` whose target is not a field-combat target, with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, before any resource, roll, session, or clock access
- [x] 3.2 Confirm a non-damaging skill aimed at a non-monster still reaches `settle_out_of_combat_cast()` with no behaviour change

## 4. Session creation and the opening action under one boundary

- [x] 4.1 Snapshot `actor.db.active_combat` and `actor.db.dialogue_session` **before** `engage_group()` runs, reusing `world/rules/action.py::_attribute_snapshot` / `_restore_attribute` the way `_snapshot_round_touched()`'s `extra` dict already does for `active_combat`
- [x] 4.2 Wrap `engage_group()` and `submit_opening_action()` in one `transaction.atomic()` owned by `initiate_field_combat()`
- [x] 4.3 On the failure path, restore both snapshotted attributes, because the Evennia idmapper cache is not transaction-aware and would otherwise leave the engaged session and the cleared dialogue session readable in process after the rollback
- [x] 4.4 On the failure path, also `unregister_participants()` for the engaged participant identities, since skip-safety registration is process state a database rollback cannot undo
- [x] 4.5 Add a comment explaining why the submission body's own `_snapshot_round_touched()` cannot cover this: it snapshots at its own entry, which in this flow is already after engagement wrote `active_combat`, so its restoration would reinstate the engaged session instead of the pre-engagement absence
- [x] 4.6 Add the comment recording that the nested submission-body `atomic()` degrades to a savepoint and that its `transaction.on_commit` callbacks fire on this outer commit, as that body's own contract states
- [x] 4.7 Confirm the opening cast charges no `AdvanceSource.COMMAND` time; the session accumulates it and the terminal settlement charges it as combat time

## 5. Observability

- [x] 5.1 Emit one `field_combat_initiated` info event through the `world.observability` facade with `char`, `room`, `tick`, `skill`, `enemy_count`, and `opening` context
- [x] 5.2 Stage it via `transaction.on_commit` on the outer transaction with every value snapshotted at staging time, so the callback performs no computation and a rollback logs nothing
- [x] 5.3 Confirm the module uses named facade imports and that every `except` block re-raises, emits a facade event, or carries a reasoned exemption comment

## 6. Command routing and documentation

- [x] 6.1 In `commands/action.py::_cast_out_of_combat()`, consult `field_combat_target()` first; a monster routes to `initiate_field_combat()` and renders through `settle_to_messages()`, anything else keeps the existing route
- [x] 6.2 Keep the existing `caller.ndb.action_context` and flee-key handling intact for the unchanged route
- [x] 6.3 Update `docs/game/commands.md` and `docs/game/command-reference.md`: aiming at a room monster starts combat with that skill as the opening action, a damaging skill cannot be aimed at anything else, and a non-damaging skill aimed elsewhere behaves as before
- [x] 6.4 Keep `tests/test_command_docs.py` green

## 7. Tests

- [x] 7.1 Create `world/rules/tests/test_combat_initiation.py` and register it in exactly one shard of `.github/evennia-shards.json` — the `rules-a` shard, which already holds every `world.rules.tests.test_combat_session_*` module
- [x] 7.2 `field_combat_target()`: every positive and negative case from task 1.3
- [x] 7.3 A damaging skill aimed at a room monster opens combat and resolves as the opening action
- [x] 7.4 A non-damaging skill — buff, heal, cleanse, debuff-only, sexual act — aimed at a room monster also opens combat, resolves as the opening action, and runs exactly one ordinary round
- [x] 7.5 A healing skill aimed at a room monster starts the fight and heals the monster, asserting the accepted consequence rather than a special case
- [x] 7.6 A damaging skill aimed at an NPC rejects with `DAMAGE_REQUIRES_MONSTER_TARGET` and deducts no resource, persists no session, makes no roll, and leaves the clock unchanged
- [x] 7.7 A resistible sexual act aimed at an NPC is unchanged: it routes through `settle_out_of_combat_cast()`, its out-of-combat coercion scan runs, and command time is charged as before
- [x] 7.8 A sexual act aimed at a monster runs the in-combat `_scan_sexual_coercion()` instead of the out-of-combat scan — asserting the recorded behaviour change
- [x] 7.9 A `usable_out_of_combat=False` skill and the reserved flee key are each rejected before the candidate battlefield is built
- [x] 7.10 A candidate-validation rejection persists no session, registers no battlefield, deducts no resource, and advances no time
- [x] 7.11 The candidate battlefield's roster keys and team membership equal the reconstructed session's for the identical targets
- [x] 7.12 A faction-sensitive skill sees the room monster as an enemy during validation, proving the battlefield-backed context is in use
- [x] 7.13 `AREA` in a three-monster room engages all three and computes the verdict against the whole team; `SINGLE` in the same room engages only the named monster; `AREA` in a one-monster room takes no distinct path
- [x] 7.14 Forcing `submit_opening_action()` to raise leaves no persisted session, no registered battlefield, no entity surface change, no clock change, and no boundary event
- [x] 7.15 After that forced failure, `read_session(actor)` in the same process without any reload returns `None`, proving the `active_combat` idmapper cache was restored and the actor is not stranded in a session the database no longer holds
- [x] 7.16 After that forced failure for an actor who held a dialogue session, `actor.db.dialogue_session` reads in process as the pre-attempt session, not as cleared; and on a committed initiation it is retired exactly as ordinary engagement retires it
- [x] 7.17 A field initiation that ends the fight settles once, runs its post-commit work once, and logs each observability event once
- [x] 7.18 A committed initiation logs exactly one `field_combat_initiated` whose `opening` matches the dispatch taken and whose `enemy_count` matches the engaged monsters; a rejected one logs none
- [x] 7.19 Command-level coverage: the cast command routes a monster-targeted cast into combat and everything else through the existing path
- [x] 7.20 Annotate every new test with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 8. Verification

- [x] 8.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules` *(run with --noinput --parallel 4 in 109s: my module green serially 12x; the flagged failures reproduce only under --parallel — one bounded run shared one retained sqlite file and one process leaked its session — serial co-process runs of the four flagged modules are green; the heal fixture's monster-flee flake was real and is now pinned; quest-issuer registry pollution traces to a foreign unregistered module, not this change)*
- [x] 8.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands tests.test_command_docs`
- [x] 8.3 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`
- [x] 8.4 `uv run --locked python -m tools.observability_lint check`
- [x] 8.5 `uv run --locked python -m tools.spec_traceability check`
- [x] 8.6 `uv run --locked python -m compileall -q world commands`
- [x] 8.7 `openspec validate field-combat-initiation --strict`
