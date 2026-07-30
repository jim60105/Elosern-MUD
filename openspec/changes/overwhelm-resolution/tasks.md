## 1. Package layout and confirmations

- [ ] 1.1 Confirm `world/rules/` holds change 9's `combat.py` (`effective_power`, `run_round`,
      `is_battle_over`, `Battlefield`, `COMBAT_YAML`) and change 8's `event_log.py`
      (`EventEntry`, `EventLog`, `render_plain_text`); create `world/rules/overwhelm.py` and
      `world/rules/rulebook/overwhelm.yaml` as new files.
- [ ] 1.2 Confirm the exact import paths and public names for `world.rules.combat.{effective_power,
      run_round, is_battle_over, Battlefield, COMBAT_YAML}` and `world.rules.event_log.{EventEntry,
      EventLog, render_plain_text}` against how changes 8/9 actually landed — no code in this change
      should assume an unconfirmed symbol name before this step.
- [ ] 1.3 Inspect change 9's landed `_step7_build_event_log`-equivalent construction (however
      `run_round()` actually turns a `damage:*` `PendingEffect` into `EventEntry` instances) to confirm
      the `"roll"`/`"damage"` kind split and the `"damage"` entry's `data` field names (`hit`, `amount`
      assumed per design.md D-4/Open Questions) — adjust `compress_event_logs()`'s field-name reads in
      task 7 if the landed names differ before writing any test against them.

## 2. Rulebook data (`world/rules/rulebook/overwhelm.yaml`)

- [ ] 2.1 Author `power_ratio_threshold: 100` with the design.md D-1/D-2 derivation referenced in an
      inline YAML comment (not restated in full — point to design.md), noting explicitly that both
      directions are checked as independent divisions, not via a second `0.01`-style constant.
- [ ] 2.2 Author `max_estimated_rounds: 5` with design.md D-1's calibration table referenced in an
      inline YAML comment — the value that makes overwhelm mean "decided and quick," not merely
      "decided."
- [ ] 2.3 Implement a small loader in `world/rules/overwhelm.py` (`OVERWHELM_YAML =
      yaml.safe_load(...)`), mirroring change 9's `COMBAT_YAML` loader pattern exactly.

## 3. The power-ratio signal (`world/rules/overwhelm.py`)

- [ ] 3.1 Implement `team_effective_power(battlefield, team_key) -> float` per design.md D-1: sums
      `combat.effective_power(entity)` over every member of `battlefield.teams[team_key]` that is both
      present in `battlefield.roster`, alive (`hp.value > 0`), and not in `battlefield.fled`.
- [ ] 3.2 Implement `power_ratio_verdict(battlefield, team_a, team_b) -> str | None` per design.md D-1:
      checks `power_a / power_b >= threshold` and `power_b / power_a >= threshold` as two independent
      divisions; handles a zero-power side by returning the other team's key without raising
      `ZeroDivisionError`; returns `None` otherwise.
- [ ] 3.3 Test: a team whose aggregate `effective_power()` is ≥100x the other's yields that team as the
      ratio verdict; a <100x gap in both directions yields `None`; a wiped side (zero living members)
      yields the other side automatically; a dead-but-still-rostered member contributes zero to their
      team's aggregate while a living member's own `effective_power()` is unaffected by their own
      current-hp attrition (per `combat-resolution`'s own established discipline, dice-combat design.md
      D-4) — reusing dice-combat's own worked reference fixtures (human elite, elf, mid/high monster)
      where useful.

## 4. The hit-rate signal (`world/rules/overwhelm.py`)

- [ ] 4.1 Implement `_agility_saturation(attacker, defender) -> Literal["hit", "miss", "contested"]`
      per design.md D-1: reads `SkillHandler.effective_value("agility")` and
      `evaluate_combat_modifiers()` for both entities exactly as `dice-combat`'s `_handle_damage` does,
      computes `delta = attacker_agi - defender_agi`, and returns `"hit"` if `delta >= 50`, `"miss"` if
      `delta <= -50`, else `"contested"`. Makes zero calls to `roll_d100()`.
- [ ] 4.2 Implement `_adjusted_agility(entity) -> float` as the shared helper both this signal and the
      round-bound signal (task 5) use — `effective_value("agility")` adjusted by
      `evaluate_combat_modifiers()`'s `agility` percentage key — so the two signals never drift by
      reading agility two different ways.
- [ ] 4.3 Implement `hit_rate_verdict(battlefield, team_a, team_b) -> str | None` per design.md D-1:
      returns `team_a` only if every living, non-fled member of `team_a` saturates `"hit"` against
      every living, non-fled member of `team_b` AND every member of `team_b` saturates `"miss"` against
      every member of `team_a` (checked as two independent `all()` conditions, not derived from one via
      negation); symmetric for `team_b`; returns `None` if neither holds or either side has no living
      members.
- [ ] 4.4 Test: a fully-saturated one-directional matchup yields the correct team key; a single
      non-saturated cross-pair anywhere yields `None`; an asymmetric-`accuracy`-modifier fixture (one
      side's accuracy buffed, not derived from agility) proves the two saturation directions are
      checked independently, not as a negation of one `delta`; no `roll_d100()` call occurs anywhere in
      this function (source-inspection or call-count assertion).

## 5. The round-bound signal (`world/rules/overwhelm.py`)

- [ ] 5.1 Implement `_expected_damage_per_attack(attacker, defender) -> float` per design.md D-1: the
      actual to-hit probability (`clamp((50 + delta) / 100, 0, 1)` using the shared `_adjusted_agility`
      helper), `attacker.skills.effective_value("atk_phys")` as the representative damage stat, and
      **only** `COMBAT_YAML["damage"]["base_multiplier"]` (never `solid_hit_multiplier` or
      `crit_multiplier`) — a deliberately conservative, never-overestimated damage figure. Makes zero
      calls to `roll_d100()`.
- [ ] 5.2 Implement `estimated_rounds_to_conclude(battlefield, overwhelming_team, overwhelmed_team) ->
      float` per design.md D-1: sums the overwhelmed team's **current** (not max) hp across its living,
      non-fled members; sums the overwhelming team's `_expected_damage_per_attack()` output against the
      single highest-current-hp overwhelmed member; returns `remaining_hp / dmg_per_round` (handling a
      zero/negative `remaining_hp` as `0.0` and a zero `dmg_per_round` as `math.inf`, never raising
      `ZeroDivisionError`).
- [ ] 5.3 Test: the four calibration-table matchups from design.md D-1 (elf vs. human elite ≈1.5
      rounds; elf vs. a 3-member low-tier monster party ≈3.3 rounds; an illustrative calamity monster
      vs. a 3-member human party ≈3.9 rounds; a 10,000-hp defender against a `damage.floor`-only
      attacker ≈10,000 rounds) each produce an estimate within a reasonable tolerance of the design
      doc's worked figure.
- [ ] 5.4 Test that `estimated_rounds_to_conclude()` is current-hp-sensitive by design (decreases as the
      overwhelmed side's current hp decreases, with no change to any `effective_value()` output),
      explicitly contrasted in the same test module against `team_effective_power()` (task 3.1), which
      must NOT change under the identical current-hp decrease — the two functions answering
      deliberately different questions is itself the property under test.
- [ ] 5.5 Test no `roll_d100()` call occurs anywhere in `_expected_damage_per_attack()` or
      `estimated_rounds_to_conclude()` (source-inspection or call-count assertion).

## 6. Combining the signals (`world/rules/overwhelm.py`)

- [ ] 6.1 Implement `_decided_direction(battlefield, team_a, team_b) -> str | None` per design.md D-1:
      combines `power_ratio_verdict()` and `hit_rate_verdict()` — returns the shared verdict when both
      agree; returns whichever is non-`None` when only one fires; returns `None` when both are `None`
      or when they disagree.
- [ ] 6.2 Implement `classify_overwhelm(battlefield) -> str | None` per design.md D-1: computes
      `_decided_direction()`; if `None`, returns `None` immediately without calling
      `estimated_rounds_to_conclude()`; otherwise computes `estimated_rounds_to_conclude()` for the
      decided direction and returns `None` instead of that direction if the estimate exceeds
      `OVERWHELM_YAML["max_estimated_rounds"]`, else returns the decided direction.
- [ ] 6.3 Test every combination from the `overwhelm-threshold` spec: ratio-only fires (and is within
      the round bound), hit-rate-only fires (and is within the round bound), both agree, both disagree
      (a constructed tank-vs-duelist fixture: high defense/hp/low agility vs. low power/high agility,
      verifying `classify_overwhelm()` returns `None` even though each signal independently returns a
      non-`None`, opposite verdict), neither fires.
- [ ] 6.4 Test the round-bound gate specifically: a decided direction whose `estimated_rounds_to_
      conclude()` is comfortably within `max_estimated_rounds` is accepted by `classify_overwhelm()`;
      a decided direction (ratio signal fires on a large max-hp gap) whose `estimated_rounds_to_
      conclude()` exceeds `max_estimated_rounds` (a floor-damage grind fixture) is rejected —
      `classify_overwhelm()` returns `None` even though `power_ratio_verdict()` alone returns a
      non-`None` verdict for the same battlefield; the disagreement case (task 6.3) never calls
      `estimated_rounds_to_conclude()` at all (call-count or mock assertion — there is no direction to
      bound).
- [ ] 6.5 Test `classify_overwhelm()` is a pure function with no cached state: two consecutive calls on
      the same battlefield object return the same result unless the battlefield's own state changed in
      between; a call after a mid-fight `effective_value()` change (simulated buff activation/disguise
      drop) returns a different result with no reset step required; a call after real progress falls
      behind what an earlier accepted estimate assumed (simulated: reduce the overwhelming side's
      recent damage output without changing the overwhelmed side's hp accordingly) returns `None` on
      the next call, without any special invalidation step.

## 7. Single-shot resolution (`world/rules/overwhelm.py`)

- [ ] 7.1 Implement `OverwhelmResult` (frozen dataclass): `event_logs: tuple[EventLog, ...]`,
      `rounds_elapsed: int`, `total_seconds: int`, `overwhelming_team: str | None`,
      `verdict_after: str | None`, `battle_over: bool`, per design.md D-3.
- [ ] 7.2 Implement `resolve_overwhelm(battlefield, action_provider, max_rounds=12) -> OverwhelmResult`
      per design.md D-3: returns immediately (zero rounds) if `classify_overwhelm()` is already `None`
      or `combat.is_battle_over()` is already `True`; otherwise loops calling
      `combat.run_round(battlefield, action_provider)` — and only this call — accumulating raw
      `EventLog`s, incrementing `rounds_elapsed`, and recomputing `classify_overwhelm()` after every
      round, stopping the loop the moment the verdict changes from the one computed at entry,
      `is_battle_over()` becomes true, or `rounds_elapsed` reaches `max_rounds`. Calls
      `compress_event_logs()` (task 8) on the accumulated raw logs before returning. `total_seconds`
      SHALL always equal `rounds_elapsed * 6` — the honest sum for however many rounds actually ran,
      never a flat charge regardless of `rounds_elapsed`.
- [ ] 7.3 Confirm (grep-based check, mirroring change 9's own task 10.2 discipline) that
      `world/rules/overwhelm.py` contains no call to `roll_d100()`, no direct write to any entity's
      `traits`/`buffs`/`sexual` state, and no reference to `WorldClock`/`advance()` — every mutation and
      every dice roll is reachable only through `combat.run_round()`.
- [ ] 7.4 Test the exact-consistency property (design.md D-3/D-5, `single-shot-resolution` spec): on a
      fixed seed and an identical starting `Battlefield` (deep-copied or reconstructed identically),
      compare `resolve_overwhelm()` against a hand-written loop calling `combat.run_round()` directly
      the same number of times — assert identical final hp for every entity, identical
      `rounds_elapsed`, identical winner, and entry-for-entry identical pre-compression `EventLog`
      sequences (expose the raw, pre-compression list internally for this test's use). Run this for
      **both** overwhelm directions (an elf/monster-tier team overwhelming a human-tier team, and the
      reverse — design doc §6.3's "player is one-shot").
- [ ] 7.5 Test early-exit-on-reclassification: construct a fixture where a mid-loop `effective_value()`
      change (a buff wearing off during `run_round()`'s own upkeep, or a disguise-drop event) flips
      `classify_overwhelm()`'s result after 1-2 rounds; assert `resolve_overwhelm()` stops calling
      `combat.run_round()` at that point and `verdict_after` reports the new value distinctly from
      `overwhelming_team`.
- [ ] 7.6 Test `total_seconds == rounds_elapsed * 6` and the golden single-round case: the elf-vs-
      human-elite reference matchup (dice-combat design.md D-4) resolves in exactly 1 round under its
      fixed seed, with the human-elite defender's final hp `<= 0`.
- [ ] 7.7 Test the bounded-curbstomp golden case (design.md D-5): a decided, multi-round-but-still-
      bounded fixture (e.g. the elf-vs-low-tier-monster-party calibration matchup) resolves fully via
      `resolve_overwhelm()`, with `rounds_elapsed` staying within a small, asserted upper bound.
- [ ] 7.8 Test the two boundary early-return cases: `resolve_overwhelm()` on an already-contested
      battlefield (including one that is decided-but-a-grind per the round-bound signal), and on an
      already-`is_battle_over()` battlefield, both performing zero `combat.run_round()` calls (mock or
      call-count assertion).
- [ ] 7.9 Test the `max_rounds` safety-cap golden case (design.md D-5): a constructed fixture where
      `classify_overwhelm()` keeps returning the same verdict every round for longer than `max_rounds`
      — asserts `resolve_overwhelm()` stops at exactly `max_rounds` rounds, `battle_over` is `False`,
      `rounds_elapsed == max_rounds`, and `total_seconds == max_rounds * 6` (the honest sum, not a flat
      charge).

## 8. EventLog compression (`world/rules/overwhelm.py`)

- [ ] 8.1 Implement `compress_event_logs(raw_logs, overwhelming_team, overwhelmed_team, rounds) ->
      tuple[EventLog, ...]` per design.md D-4: filters every `EventLog.entries` to drop `kind=="roll"`
      entries via `dataclasses.replace()`; drops any resulting `EventLog` left with zero entries; builds
      one summary `EventLog` (`kind="overwhelm_resolution"`, `actor=overwhelming_team`,
      `targets=(overwhelmed_team,)`, `time_cost_seconds=0`) whose single `EventEntry`'s `data` contains
      `rounds`, `hits` (count of `"damage"`-kind entries with a truthy `hit` field), and `total_damage`
      (sum of their `amount` field); prepends it to the filtered tuple.
- [ ] 8.2 Confirm (via `git diff` / source inspection) that `world/rules/event_log.py` is not modified
      by this change — `compress_event_logs()` uses only `EventEntry`'s and `EventLog`'s existing public
      constructors and `dataclasses.replace()`.
- [ ] 8.3 Test: a `"roll"`-kind entry is dropped; a `"damage"`-kind entry recording a miss survives
      unchanged; an all-`"roll"` input `EventLog` is dropped entirely from the output; the summary
      entry's `data["hits"]`/`data["total_damage"]` match a hand-computed total against a constructed
      fixture; the summary entry's `time_cost_seconds` is exactly `0`; the summary entry's `actor`/
      `target` equal the team-key arguments exactly.
- [ ] 8.4 Test fidelity: every individual `"damage"`-kind entry from the input is still present,
      correctly attributed to its original entity-keyed `actor`/`target`, in the compressed output
      alongside the summary entry — compression never reduces the record to only the aggregate.

## 9. Rendering with no LLM present

- [ ] 9.1 Test `event_log.render_plain_text()` (change 8, unmodified) against the summary `EventLog`
      `compress_event_logs()` produces: asserts every `{data[...]}` placeholder in the entry's
      `text_template` resolves against `data`, with no unresolved `{...}` remaining and no import of
      any `world/ai/` module anywhere in the call path.
- [ ] 9.2 Test that joining `render_plain_text()` over every `EventLog` in a compressed encounter's
      output tuple, in order, produces a non-empty, fully-resolved string reproducing the summary
      sentence followed by the individual per-hit sentences — the same join-over-a-list pattern an
      uncompressed `run_round()` output already requires.
- [ ] 9.3 Test `render_plain_text()` is called twice on the same compressed `EventLog` and returns
      byte-identical output both times (purity check).

## 10. Verification

- [ ] 10.1 Run the full `world/rules/tests/` suite added by this change and confirm every test passes.
- [ ] 10.2 Confirm `world/rules/overwhelm.py` never calls `WorldClock.advance()` or anything resembling
      it (grep-based check).
- [ ] 10.3 Confirm this change modifies no file authored by any earlier change — `git diff --stat`
      against the pre-change tree shows only new files under `world/rules/overwhelm.py`,
      `world/rules/rulebook/overwhelm.yaml`, and `world/rules/tests/`.
- [ ] 10.4 Confirm change 9's own golden and calibration test suites
      (`test_golden_combat.py`, `test_to_hit_calibration.py`, `test_effective_power.py`) still pass
      unmodified — this change never edits `combat.py`, `dice.py`, or `rulebook/combat.yaml`.
- [ ] 10.5 Confirm change 8's own `EventLog`/`event_log.py` test suite still passes unmodified, and that
      a diff of `event_log.py` against the pre-change tree is empty.
- [ ] 10.6 Confirm no fixture or test in this change's own suite requires more than `max_rounds` (12)
      real `combat.run_round()` iterations to complete — a grep/count-based check over the test suite's
      own fixtures, guarding against a regression back toward the unbounded-loop hazard this change's
      design revision exists to close.
- [ ] 10.7 Run `openspec validate overwhelm-resolution --strict` and confirm it passes.
