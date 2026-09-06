# Tasks: defeat-aftermath-recovery

## 1. Rulebook `recovery` section

- [ ] 1.1 `world/rules/rulebook/defeat_aftermath.yaml`: add `recovery` section (`regen_scale`, `max_recovery_seconds`, `wake_fraction: 0.05`); register its validator with the core's per-section loader; malformed section fails load (test)

## 2. Solve + advance + clamp

- [ ] 2.1 `world/rules/defeat_aftermath.py`: `solve_recovery_seconds(current, carried, rate, scale, target, cap)` — minimum whole seconds via the virtual scaled-rate model `floor(current + carried + rate×scale×t) ≥ target`, integer-search guard, `t = 0` when already at/above; pure function, unit-tested against the clock's model semantics (fraction carrying, floor behavior, interval overshoot)
- [ ] 2.2 Wire the phase after the core's `weak_granted`: advance once by `t` (source `defeat_aftermath`), clamp HP to exactly `ceil(max_hp × wake_fraction)` when overshot, EventLog `recovery_advance` + zh-tw wake line, widened observability context `{..., seconds, hp_wake}`; cap-hit path advances the cap, skips the clamp, emits one `log_error`

## 3. Battery extension (same test module, D-C7 manifest)

- [ ] 3.1 Recovery rows in `world/rules/tests/test_defeat_aftermath_core.py`: exact-target wake; mid-interval overshoot clamped (coarse-rate fixture); already-above inert path; window crossing exactly one quest deadline + one restock boundary — only those two clock mutations outside declared writes; cap-hit error path
- [ ] 3.2 Rollback injection after the clamp: clock, HP, EventLog all pre-settlement; retry reproduces the same `t`
- [ ] 3.3 Retained-winner smoke: defeat a quest-bound winner → wake at target → in-room skip refused → move adjacent → rest succeeds to full

## 4. Traceability + gates

- [ ] 4.1 `covers_requirement` annotations for every requirement; `uv run --locked python -m tools.spec_traceability check` green; `.github/evennia-shards.json` unchanged (same modules)
- [ ] 4.2 Focused run green: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_defeat_aftermath_core`; `tools.observability_lint check`; `git diff --check` clean
