## Context

The approved brainstorming design for this work is
`docs/superpowers/specs/2026-09-10-field-combat-initiation-design.md`; this
change implements its §5 primitives only (D-2 and D-5), leaving every rewiring
decision to the two follow-up changes.

Current state:

- `world/rules/combat.py::run_round()` iterates `roll_initiative(battlefield)`,
  an agility-dominant score plus a `roll_d100()` jitter, sorted descending with
  the roster key as the tie-break. There is no way for a caller to say who acts
  first.
- `world/rules/overwhelm.py::resolve_overwhelm()` loops `run_round()` up to
  `max_rounds`, recomputing `classify_overwhelm()` after every round, and
  compresses the collected logs. It already threads several keyword-only policy
  flags (`simulated`, `nonlethal_keys`, `journal_sink`, `notifications_sink`)
  through `_resolve_overwhelm_raw()`.
- `overwhelm.py` already imports `SKILL_REGISTRY` for its compressed
  commanded-action marker, so the damage query needs no new dependency.
- `"damage"` is the only HP-damage effect handler in the project
  (`world/rules/combat.py:349`), registered against the `traits` surface.

Constraint from `AGENTS.md`: `world/rules/` is part of the deterministic
single-writer core, and the project has no released users, so a
forward-declared seam with guarded tests is preferred over any compatibility
shim.

## Goals / Non-Goals

**Goals:**

- Give one round an externally chosen first actor, without touching how
  initiative is computed.
- Give callers a pure, cheap, deterministic answer to "does this commanded
  action damage an enemy".
- Keep every current caller's behaviour bit-identical, so this change is
  provably inert on its own.

**Non-Goals:**

- Any change to who dispatches `resolve_overwhelm()`. The ordinary loop still
  compresses encounters after this change; removing that is
  `combat-session-opening-dispatch`.
- Any change to `classify_overwhelm()`'s verdict logic. The new query is not
  called from inside it.
- Any exploration-side entry point, command routing, or reject reason.
- Any change to the skill registry's `usable_out_of_combat` values.

## Decisions

**D-1. First strike reorders the rolled sequence; it does not re-roll or
re-score.** `run_round()` calls `roll_initiative()` exactly as today, then
moves `first_actor` to index 0 of the returned list, preserving the relative
order of everyone else.

Alternatives rejected:

- *Give the actor a temporary agility buff.* Rejected because it is not a
  guarantee — a high-agility monster could still win the roll — and because it
  would leak into `evaluate_combat_modifiers()`, `effective_power()`, and
  therefore into `classify_overwhelm()`'s own verdict.
- *Bypass `roll_initiative()` for the whole round.* Rejected because the
  remaining combatants' order should stay agility-driven; only the opener is
  privileged.
- *Resolve the opening action outside the round, then run a full round.*
  Rejected in brainstorming (D-5): it hands the player an extra action and
  forces a separate time-cost accounting.

The override is applied after the liveness filter that `roll_initiative()`
already performs, so naming a dead, fled, or knocked-out key simply has no
effect — the key is not in the sequence to move. Naming a key absent from the
roster likewise does nothing. Both are silent no-ops rather than errors,
because `run_round()` is on the hot path of every combat and must not raise on
a stale key.

**D-2. `resolve_overwhelm()` forwards `first_actor` to round one only.**
`_resolve_overwhelm_raw()` already special-cases `rounds == 0` to capture the
round-one log window for the commanded-action marker; the same condition gates
the forward. Later rounds pass `None`.

Rationale: the privilege belongs to the *opening*, not to the whole compressed
encounter. Forwarding it every round would silently make the player act first
for up to `max_rounds` rounds, which no requirement asks for and which would
make the compressed path diverge from the equivalent manual `run_round()` loop
that `single-shot-resolution` already pins with an equivalence contract.

**D-3. The existing keyword-forwarding discipline is preserved.**
`resolve_overwhelm()` currently forwards its policy flags to `run_round()`
*only when they differ from the defaults*, so default-mode callers observe the
pre-change call signature byte-identically (`fix-dot-kill-credit` D4).
`first_actor` follows the same rule: when it is `None`, the call into
`run_round()` is unchanged.

**D-4. The damage query is static and concrete-target-only.**
`commanded_damage_reaches_enemy()` reads
`SKILL_REGISTRY.get(skill_key).effects` for a `DamageEffect` instance and
intersects the supplied target keys with the team opposing `actor_key`. It
takes concrete roster keys; resolving an AREA shorthand is the caller's job,
because the caller (a session facade or the field entry) is the only layer that
knows which shorthand was approved.

Alternatives rejected:

- *Include indirect HP movement (`SexualDrainEffect`).* Rejected: that effect
  moves the target's pleasure into the caster's own pools; treating it as
  damage would make a sexual act eligible for one-shot settlement, which
  contradicts the brainstormed intent.
- *Simulate the action and check for non-zero damage.* Rejected: damage
  magnitude depends on a `roll_d100()` to-hit, so "will it damage" has no
  deterministic answer, and the query must stay side-effect free.

An unknown `skill_key` returns `False` rather than raising, so the query is
safe to call before any registry validation has run.

**D-5. The query lives in `overwhelm.py`, not in `targeting.py` or a new
module.** It is a precondition of overwhelm classification and nothing else,
and `overwhelm.py` already owns the pure-query discipline plus the
`SKILL_REGISTRY` import. Putting it in `world/skills/` would invert the
project's dependency direction (`world/rules/` depends on `world/skills/`,
never the reverse) because it needs `Battlefield` team membership.

## Risks / Trade-offs

- **[The seam has no production consumer when this change lands.]** →
  Deliberate, and permitted by `AGENTS.md`'s forward-declared-seam rule. Both
  additions are covered by their own tests, and the inertness is itself
  asserted: existing callers must produce identical results with the new
  parameters defaulted.
- **[`first_actor` could be mistaken for "acts twice".]** → The requirement
  and the docstring state reorder-only explicitly, and a test asserts the
  round still contains exactly one action per capable combatant.
- **[Reordering could accidentally drop or duplicate a key.]** → Covered by a
  test asserting the returned order is a permutation of the un-overridden
  order, with the named key first and the remaining relative order preserved.
- **[A future caller may pass an AREA shorthand to the damage query.]** → The
  signature accepts only a tuple of concrete keys and the requirement says so;
  a shorthand string would simply fail to intersect the enemy team and return
  `False`, which is the fail-closed direction (no one-shot settlement).
- **[Extending existing test modules keeps `.github/evennia-shards.json`
  untouched, but a new module would need registering.]** → Prefer extending
  `world/rules/tests/test_overwhelm_threshold.py` and the existing round-loop
  tests; if a new module is unavoidable, register it in the same change.
