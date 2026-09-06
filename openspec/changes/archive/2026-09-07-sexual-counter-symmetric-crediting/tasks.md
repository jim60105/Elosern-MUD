# Tasks: sexual-counter-symmetric-crediting

## 1. Act-definition flip (data rows)

- [x] 1.1 `world/skills/sexual_acts/combat.py`: `combat_tease` seed row (first row of `COMBAT_ACTS`) — `participant_counters=("hostile_act_count",)`
- [x] 1.2 `world/skills/sexual_acts/combat.py`: all eight rows — mirror `hostile_act_count` into `participant_counters`
- [x] 1.3 `world/skills/sexual_acts/interspecies.py`: all seven rows — mirror `interspecies_act_count` into `participant_counters`
- [x] 1.4 `world/skills/sexual_acts/shame.py`: `shame_provocative_gaze` row — mirror `hostile_act_count`; the four public-exposure rows stay `participant_counters=()`

## 2. Convention documentation

- [x] 2.1 Rewrite the module docstrings of `combat.py`, `interspecies.py`, and `shame.py` (the combat seed lives in `combat.py`; `solo.py` documents no crediting convention) to state the symmetric convention and the direction-bound exception (`exposure_act_count` / `watched_count` stay actor-only)
- [x] 2.2 `world/skills/sexual_acts/_builder.py`: document the counter semantics split (direction-free vs direction-bound) next to the `actor_counters` / `participant_counters` fields

## 3. Regression-test rewrite

- [x] 3.1 `world/skills/sexual_acts/tests/test_seed_acts.py`: combat-seed test expects both participants credited; move `covers_requirement` to the renamed seed ID
- [x] 3.2 `world/skills/sexual_acts/tests/test_combat_catalog.py`: actor-only crediting test inverted to symmetric (keep the force-compliant resist rolls pattern)
- [x] 3.3 `world/skills/sexual_acts/tests/test_interspecies_catalog.py`: Monster-target crediting test inverted; the "Monster target is never credited" docstring-era pins updated
- [x] 3.4 `world/skills/sexual_acts/tests/test_shame_catalog.py`: `shame_provocative_gaze` test inverted + public-exposure actor-only pin kept; move `covers_requirement` to the renamed gaze ID
- [x] 3.5 Audit `test_registry_structure.py` and `test_acceptance.py` for asymmetry pins; update any that assert the retired convention

## 4. Traceability and manifest

- [x] 4.1 `uv run --locked python -m tools.spec_traceability list` for the four delta capabilities; confirm every MODIFIED/RENAMED requirement keeps a `covers_requirement`-annotated test; `check` green
- [x] 4.2 Confirm `.github/evennia-shards.json` needs no change (no new test modules); `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills` green
- [x] 4.3 `uv run --locked python -m tools.observability_lint check` (no logging touched) and `git diff --check` clean
