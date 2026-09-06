# Tasks: defeat-aftermath-companion-victims

## 1. Pool selection

- [ ] 1.1 `world/rules/defeat_aftermath.py`: candidate pool = non-fled allied participants (player + knocked-out companions); extend `derived_roll(..., participant_slot, purpose="target")` for per-attempt victim selection; fled filtering before the draw
- [ ] 1.2 Per-victim writes: declared deltas onto the selected victim's own `SexualState` via the existing write path; symmetric counter credits per the shared convention; `violation_act` entries carry the victim identity

## 2. Outcome mapping + wake lines

- [ ] 2.1 Return `{participant: ViolationOutcome}` from `run_violation_sequence` (player key shape unchanged)
- [ ] 2.2 zh-tw companion wake observation lines in `player_messages.py` (read of the outcome, no new mutation)

## 3. Tests (extend `test_defeat_aftermath_violation.py`; shard manifest unchanged)

- [ ] 3.1 Pool cases: knocked-out companion selected takes its own writes + symmetric credits; fled companion never selected and untouched; solo party byte-identical to the pinned player-only baseline; all-allies-fled settles cleanly; mixed two-victim sequence credits the violator exactly once per attempt
- [ ] 3.2 Companion wake observation emitted with matching counts
- [ ] 3.3 `covers_requirement` annotations for the modified requirements (migrate the player-only requirement's IDs to the new full-pool requirement); `tools.spec_traceability check` green
- [ ] 3.4 Focused run green: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_defeat_aftermath_violation world.rules.tests.test_defeat_aftermath_core`; `tools.observability_lint check`; `git diff --check` clean
