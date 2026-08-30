# Proposal: declared-practice-skip

## Why

`magic-xp-engine-retirement` deleted ambient study XP and left the clock's
`practice_settlement` stage a zero-growth placeholder; `use-driven-skill-lineage`
made proficiency the only growth currency, accruable only by use. Design
`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md` §11 (D7)
closes the loop: a player can DECLARE practice when skipping time — growth from
a declared intention, never from time passing unobserved.

## What Changes

- The `rest` time-skip command gains the declared-practice clause (design
  syntax `skip <hours> [practice <skill>]`; the mounted command carrying the
  duration form is `rest`, so the shipped surface is
  `rest <duration> [practice <skill>]`; a no-clause `rest` is the explicit
  rest and gains nothing).
- A declared-practice booking is preflighted BEFORE any clock advance: skill
  must be owned, a legal ACTIVE skill, and not saturated at its tip cap.
  Stable rejection reasons `PRACTICE_SKILL_UNKNOWN` / `PRACTICE_SKILL_CAPPED`
  with ZERO clock advance — a skip never half-applies.
- On an accepted booking, the clock's `practice_settlement` stage becomes the
  real writer: exactly SKIP-sourced, once per entity per advance, closed-form
  per whole study-hours (duration-size independent):
  `hours × PRACTICE_XP_PER_STUDY_HOUR (10.0) × learning × affinity ×
  growth_rate_multiplier`, saturating at the derived tip cap, writing only
  `db.skill_proficiency`.
- `progression.yaml` carries `PRACTICE_XP_PER_STUDY_HOUR` with the
  playtest-recalibration header note.

## Capabilities

### New Capabilities

(None — the contract lands in the existing time-skip, safety-gate, and
settlement-order capabilities.)

### Modified Capabilities

- `time-skip-commands`: the `rest` command's practice clause and booking
  preflight.
- `skip-safety-gate`: practice rejections compose with the safety gate and
  still perform zero clock advance.
- `settlement-stage-order`: the `practice_settlement` stage stops being a
  zero-growth placeholder and becomes the declared-practice writer.

### Removed Capabilities

(None.)

## Impact

- Code: `commands/skip.py` (`CmdRest` clause + booking),
  `world/rules/time_skip.py` (booking preflight helper),
  `world/rules/clock.py` (stage body), `world/rules/progression.py`
  (closed-form hourly grant), `world/rules/rulebook/progression.yaml`.
- Tests: command-level rejection/acceptance tests; clock-stage integration
  tests. No new test modules unless clause tests need their own file (then
  `.github/evennia-shards.json` registration in the same change).
- No backward-compatibility or migration work: the project is unreleased with
  zero users.
