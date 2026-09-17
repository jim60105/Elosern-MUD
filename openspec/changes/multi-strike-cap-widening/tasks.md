## 1. Preparation (verify shipped state at the apply-time tip)

- [ ] 1.1 Re-confirm against current source (codegraph/LSP): `DamagePolicy.__post_init__`'s `(0, 1)` membership rejection, boolean rejection, `unknown repeat_when` rejection, the `repeat_when ⟹ == 1` pin, `__init__`'s normalization; `combat.py` `_handle_damage`'s `extra` leg, `total_strikes = 1 + …`, the `for _ in range(total_strikes)` loop, the per-strike divert ledgers, the `marked` dedup + single post-loop `knocked_out_mark`; and the wind `gale_dance_strike` shipped row (`DamagePolicy(extra_strikes=1)`).
- [ ] 1.2 Confirm `.github/evennia-shards.json` current content before appending (wave siblings also append).

## 2. Validation widening (skill-effect-model delta)

- [ ] 2.1 `world/skills/effects.py`: the membership set `(0, 1)` → `(0, 1, 2)` with the error naming the closed set; docstring's two-shape block gains the N-scope sentence (evidence-conditional stays exactly one; predicate-free admits one or two; total = 1 + N). Every other validation byte-unchanged.

## 3. Consumption confirmation (expected zero textual change)

- [ ] 3.1 Run the shipped strike suites unchanged (evidence-conditional + unconditional wind scenarios verbatim). Any failure here is a latent loop defect — fix minimally inside `_handle_damage`'s strike loop (this change owns that hunk per the Batch note) and record the defect in the PR body.

## 4. Tests (synthetic rows only; zero data-catalog tests)

- [ ] 4.1 In-file: the out-of-cap rejection test re-homed — `extra_strikes=2` (no predicate) constructs; 3, boolean, non-int, and every `repeat_when`-count≠1 combination still raise verbatim.
- [ ] 4.2 New focused module (register in `.github/evennia-shards.json`): three-strike settlement on a synthetic skill — fixed-seed 3-roll count/order across hit/mix sweeps; once-paid resources/practice; ordered HP projection; three-strike divert cap/gauge ledger discipline; ONE knockout mark and one defeat credit across a lethal 3-sweep (protected and unprotected); full rollback of all three pendings on a later commit failure.
- [ ] 4.3 Run ONLY the touched modules — no project-wide suite.

## 5. Census / hygiene

- [ ] 5.1 Grep census: zero shipped rows use `extra_strikes=2` at ship time; wind row and every shipped evidence scenario unchanged (`git diff --stat` proof).
- [ ] 5.2 `openspec validate multi-strike-cap-widening --strict` green.
