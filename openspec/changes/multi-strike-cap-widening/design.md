## Context

Shipped state at master 06b68fef, verified in source:

- Validation (`world/skills/effects.py`): `DamagePolicy.extra_strikes` normalization `extra_strikes = 1 if repeat_when is not None else 0` (:535); `__post_init__` rejects non-int/boolean counts (:667-670), rejects `extra_strikes not in (0, 1)` (:671-674), and pins `repeat_when ⟹ extra_strikes == 1` (:675-678).
- Consumption (`world/rules/combat.py` `_handle_damage`): the `extra` eligibility leg (:361-368) — evidence lookup runs only when `repeat_when` is set, an unconditional policy always qualifies; `total_strikes = 1 + damage_policy.extra_strikes if extra else 1` (:369); `for _ in range(total_strikes)` (:373) — per-strike `roll_d100()`, per-strike multiplier/attack/predicate/defense/max-HP computation, per-strike divert planning against the `planned_cap_spend`/`planned_gauge_spend` ledgers, one `PendingEffect` + divert pendings per strike; the `marked` dedup list + the single post-loop `knocked_out_mark|<key>` battlefield effect (:550-564). The loop ALREADY generalizes over `total_strikes`; only the validation constant caps it.

The node-data consumer (lightning.md): thunder_combo 「2.0，多段傷害（連續三次判定）」 = 3 total = `extra_strikes = 2`.

## Non-Goals

- No change to `repeat_when`'s shape (evidence-conditional stays exactly-two), no new evidence kinds, no `repeat_mode` enum, no per-strike coefficient variation, no element keys, zero live rows (`thunder_combo`'s policy is the catalog's data). No touch on the wind `gale_dance_strike` row or the shipped evidence tests' scenarios. No N>2: the closed set is the smallest superset covering the ONLY authored triple in all eight trees — a wider cap is vocabulary nobody priced.

## Decisions

### D1 — Closed set {0, 1, 2}; `extra_strikes` keeps ADDITIONAL semantics

The widened membership test is `(0, 1, 2)`. Alternative considered: reinterpret the field as TOTAL strikes (`extra_strikes=3` = three total) — rejected: it breaks every shipped pin (wind's `gale_dance_strike(extra_strikes=1)`, the `repeat_when ⟹ == 1` rule, the normalization, four scenario wordings) to rename nothing the lore cares about; ADDITIONAL semantics make the delta one literal plus error wording. Why cap at 2 and not 3+ / unbounded: the ratified pre-release discipline (no speculative headroom) — every authored 多段 row across the eight lore trees is 兩次 or 三次; N>2 would demand re-deriving the single-terminal-emission proof surface for untested counts. Re-opening the set later is a one-literal superset delta.

### D2 — `repeat_when ⟹ extra_strikes == 1` stays verbatim

The evidence-conditional shape is the light `penitent_touch` / wind-counter family; no authored row wants a 3-strike evidence gate, and widening it would multiply the evidence-matrix test surface for zero priced demand. The pin also stays cap-compatible (1 ∈ {0,1,2}) — the shipped rejection needs no rewording.

### D3 — Consumption is confirmation-only; the terminal-emission invariant is the delta's test payload

`combat.py` textually does not change: `total_strikes = 1 + extra_strikes` and the loop already compute N=3. The widening's real risk is a latent N>1 defect, so the requirement pins and the tests target exactly the surfaces a loop generalization can leak: (a) roll COUNT and ORDER per strike (fixed-seed); (b) once-paid payment/practice (shipped single-payment path — assert it holds for a 3-sweep); (c) ordered HP projection (strike 2 sees post-strike-1 HP at commit ordering); (d) diversion ledgers across three strikes (cap not double-spent per strike); (e) ONE terminal emission per target regardless of N — the `marked` list's `if key not in marked` dedup plus the single post-loop mark effect is the shipped mechanism; the test asserts one knockout mark for a 3-hit lethal protected sweep; (f) atomic rollback of all three pendings. If any test exposes a genuine defect, this change owns the minimal `_handle_damage` fix (declared hunk-disjoint from `turn-order-control`'s `run_round` hunks).

### D4 — Validation surface

`extra_strikes=2` with `repeat_when=None` constructs; `extra_strikes=3`, booleans, non-ints, and any `repeat_when` count ≠ 1 still raise verbatim; the error message wording updates to name the closed set. The dataclass is frozen with `__post_init__` validation — no parser/grammar change (`DamagePolicy` is authored through `EffectPolicy`, not an effect-ID string), so `parse_effect` is untouched.

## Risks / Trade-offs

- **Golden-seed drift:** fixed-seed wind/evidence tests consume exactly 2 rolls per multi-strike cast; an unconditional `extra_strikes=2` row ships only in the catalog, so every shipped golden consumes identical roll counts. No golden edit expected; if one drifts it signals the loop consumes a roll it shouldn't (defect, see D3).
- **Roll-order coupling with `turn-order-control`:** both changes touch dice consumption in combat but in disjoint functions (provider-call slots vs strike rolls); a round with BOTH an extra action and a 3-strike cast consumes 2 provider calls × their own strike rolls — priced, testable, and owned by the catalog's behavior module, not this grammar change.
