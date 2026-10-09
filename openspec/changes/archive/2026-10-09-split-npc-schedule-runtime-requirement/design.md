# Design

## Context

See `proposal.md` for motivation. The live `npc-schedule-runtime` capability currently has a single clock-source requirement with distinct source-selection, occurrence, entry, silencing, and exam-hold contracts. `tools.spec_traceability` derives canonical IDs from requirement headings and checks that every ID is covered by substantive test annotations. The runtime and its tests are not changed in this proposal.

## Goals / Non-Goals

**Goals:**
- Make each concern a separately testable requirement while retaining all current observable behavior and schedule-hold clauses.
- Make canonical requirement-ID updates explicit and keep the resulting requirements traceable to substantive tests.
- Pass the specified strict validation and repository contract gates.

**Non-Goals:**
- Change schedule settlement, clock arithmetic, service silencing, hold persistence/release, event shape, or startup composition.
- Alter unrelated requirements in `npc-schedule-runtime`, implement the proposal, or archive it.

## Decisions

- Remove the old requirement and add the eight exact requirements in the delta: `the-npc-schedules-settlement-source-selects-tagged-npcs`, `occurrences-obey-the-shared-due-window-boundaries`, `cycles-and-ordering-remain-absolute-and-deterministic`, `due-state-entries-update-state-and-emit-events`, `due-movement-uses-real-exits-and-emits-events`, `silenced-npcs-skip-all-schedule-effects-first`, `an-active-exam-hold-defers-host-schedule-mutation`, and `releasing-an-exam-hold-replays-its-interval-once`.
- Move each pre-existing clause and scenario into the matching requirement, preserving daily/weekly phase anchoring, all interval boundaries, stable IDs/order, real Exit traversal, JSON-safe event data, skip-first silence behavior, return-to-anchor resumption, unrelated-NPC equivalence, held interval recovery, one-time replay, no clock advance, early availability of hold/release core, and active-hold preservation on corrupt schedule storage.
- The old canonical ID `npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries` is removed. The eight replacement IDs are the kebab-case suffixes above prefixed with `npc-schedule-runtime::`. In the annotation migration, retain substantive mappings from `CycleArithmeticTests.test_absolute_cycles_match_bounded_integer_oracle`, `WeeklySettlementTests.test_bulk_matches_daily_windows_across_calendar_boundaries_and_reload` and `.test_assignment_at_due_tick_keeps_absolute_phase_and_order`; `test_npc_schedule_runtime` tests `test_due_state_entry_updates_state_and_emits_event_with_payload`, `test_due_move_entry_relocates_along_a_real_exit_and_emits_events`, `test_move_success_writes_the_templates_default_state`, `test_occurrences_carry_the_day_start_plus_offset_due_tick`, `test_npc_without_a_schedule_settles_to_nothing`, `test_passed_occurrences_never_settle_after_mid_day_assignment`, `test_assignment_exactly_at_a_due_tick_settles_that_occurrence`, `test_start_boundary_occurrences_already_settled_do_not_replay`, `test_multi_day_skip_matches_repeated_day_by_day_advances`, `test_duplicate_key_npcs_tie_break_by_stable_primary_key`, `test_traveling_place_bound_companion_settles_nothing`, and `test_returning_to_anchor_resumes_settlement`; source selection is covered by `SourceRegistrationTests.test_sync_registers_settle_npc_schedules_as_the_only_source`. Exam deferral/release coverage belongs to substantive `test_guild_exam_schedule_hold` tests including `test_weekly_departure_after_synthetic_terminal_sequences`, `test_effective_from_excludes_past_occurrences_and_orders_multiple_cycles`, `test_locked_exit_is_consumed_and_same_tick_state_still_settles`, and `test_indeterminate_schedule_keeps_pending_hold_for_repair`. During apply, compare the full original scenario list to this clause mapping; verify every annotation against assertions, add only needed secondary IDs, and remove any obsolete old-ID association whose asserted behavior has no replacement requirement (do not force-fit it).
- The separate `guild-exam-schedule-hold` capability already specifies effective-from, silencing, locks/vetoes, per-entry failure isolation, recoverability/idempotence, and transactional rollback; this change leaves that capability untouched and does not duplicate or weaken it.
- Keep the unrelated NPC-movement, failed-entry, interaction-gating, and startup-recovery requirements unchanged.

## Risks / Trade-offs

- A scenario could be lost or detached from its contract during the split. Mitigate by mapping every clause and existing scenario to one replacement requirement, then review the delta against the synchronized capability and run strict validation.
- Removing the old canonical ID can leave stale or uncovered annotations. The ID/test mapping above and `tools.spec_traceability check` mitigate this risk; the latter is also required after implementation.
- Text compression could weaken semantics. The acceptance gate is clause-by-clause preservation, not merely successful parsing or shorter text.