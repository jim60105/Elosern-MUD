# Tasks: defeat-aftermath-companion-victims

## 1. Pool selection

- [x] 1.1 `world/rules/defeat_aftermath.py`: candidate pool = non-fled allied participants (player + knocked-out companions); extend `derived_roll(..., participant_slot, purpose="target")` for per-attempt victim selection; fled filtering before the draw — implemented as `_violation_pool` (canonical order: player first, companions by ascending pk, identical from the battlefield and degraded paths) plus `_select_violation_victim` (solo pool short-circuits without touching the dice; the draw keys on session id + violator + attempt index + purpose="target" and resolves a pool slot)
- [x] 1.2 Per-victim writes: declared deltas onto the selected victim's own `SexualState` via the existing write path; symmetric counter credits per the shared convention; `violation_act` entries carry the victim identity (entry `target` is the selected victim; companion-victim template variants added)

## 2. Outcome mapping + wake lines

- [x] 2.1 Return `{participant: ViolationOutcome}` from `run_violation_sequence` (player key shape unchanged; only participants selected at least once appear)
- [x] 2.2 zh-tw companion wake observation lines in `player_messages.py` (read of the outcome, no new mutation — `companion_wake` kind plus the three companion-victim violation templates)

## 3. Tests (extend `test_defeat_aftermath_violation.py`; shard manifest unchanged)

- [x] 3.1 Pool cases: knocked-out companion selected takes its own writes + symmetric credits; fled companion never selected and untouched; solo party byte-identical to the pinned player-only baseline; all-allies-fled settles cleanly; mixed two-victim sequence credits the violator exactly once per attempt — plus canonical cross-path pool order, unselected-companion omission (D-P3), and a mixed-pool rollback replay
- [x] 3.2 Companion wake observation emitted with matching counts (rendered-surface assertion included)
- [x] 3.3 `covers_requirement` annotations for the modified requirements (the full-pool requirement keeps its heading, so its ID is unchanged; the wake-observation test carries the new ADDED requirement's slug); `tools.spec_traceability check` reports 0 uncovered requirements and exactly one expected `unknown-requirement-id` for the ADDED requirement until the archive workflow syncs the delta spec into `openspec/specs/` (the DA4 task 4.5 precedent; archive is owner-gated)
- [x] 3.4 Focused run green: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_defeat_aftermath_violation world.rules.tests.test_defeat_aftermath_core world.prompts.tests.test_verbatim_shipment` (89 tests); `tools.observability_lint check` clean; `git diff --check` clean
