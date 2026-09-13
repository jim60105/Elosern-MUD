## Context

See `proposal.md` — Why, and `docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §5.6.

Constraints that shape the approach:

- `_apply_pleasure_gain` is order-sensitive by construction: its first two statements must read
  pre-mutation state, and `sexual-act-effects` pins that with an implementation-inspection scenario.
  It cannot be "cleaned up" while being moved.
- It is already imported across a module boundary under its private name
  (`world/rules/defeat_aftermath.py:47`), so the "private to the cast pipeline" containment is
  fictional today; publishing it records reality rather than granting new access.
- `_zero_pleasure` (`world/rules/action.py:1380`) is a second existing direct writer of
  `entity.sexual.pleasure.base`. Any invariant phrased as "one function writes pleasure" is false
  before this change and would stay false after it.
- `world/rules/action.py` is 2341 lines and imports broadly. Anything a non-cast caller must reach
  cannot live there.
- `world/rules/buffs.py` already holds both grant-time guards (equipment immunity, `unique_per_source`
  source key) inside `_add_buff`. Publishing the function is the whole job; re-implementing the guards
  at a new seam would be the failure mode.
- `_remove_buff_keys` takes **instance** keys (`buff.buffkey`), while every caller thinks in
  definition keys. `cleanse_debuffs` already does the instance-key translation correctly; the new API
  must do it in the same one place.

## Goals / Non-Goals

**Goals:**

- One importable entry point per effect family, reachable without importing the cast pipeline.
- The instance-key/definition-key translation exists in exactly one function.
- Zero behavior change for every shipped caller.

**Non-Goals:**

- Any item work. This change touches no item file.
- Changing gauge writing. HP/MP/SP already have a single clean entry point in
  `world/rules/items.py::_write_gauge` and `world/rules/combat.py::_apply_heal`; unifying those two is
  a separate question this change does not answer.
- Generalizing `apply_buff` to take a duration override or a stacking override. Buff definitions own
  those.

## Decisions

### D1 — `world/rules/pleasure.py` as a new module, not `sexual_state.py`

*Why:* `world/rules/sexual_state.py` owns the pleasure **rulebook** (band table, multipliers,
validation). `apply_pleasure_gain` is a *writer*, and the rulebook module is imported by read-only
query surfaces that must not gain a transitive path to a state writer. A dedicated small module keeps
the writer/reader split visible.

*Alternative rejected:* keep it in `action.py` and have items import from there. That makes every item
use depend on the full cast pipeline import graph, and re-creates the coupling this change exists to
remove.

### D2 — Move the body unedited

`apply_pleasure_gain` is a pure rename plus relocation. No reordering, no extraction of the two
`_apply_climax_phase_set` calls, no signature change.

*Why:* the spec pins the first-two-statements ordering with a source-inspection scenario, and the
docstring records exactly which `sexual.yaml` rules it hand-replicates and why. A move that also
tidies is a move whose regressions are invisible in review.

*Note:* `_apply_climax_phase_set` does **not** move. It lives in `world/rules/sexual_state.py:853`,
is exported there, and is already imported by both `action.py:48` and `sexual_transitions.py:14`.
`sexual_state.py` imports nothing from `action.py`, so there is no circular-import risk;
`pleasure.py` simply imports it the same way its existing callers do.

### D2b — `zero_pleasure` moves too, and stays a separate function

*Why it moves:* it is the other direct writer of `entity.sexual.pleasure.base`. Leaving it behind
would make the module boundary meaningless and the structural test unwritable.

*Why it is not folded into `apply_pleasure_gain`:* zeroing through `apply_pleasure_gain(entity,
-current)` would run that function's `was_at_critical_point` branch, pushing a target sitting at 接近
into 進行中. Draining someone's pleasure to zero must not advance their climax phase. The two
writers have genuinely different semantics — one is a delta with an arousal-coupled cascade, one is a
forced reset with none — and the cascade is exactly what distinguishes them.

*Consequence for the invariant:* the checkable statement is "every write to
`entity.sexual.pleasure` lives in `world/rules/pleasure.py`", not "every write goes through one
function". The spec delta is written that way.

### D3 — `remove_by_selector` returns a count; `cleanse_debuffs` becomes a thin alias

*Why the count:* the item model's effectiveness test for a removal effect is "did anything actually
go", and the existing `item_used` event payload already carries a removed-count. Returning it from the
one function that knows means no caller re-counts.

*Why keep `cleanse_debuffs` at all:* it is the name the cleanse effect handler and the holy-water
settlement already use, and `cleanse-effect-handler`'s requirement is written around it. Re-expressing
it as `remove_by_selector(entity, "negative")` keeps both callers on one implementation while leaving
the shipped call sites untouched.

### D4 — Selector strings, not an enum, at this layer

*Why:* `world/rules/buffs.py` is a low-level module with no vocabulary of its own; an enum defined
here would have to be imported by the item rulebook loader, inverting the dependency (rules data
depending on a buff-module enum). The item loader validates its own closed vocabulary and passes a
plain string down. The removal function still fails closed on an unrecognized selector.

*Trade-off:* the string contract is checked at two layers rather than one. Accepted because the
alternative couples the item vocabulary to the buff module's import graph.

### D5 — The new selectors ship unused

`positive` and `all`, and concrete-key removal, have no caller until `add-declarative-item-effects`.

*Why ship them here:* `AGENTS.md` sanctions forward-declared seams, and the alternative — adding half
the API now and half later — means the selector vocabulary is defined across two changes and reviewed
in neither as a whole. Their tests land here, so the seam is exercised rather than merely declared.

### D6 — The rulebook engine and clock decay stay sanctioned pleasure writers; `_handle_cleanse` applies through the selector

*Why the pleasure invariant names a closed writer set, not one module:* two shipped deterministic
writers cannot route through `apply_pleasure_gain`/`zero_pleasure` without a behavior change this
behavior-preserving change must not make: `sexual_transitions._apply_then`'s `bounded_counter`
branch writes rulebook-declared delta/set effects (and reads the arousal-ordinal direction around
its own write), and `sexual_state.decay_tick` is a floor-relative decay step. The ADDED requirement
and its first scenario are therefore phrased as a closed set of sanctioned writers — the shared
module's two functions plus those two engine branches — and the structural test scans for exactly
that set (alias-aware, since both engine writers assign through a local `trait` binding, not
through a literal `entity.sexual.pleasure.` chain).

*Why the cleanse handler's `apply()` changes:* the `cleanse-effect-handler` delta's trace scenario
requires the `cleanse:status` effect to reach the same shared removal as every other clearing path.
`_handle_cleanse` keeps its stage-time selection (it owns the effect description and the
skip-when-empty check) but its staged `apply()` calls `remove_by_selector(target, "negative")`
instead of replaying a snapshot key tuple, so the polarity filter lives in one function. Every
shipped cleanse test passes unchanged.

## Risks / Trade-offs

- **The pleasure move silently reorders the pre-mutation captures** → move the body with no edits at
  all; the existing source-inspection scenario in `sexual-act-effects` is the automated guard, and it
  must be pointed at the new location as part of the same task.
- **A missed `_apply_pleasure_gain` call site** → there are six in production: three in `action.py`
  (`:964`, `:1103`, `:1104`) and three in `world/rules/defeat_aftermath.py` (`:926`, `:928`, `:1499`),
  plus nine in `test_sexual_act_effects.py`. After the move, `grep` for the old private name must
  return zero hits anywhere.
- **Circular import between `pleasure.py` and `action.py`** → the moved bodies reach only
  `sexual_state.py` (for `_apply_climax_phase_set`) and `_EFFECTS_CONFIG`. Verify `pleasure.py`
  imports nothing from `action.py`; if anything the moved bodies touch still lives in `action.py`, it
  moves as well rather than being imported back.
- **`remove_by_selector` given a definition key that is also a selector word** → the loader in the
  consuming change rejects a `buffs.yaml` definition named `all`, `positive`, or `negative`; add a
  startup assertion in this change so the collision can never be introduced later.
- **Merge conflict with `refactor-target-resolution-srp`** → both edit `world/rules/action.py`'s
  import preamble around `:48-58`. Logically independent, textually adjacent: sequence them rather
  than working both trees at once.

## Migration Plan

No data migration. Ships as one commit: the move, the two published functions, and the updated call
sites and tests. Rollback is a revert; nothing persisted changes.
