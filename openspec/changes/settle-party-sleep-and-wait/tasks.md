# Tasks

Worker: luna
Branch: `feat/settle-party-sleep-and-wait`
Worktree: `.worktrees/settle-party-sleep-and-wait`

## 1. Party mental intervals and completion

- [ ] 1.1 Extend `world/rules/clock.py::WorldClock.advance` and `build_advance_snapshot_registry` with explicit mental activity/scope context while preserving unrelated fixed stage order and the 86400-second bound. Classify every production advance caller and wire player-driven noncombat mental scope via `present_party_scope`; extend `world/rules/tests/test_clock.py` and `test_party_time_settlement.py` for narrow-resource/wide-mental scope and later-source rollback.
- [ ] 1.2 Integrate sampled full-interval completion through `world/rules/cast_settlement.py::settle_out_of_combat_cast` and `world/rules/items/settlement.py::use_item`, plus other indivisible player-time owners. Extend existing cast/companion field tests for depleted caster and only-unselected-companion cases; assert full effects/costs/time and post-commit-only prompts without retrospective recovery.
- [ ] 1.3 Update `clock.py::_practice_settlement` to preserve sleeping/zero-time bookings, consuming only later eligible awake SKIP intervals under existing whole-hour rules. Extend `world/rules/tests/test_time_skip.py` with mixed sleeping/studying members, interruption and rollback; document the unchanged whole-hour rule and sleeping-booking preservation in both player command pages.

- [ ] 1.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 2. Entry and interruptible skip operation

- [ ] 2.1 Refactor `world/rules/time_skip.py::advance_skip` and `seconds_to_full_regen` into proposed explicit `enter_sleep`/`continue_sleep` and immutable accepted elapsed results. Verify full gauges with half reserve need 15000 seconds, forced sleep needs 6000 seconds from zero, shared activity differs per member and entry advances zero.
- [ ] 2.2 Compose pure next forced-sleep/wake/registered-interaction boundaries with skip safety and one committed interval, including tie events and accepted-operation replay protection. Extend `test_time_skip.py` with first-wake, first-collapse, 37-second synthetic event, unsafe wait and duplicate-result cases; verify requested remainder is discarded.
- [ ] 2.3 Route `commands/skip.py` and `web/webclient/actions/exploration_actions.py::_wait_adapter` through that same operation, keeping rest as waiting transport and existing practice/daypart/protocol bounds. Update existing waiting Vue presentation and `web/webclient-app/tests/waiting_surface.test.js`, exploration adapter tests, both command docs and `tests/test_command_docs.py`; verify identical text/browser elapsed receipts and no quiet-rest choice.
- [ ] 2.4 Change `server.dream_service.enter_after_sleep` integration to accept only positive elapsed voluntary sleep receipts after handoff opportunity. Extend `world/narrative/tests/test_dream_surface.py` for entry-only, zero duration, forced sleep, interruption and offline failure; verify no duplicate resource/time settlement.

- [ ] 2.5 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 3. Stationary travel and recovery surface

- [ ] 3.1 After `charge-distance-based-travel`, enforce present-forced-sleeper preflight across `typeclasses/exits.py` plain/costed exits, both gate directions and wilderness movement before any waiver/relocation. Reuse intended source-present follow scope in `world/rules/movement.py` and `movement_settlement.py`; extend movement/party tests for awake possession, remote sleeper exclusion and zero-write refusal on every lineage.
- [ ] 3.2 Expose non-acting status/explicit safe recovery wait for no-awake-candidate accounts through the shared rules operation, leaving contextual transfer delivery to its dependent change. Verify first eligible wake, no background clock, hostile refusal and local awake interactions; document stationary recovery and travel refusal in both command pages.

- [ ] 3.3 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 4. Integrated handoff gates

- [ ] 4.1 Run the owning focused suites and `uv run --locked python -m tools.contract_gate` before handoff/archive; retain actual command output as implementation evidence, without claiming planning artifacts prove runtime behavior.
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.observability_lint check`; verify substantive literal-ID coverage and keep `tools/observability_freeze.json` shrink-only. Use only `world.observability` for production logging.
- [ ] 4.3 Run `tests/test_command_docs.py` through the repository's documented test runner for every changed command surface, then `openspec validate settle-party-sleep-and-wait --strict`; verify docs, deltas and real test evidence agree before handoff.
