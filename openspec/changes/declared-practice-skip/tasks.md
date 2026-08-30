# Tasks: declared-practice-skip

## 1. Booking surface

- [x] 1.1 `commands/skip.py::CmdRest`: parse the optional
  `practice <skill>` clause after the duration token; parse → safety gate →
  booking preflight in that fixed order.
- [x] 1.2 `world/rules/time_skip.py`: `preflight_practice_booking(actor,
  skill_key) -> PracticeReject | None` — ACTIVE + owned + below derived tip
  cap; stable reasons `PRACTICE_SKILL_UNKNOWN` / `PRACTICE_SKILL_CAPPED` with
  zh-tw messages.
- [x] 1.3 Rejections: message printed, `WorldClock.advance()` never called, no
  booking recorded (zero clock advance on every rejection path).

## 2. Settlement writer

- [x] 2.1 `world/rules/clock.py`: the `practice_settlement` stage reads the
  actor's pending booking (set by `CmdRest` before `advance`), computes
  `completed_whole_hours × PRACTICE_XP_PER_STUDY_HOUR × learning × affinity ×
  growth_rate_multiplier` in closed form (once per entity per advance,
  SKIP-source only, no quantum loop), saturates at the tip cap, and consumes
  the booking.
- [x] 2.2 COMBAT-sourced advance leaves the booking untouched (skipped stage).
- [x] 2.3 `world/rules/progression.py`: closed-form hourly grant helper
  (shares the affinity/growth/learning factors with the use-accrual path — one
  formula, two entry points). Storage SHALL route through
  `use-driven-skill-lineage`'s shared `award_practice_xp(entity, skill_key, xp)`
  primitive (the sole clamping writer at `cap(S)`); no direct
  `skill_proficiency` write from this helper.
- [x] 2.4 `world/rules/rulebook/progression.yaml`: `PRACTICE_XP_PER_STUDY_HOUR:
  10.0` with the playtest-recalibration header note.

## 3. Tests

- [x] 3.1 Command tests (extend the existing `commands` skip tests): valid
  booking settles hourly; capped/unknown/unowned/PASSIVE rejections with zero
  `advance()` calls (assert the mock was never called); plain rest grows
  nothing; safety-gate rejection precedes booking check.
- [x] 3.2 Clock integration: booking survives a COMBAT-source advance and
  settles on the next SKIP advance; hourly math ignores sub-hour remainders;
  a booked award crossing the derived tip cap saturates identically to a
  per-use award (same primitive, one clamp); growth buff participates.
- [x] 3.3 No new test modules expected → `.github/evennia-shards.json`
  untouched (register in-change if a new file is created).
- [x] 3.4 Command docs (in this change): `rest` syntax row + description gain the
  `[practice <skill>]` clause in `docs/game/command-reference.md`, the overview row
  in `docs/game/commands.md`, and the curated manifest in `tests/test_command_docs.py`;
  `tests.test_command_docs` green.

## Verification

- [x] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands world.rules`
- [x] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [x] V3 `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] V4 `openspec validate declared-practice-skip --strict`
- [x] V5 `git diff --check`

## Post-sync traceability (during archive/sync)

- [ ] P1 On sync, ensure the §3.1/§3.2 assertions carry the
  `time-skip-commands` / `skip-safety-gate` / `settlement-stage-order`
  requirement IDs (slugs unchanged — titles were not renamed).
