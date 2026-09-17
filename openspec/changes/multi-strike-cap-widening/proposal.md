## Why

The lightning tree prices 雷霆連擊 thunder_combo at 「2.0，多段傷害（連續三次判定）」 — three strike resolutions per cast — but the shipped multi-hit vocabulary caps at two. `DamagePolicy.extra_strikes` is validated into `{0, 1}` (`world/skills/effects.py:671-674`, the unconditional-multi-strike wave's own pin: 「`extra_strikes not in (0, 1)` raises」), while every machinery the third strike needs is already shipped and generic: `combat.py:369` computes `total_strikes = 1 + damage_policy.extra_strikes` and the settlement is a real `for _ in range(total_strikes)` loop (`combat.py:373+`) with per-strike independent `roll_d100()`, per-strike ordered damage staging, per-strike divert planning, and ONE terminal knockout-mark emission per target assembled after the loop (`combat.py:550-564`). The cap is a validation constant around a loop that already generalizes — the same posture the wind wave took when it opened the conditional-only shape to `extra_strikes=1` (archived `2026-09-17-unconditional-multi-strike`). Future elements' flurry nodes (any element's triple-hit) ride the same widening.

## What Changes

- **Batch declaration.** This change lands SECOND in the lightning wave (after `turn-order-control`); the data-only `lightning-spell-catalog` follows per `## Batch` with machine-readable `depends-on:` lines and the combat.py hunk-sequencing note.
- **MODIFIED strict-superset delta on the shipped follow-up-strike requirement:** the extra-strike count widens from the `{0, 1}` closed set to `{0, 1, 2}` (total strikes = 1 + N, so thunder_combo's 「連續三次判定」 authors as `DamagePolicy(extra_strikes=2)`). `extra_strikes` keeps its ADDITIONAL-strikes semantics verbatim; the `repeat_when ⟹ extra_strikes == 1` pin stays verbatim (the evidence-conditional shape remains exactly two strikes — no shipped or planned evidence rule wants three); the unknown-evidence-kind and boolean-count rejections stay verbatim; `__init__`'s normalization (`extra_strikes = 1 if repeat_when else 0`) stays verbatim. No new field, no enum, no `repeat_mode`.
- **The settlement inherits the loop verbatim.** `total_strikes = 1 + extra_strikes` and the existing `for _ in range(total_strikes)` already compute N>1 correctly — the widening's behavioral content is the INVARIANTS re-pinned at N=2 by requirement + test: each of the 1+N strikes independent-rolls with the same coefficient/policy; no strike's miss suppresses any later strike; resources/time paid and practice awarded ONCE per cast; ordered HP projection across all strikes; per-strike divert planning with the shipped cap/gauge ledgers; AT MOST ONE terminal defeat/knockout emission per target per cast regardless of N (the single post-loop `knocked_out_mark` effect + the `marked` dedup list are the shipped mechanism — pinned, not rewritten); atomic rollback across all N pending strikes; nonlethal flooring across the whole sweep.
- No element keys, no new evidence kinds, no changes to the wind `gale_dance_strike` row or any shipped data. This change ships ZERO live rows — inert-but-valid grammar (the unconditional-multi-strike precedent); `thunder_combo`'s three-strike policy is `lightning-spell-catalog` data.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-effect-model`: the requirement 「A follow-up strike repeats damage on evidence or unconditionally without repeating the action」 is MODIFIED to a strict superset — the extra-strike declaration widens from one to two extra independent strikes, keeping every shipped guarantee verbatim (independent rolls, once-paid action, ordered projection, single terminal emission per target, atomicity, the evidence-conditional shape pinned at exactly one extra strike); the sole changed rule is the `{0,1}` construction cap → `{0,1,2}`. Canonical ID `skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action`.

## Impact

`world/skills/effects.py` (`DamagePolicy.__post_init__` — the membership set `(0, 1)` → `(0, 1, 2)` and the error wording; docstring: 「may be configured in two shapes」 gains the N-scope sentence; every other validation untouched). `world/rules/combat.py` — expected ZERO textual change (the loop already generalizes); implementation CONFIRMS by test, and only if a test exposes a latent N>1 defect does this change own the fix in `_handle_damage`'s strike loop. `world/rules/tests/test_action_evidence.py` / `test_conditional_damage.py` in-file updates (the out-of-cap rejection test re-homed: 2 now constructs, 3 still raises; every wind scenario verbatim); new N=3 behavior module registered in `.github/evennia-shards.json`.

Sequencing: `effects.py` is this change's alone. `combat.py` is SHARED with `turn-order-control` — this change expects zero hunks there (confirmation-only); if a latent defect forces a `_handle_damage` edit, it sits ~400 lines from `turn-order-control`'s `run_round` hunks — textually disjoint, supervisor sequences the merges per the declared queue.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.

## Batch

- depends-on: turn-order-control
  (code conflicts: none functional — queue position declared for `combat.py` hunk sequencing: `turn-order-control` edits `run_round()` ~895-940; this change expects no `combat.py` hunk at all, and any defect-fix hunk would land in `_handle_damage()` ~361-578, textually disjoint, either order applies cleanly. `.github/evennia-shards.json` — both append one test module each; manifest edits sequence under supervisor. Otherwise file-disjoint: this change owns `world/skills/effects.py` and the two existing strike-test modules.)
- `lightning-spell-catalog` depends on this change and authors `thunder_combo`'s `DamagePolicy(extra_strikes=2)` policy data over the grammar shipped here.
