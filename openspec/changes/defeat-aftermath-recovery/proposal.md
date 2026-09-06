# Proposal: DA2 — defeat-aftermath-recovery

Change ID: **DA2** (parent design §8 archive order).

## Why

`defeat-aftermath-core` leaves the defeated player waking at HP 1 —
playable but incomplete. The owner-approved design
(`docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md` §3.1 step 5)
prices defeat in world time: the clock advances until HP reaches exactly
`ceil(max_hp × 0.05)`, computed from the stored regen model and the
rulebook defeat scale — the mechanic that kills the zero-cost
lose→rest→refight loop, because the time tax is paid at settlement, not by
walking to a safe room. The arithmetic is risky (integer HP + float
remainder, overshoot, clock side effects), so it is isolated here with its
own battery.

## What Changes

- **Recovery advance phase** appended to the core's aftermath order (same
  `settle_session` transaction): the aftermath computes the minimum
  non-negative integer seconds `t` such that the stored gauge-regen model
  (`world/rules/clock.py` semantics: integer HP gain per interval with a
  carried float remainder, rate scaled by the rulebook `recovery` section's
  defeat scale while `defeat_weak` is mounted) first reaches or exceeds
  `ceil(max_hp × 0.05)`; it advances the world clock once by `t` with
  source `defeat_aftermath`, then performs a clamp write pinning HP to
  exactly the target — the wake state never sits above the target, and
  within the final interval HP may land on or above it before the clamp.
- Edge semantics: player already at/above target → `t = 0`, no advance, no
  clamp; an unreachably large `t` beyond the rulebook `max_recovery_seconds`
  → cap at the ceiling, settle at the HP the capped advance produces, and
  emit a `log_error` facade event (never silently truncate).
- **`recovery` section** in `rulebook/defeat_aftermath.yaml` with its own
  section validator registered through the core's per-section loader
  (forward-compat seam).
- **Clock side-effect battery**: advancing through the recovery window may
  legitimately fail a quest deadline, cross a gauge daily decay/reset
  boundary, restock a merchant, or expire a buff — the test manifest
  enumerates these as clock-caused; anything else is a contract failure.
- **Rollback-injection tests** for the phase (advance + clamp + EventLog
  `recovery_advance` commit or vanish together) and the
  **retained-winner route smoke**: defeat a quest-bound winner, move to an
  adjacent room, `skip`/rest succeeds there.
- **BREAKING** (settlement semantics, no released users): the core
  capability's declared-write list and the wake-state expectations gain the
  recovery phase; the core's "wake at 1" intermediate behavior is replaced.

## Capabilities

### New Capabilities

- `defeat-aftermath-recovery`: the 5% recovery advance — minimum-seconds
  solve against the stored regen model, the rulebook defeat regen scale,
  the exact-target clamp, the clock side-effect contract, and the
  bounded-failure edge.

### Modified Capabilities

_None._ The capability `defeat-aftermath-core` is this family's own new
capability and does not exist in `openspec/specs/` until it archives
(recovery archives immediately after it, parent design §8), so the extended
contract — the recovery phase's declared writes and the wake-at-target
settlement outcome — is expressed as ADDED requirements of
`defeat-aftermath-recovery`, whose scenarios supersede the core's interim
"wake at 1" expectation in the synced main specs.

## Impact

- `world/rules/defeat_aftermath.py` (recovery phase beside the core
  writer), `world/rules/rulebook/defeat_aftermath.yaml` (`recovery`
  section + validator).
- No changes to `world/rules/clock.py` — the solve and clamp are aftermath
  math over the shipped regen model; the clock itself is called through its
  normal advance entry point with a source tag.
- Tests: extends `world/rules/tests/test_defeat_aftermath_core.py`'s
  battery with the recovery manifest rows + new recovery module tests;
  shard manifest unchanged (same modules).
- Depends on `defeat-aftermath-core` (archives immediately after it per
  parent design §8). Blocks nothing.
