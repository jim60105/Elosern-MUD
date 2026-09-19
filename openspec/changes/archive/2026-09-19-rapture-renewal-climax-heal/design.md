## Context

See proposal.md — Why. The mechanism this design attaches to:

- `_apply_climax_phase_set(entity, phase)` is the canonical phase writer. It no-ops on any edge outside its valid-transition set, and it is what `apply_pleasure_gain()` calls to walk 未達 → 接近 → 進行中.
- `dispatch_phase_reaction(entity, from_phase, to_phase)` fires **once per canonical phase change** and builds a context carrying `entity`, `field`, `climax_phase` (= `to_phase`), `from_phase`, `to_phase` and `active_buffs`. Its docstring already requires callers to run inside a snapshotting transaction.
- Its executor currently handles exactly two actions, `apply_buff` and `remove_buff`.
- `skill_qualified` is already in `schema.py`'s recognized `when` vocabulary and resolves by reading `context["entity"]`, fetching its `skills` handler and calling `can_use_skill`. The phase context supplies `entity`, so the condition works in a phase rule today with no schema change.
- The two-step gate matters here: the gain that pushes pleasure past the 極限 floor sets 接近; the *next* gain sets 進行中. So the rule keys on entry to 進行中, which is the single moment the lore calls "兌現".

## Goals / Non-Goals

**Goals:**

- Once per climax, guaranteed by the dispatcher's transition semantics rather than by a bookkeeping flag.
- The magnitude is rulebook data.
- The heal can never produce more HP than was lost, so no arousal source turns the loop into a generator.

**Non-Goals:**

- No change to the climax state machine, its reset value, its SP cost, its action lock, or `priestly_grace`. No new `when.event` value.

## Decisions

### D1. Hook the phase dispatcher, not the outcome dispatcher

The alternative was a new `climax_started` value in the closed `when.event` vocabulary, dispatched from `apply_pleasure_gain()`.

Rejected because the phase dispatcher **already** provides exactly the semantics required, for free: it is called from the canonical phase writer, it fires on transitions rather than states, and `_apply_climax_phase_set` already refuses invalid edges — so "once per climax" is a property of the existing machinery, not something this change has to enforce. Adding an event would introduce a second path into the same moment and leave two places that could disagree about when a climax started.

### D2. Reuse the shipped phase-rule condition shape; no new condition vocabulary

The rule reads `when: {field: climax_phase, equals: 進行中, skill_qualified: rapture_renewal}`.

Both keys are already in `_RECOGNIZED_WHEN_KEYS`; `to_phase` is **not**, despite the phase dispatcher placing it in the evaluation context, so authoring against it would fail at load. The shipped `climax_in_progress_empowerment` rule already expresses exactly this trigger with `field: climax_phase, equals: 進行中`, and it is equivalent to a transition test because `dispatch_phase_reaction` builds its context with `climax_phase = to_phase` and is only ever called on a real transition. Copying that rule's shape means this change adds no condition vocabulary at all.

Using `skill_qualified` for the ownership half keeps the semantics (including how a disguised or conferred skill resolves) identical to `pain_to_pleasure`'s gate, rather than inventing a parallel notion of "has the passive".

### D3. The magnitude is a max-HP fraction in the rulebook

`self_heal_max_fraction: 0.5` in the rule, `floor(max_hp × fraction)` in the engine, validated at load as a finite number in `(0, 1]`.

The fraction belongs in data for the same reason `pain-to-pleasure-hp-scaling`'s coefficient does: these two numbers are a matched pair — 140 and 0.5 are derived from each other so the loop nets to zero — and a balance pass will want to move them together, from data, without a code edit. Expressing it as a *fraction of max HP* rather than a flat amount is what keeps the pairing scale-free across characters of wildly different HP.

### D4. Clamp to the HP gap; never revive

The heal is `min(floored_amount, max_hp − current_hp)`, and it is skipped entirely when current HP is at or below zero.

The clamp is the load-bearing balance constraint, not a defensive nicety. Sensitivity multipliers, shame multipliers, equipment `pleasure_gain` and ordinary sexual stimulus all accelerate the arousal ramp. Without the clamp, a clergy who reached climax having lost only 10% of their HP would still bank 50%, and every one of those accelerators would become a net HP faucet. With it, the accelerators make the loop *turn faster* but can never make it *yield more than was lost* — which is precisely the property the lore page claims.

### D5. The trigger is source-agnostic, by decision

The payout keys on entering the in-progress climax phase and asks nothing about where the arousal came from. A clergy who reaches climax through out-of-combat intimacy is healed exactly as one who was beaten into it.

This was reviewed and **kept deliberately**. The alternative, requiring that some of this climax's arousal originated from `pain_to_pleasure`, needs a per-climax provenance flag written on every pleasure gain and cleared on every reset: new persistent state, a new write on the hottest path in the sexual system, and a new way for the two passives to disagree. That is a large mechanism to buy a restriction the costs already impose.

What the clergy actually pays for an out-of-combat top-up is the climax's own shipped price: the SP charge at `sp_cost_on_climax` (20 to 30), the action lock while in-progress, the world-clock time to climb 70 pleasure points, and the high-arousal agility and accuracy penalty carried throughout the climb. The payout is still clamped to missing HP (D4), so this cannot manufacture HP, only recover it more slowly and more expensively than a dedicated heal would.

So the passive is two things at once, on purpose: the damage loop's third leg, and a costed out-of-combat recovery option available to the archetype whose whole identity is turning arousal into restoration. The spec pins this as contract rather than leaving it as an unstated consequence.

### D6. The transaction surface must be verified, not assumed

The phase dispatcher's callers snapshot buff state because, until now, buffs were all it wrote. This change makes it write HP, so the enclosing snapshot has to cover HP for the spec's rollback scenario to hold.

`damage-state-feedback` already requires that a failed settlement restores "HP, negative buff state, pleasure, phase, counters and marker" together for the *outcome* cascade, so the machinery exists; what needs checking is whether every caller of the **phase** dispatcher sits inside a face with the same coverage. This is called out as an explicit verification task rather than an assumption, because it is the one place this change could silently violate an existing requirement.

## Risks / Trade-offs

- **The phase dispatcher gains a non-buff side effect.** → Contained: one new action key, validated at load, executing one clamped write. But it does change the dispatcher's character from "buff marker plumbing" to "state-transition effects", which is worth knowing when the next action is proposed for it.
- **Shipping this without `pain-to-pleasure-hp-scaling` grants sustain on the old ramp.** → No code dependency, but a real balance one. Under the retired tier table a clergy needs ~14 ordinary hits to climax, so the heal would be rare rather than broken; still, the two are designed as a pair and should land together.
- **A character with no `sexual` handler never triggers it.** → Correct by construction: no handler means no climax phase means no transition. Monsters and NPCs without the state are unaffected.
- **The source-agnostic trigger makes this an out-of-combat heal too.** → Accepted as explicit design (D5) and pinned in the spec. Worth restating for balance passes: a clergy can convert SP and time into HP outside combat, bounded by the HP-gap clamp. If out-of-combat sustain ever needs tightening, the lever is the authored fraction or the climax SP cost, both data.
- **The census test in `test_skill_registry.py` must be updated in the same commit.** → Otherwise the registry import succeeds and the suite fails on a stale key set. Listed as its own task.

## Open Questions

None. The passive's key, label, category, element and the 0.5 fraction are all ratified in `docs/lore/skill-trees/light.md` §聖職者循環的數值平衡 and `docs/lore/skill-trees/enhancement.md`.
