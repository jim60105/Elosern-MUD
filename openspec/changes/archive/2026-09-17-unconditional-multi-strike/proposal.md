## Why

The wind tree prices 疾風刃舞 gale_dance_strike at 「2.0，多段傷害（連續兩次判定）」 — two strike resolutions per cast with NO precondition — but the shipped multi-hit vocabulary is locked to a condition: `DamagePolicy.extra_strikes` may be non-zero ONLY together with `repeat_when`, and `repeat_when` accepts exactly one evidence kind (`forced_interaction`, the light `penitent_touch` shape). 「連續兩次判定」 with no condition is inexpressible at master 9ca95ba even though the entire settlement machinery it needs — two independent hit rolls, ordered HP projection, single terminal defeat/knockout emission, one payment/practice per cast, atomic rollback — is shipped and covered (`world/rules/tests/test_action_evidence.py`). Future elements' 多段 nodes (any element's flurry/multi-hit) ride the same seam, so the fix is generic vocabulary, not a wind branch.

## What Changes

- **Batch declaration.** This change lands SECOND in the wind wave (after `displaced-knockback`); `wind-spell-catalog` follows per `## Batch` below with machine-readable `depends-on:` lines and combat.py hunk-sequencing notes.
- Open the `DamagePolicy` authoring grammar with a strict-superset MODIFIED delta on the shipped conditional-follow-up-strike requirement: an extra-strike count may now be declared WITHOUT a `repeat_when` predicate — `DamagePolicy(extra_strikes=1)` constructs and means 「always resolve the extra strike」 (design D1 retires the single rejection rule 「extra_strikes > 0 requires repeat_when」; the `extra_strikes ∈ {0,1}` cap, the `repeat_when ∈ EVIDENCE_KINDS` validation, and the 「repeat_when ⟹ extra_strikes == 1」 pin all stay verbatim; no new field, no `repeat_mode` enum).
- The settlement consumes the widened vocabulary through ONE boolean leg in the existing `_handle_damage` extra-strike computation: the evidence lookup runs only when `repeat_when` is set; an unconditional policy always takes the shipped dual-strike loop — independent rolls, same coefficient/policy per strike, ordered HP projection, at most one terminal defeat/knockout, single payment/practice, nonlethal flooring, atomic rollback — every guarantee the conditional sibling's requirement pins, inherited verbatim (`total_strikes = 1 + extra_strikes` replaces the hard-coded 2/1; identical while the cap holds).
- No element keys, no second rules engine, no new evidence kinds, no `extra_strikes > 1`. This change ships ZERO live rows — the `gale_dance_strike` policy is `wind-spell-catalog` data — inert-but-valid vocabulary, exactly the `terrain-marker` precedent.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-effect-model`: the requirement 「A conditional follow-up strike repeats damage without repeating the action」 is MODIFIED to a strict superset — a validated damage policy may declare the extra strike unconditionally (no evidence predicate), keeping every shipped guarantee (independent rolls, once-paid action, ordered projection, single terminal emission, atomicity); every evidence-conditional scenario stays verbatim, and the sole retired rule is the construction rejection of `extra_strikes` without `repeat_when`.

## Impact

`world/skills/effects.py` (`DamagePolicy.__post_init__` — retire one rejection + docstring; `__init__` normalization unchanged); `world/rules/combat.py` (`_handle_damage`'s extra-strike computation hunk, ~lines 360-366 — one boolean leg + the `total_strikes` arithmetic; disjoint from `displaced-knockback`'s `default_attack_policy` filter in the same file ~400 lines away — the supervisor sequences the two merges — `displaced-knockback` first per the declared queue; either order applies cleanly); `world/rules/tests/test_conditional_damage.py` / `world/rules/tests/test_action_evidence.py` in-file updates (the retired rejection's test replaced by the acceptance behavior; every other pin verbatim); new focused behavior test module registered in `.github/evennia-shards.json` (rules-a; the wave's manifest appends sequence under supervisor); traceability ledger hygiene stays in the separately authorized main-sync. `openspec list --json` returned an empty change set at authoring time — no active-change file conflicts.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.

## Batch

- depends-on: (none functionally; queue position declared by the supervisor) displaced-knockback
  (code conflicts: `world/rules/combat.py` SHARED — this change edits `_handle_damage`'s extra-strike computation hunk; `displaced-knockback` edits `default_attack_policy`'s candidate filter, ~400 lines away, textually disjoint hunks, same file: the supervisor sequences the two merges — `displaced-knockback` first per the declared queue; either order applies cleanly (textually disjoint: `combat.py` ~360 vs ~767). `.github/evennia-shards.json` — both append one test module; manifest edits sequence under supervisor. Otherwise file-disjoint: this change owns `world/skills/effects.py` and the two existing strike-test modules.)
- `wind-spell-catalog` depends on this change and authors `gale_dance_strike`'s `DamagePolicy(extra_strikes=1)` policy data over the grammar shipped here.
