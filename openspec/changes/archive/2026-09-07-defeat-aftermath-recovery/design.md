# Design: defeat-aftermath-recovery

Parent design: `docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md`
§3.1 step 5 / §3.2 item 2 (scale half).

## Context

`_settle_gauge_regen` (`world/rules/clock.py:170`) stores HP integrally
with a carried float remainder: after advancing `elapsed` seconds,
`current = floor(current + carried + rate × elapsed)` (or the max clamp).
The recovery solve must respect that exact model — demanding "exactly 5%
by interval arithmetic" is wrong when one interval overshoots, and a pure
`t = (target - hp) / (rate × scale)` division silently under- or
over-shoots around the floor.

## Goals / Non-Goals

**Goals:**

- Wake at exactly `ceil(max_hp × 0.05)` via a minimum-seconds solve over
  the stored model + one clamp write, inside the settlement transaction.
- The rulebook `recovery` scale section through the core's per-section
  loader; bounded-failure edge; clock side-effect manifest; rollback tests;
  the retained-winner move-and-rest smoke.

**Non-Goals:**

- No clock-engine changes (no new regen model, no per-entity rate override).
- No violation/digest behavior. No `skip_safety` changes (the refusal is
  the point).

## Decisions

**D-R1: Solve, then one advance, then clamp — no tick-by-tick loop.**
The aftermath computes the smallest non-negative integer `t` with
`floor(current + carried + scaled_rate × t) ≥ target` (closed form with an
integer-search guard at the boundary; `t = 0` when already at/above),
advances the world clock once by `t` with source `defeat_aftermath`, then
clamps HP down to exactly `target` if the tick overshot. This preserves the
clock's own semantics for every OTHER entity in scope during the window
(companions regen normally) while the player's wake value is pinned. A
clamp is a declared aftermath write, not a regen side effect.
- Rejected alternative: advancing interval-by-interval until HP ≥ target —
  re-implements the clock loop in the aftermath and cannot express "never
  above target" anyway.
- Rejected alternative: bare division — lands wrong whenever the floor
  crosses mid-interval; the spec's arithmetic is the model itself.

**D-R2: The scale is settlement math, not a buff effect.**
The buff engine's `rate` modifier is an absolute per-interval delta
(`world/rules/buffs.py`); a scale-shaped regen tax would be a new effect
kind. The tax is instead a time multiplier inside the solve: `t` is the
minimum whole seconds for the *virtual* scaled-rate model
(`stored_rate × recovery.regen_scale`, scale < 1) to first reach the
target, while the clock's real advance runs the ordinary un-scaled model —
so the world pays the long window and the player's actual HP lands at or
above the target, and the clamp write pins it to exactly the target. The
`defeat_weak` buff is the narrative handle the scale reads against; the
clamp is the standard path, not an exception. `world/rules/clock.py` is
never edited beyond the new `AdvanceSource.DEFEAT_AFTERMATH` vocabulary
member the spec's `source defeat_aftermath` requires — the regen model,
stage machinery, and snapshot semantics are untouched — and no entity's
stored rate is mutated. On the capped path the real un-scaled advance may
land above the virtual target, so the aftermath writes the player's HP
from the virtual scaled model at the cap (the same declared-write family
as the clamp; plan-review finding 1).

**D-R3: `max_recovery_seconds` bounds the pathological case loudly.**
Zero/tiny scale or a degenerate rate could make the target unreachable;
the solve returns the cap, the settle stops below target, and one
`log_error` facade event fires (`char`, `tick`, `target`, `capped`). Silent
truncation is forbidden — this is the observability rule for degradation.

**D-R4: The side-effect manifest extends the core's battery in place.**
The core's declared-write manifest test module gains recovery rows: for a
window crossing exactly one quest deadline + one restock boundary, assert
only those two causal mutations + the aftermath's declared writes
(advance, clamp, `recovery_advance` entry). The manifest stays code in
`test_defeat_aftermath_core.py` (D-C7), not a second battery file.

**D-R5: `recovery_advance` is the phase's EventLog kind.**
Open-vocabulary addition with its zh-tw template line (the wake line at
target HP), authored here; observability keeps the core's single
`defeat_aftermath` info event, widened context `{..., seconds, hp_wake}`.

## Risks / Trade-offs

- [The window can fail an active quest's deadline] → owner-approved world
  consequence; the manifest pins it as clock causality, not record erasure.
- [A very long `t` advances companions/rooms/merchants far] → same
  semantics as any long rest/skip; the clock is already the single writer
  of that machinery.
- [Clamp below a legitimate overshoot looks like HP damage] → it is one
  deterministic aftermath write with its own EventLog entry; nothing else
  can trigger it.
