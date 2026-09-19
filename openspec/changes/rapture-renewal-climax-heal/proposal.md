## Why

`pain_to_pleasure` converts damage into arousal and `priestly_grace` converts arousal into stronger healing **for other people**. Nothing converts the clergy's own accumulated arousal back into their own survival, so the archetype documented in `docs/lore/skill-trees/light.md` — 「受傷換快感、快感換回復」 — is missing its third leg. In play the clergy currently pays the whole cost of the loop (a rising arousal gauge that inflicts agility −20% and accuracy −15 past the 高度 band, an action lock during climax, and an SP cost when it ends) and receives nothing back for themselves.

The companion change `pain-to-pleasure-hp-scaling` reprices the first leg so that losing half of maximum HP walks exactly one climax journey. That coefficient was derived specifically so a **50%-of-max-HP self-heal at climax** makes the loop net-zero on HP: the clergy gets back exactly what they bled, having paid for it in degraded combat performance, a lost turn and SP. Without this change that derivation has no counterpart and the loop is all cost.

## What Changes

- **New `ENHANCEMENT` passive `rapture_renewal`** (歡愉回生), `element="light"`, `TargetSpec.NONE`, empty cost, `group=None` — the same acquisition shape as its two siblings: story- or ordination-granted, never practised, never on a lineage tree.
- **The phase-reaction `then` vocabulary grows one action**: a self-heal expressed as a fraction of the recipient's maximum HP. The `when` side needs nothing new — `skill_qualified` is already in the recognized condition vocabulary and already resolves against `context["entity"]`, which the phase dispatcher already supplies.
- **One new rule in `state_reactions.yaml`**, conditioned on the transition into the in-progress climax phase and on qualifying for `rapture_renewal`, healing the authored fraction of maximum HP at no resource cost.
- **Fires exactly once per climax.** The phase dispatcher runs on canonical phase *transitions*, not on phase state, so entering the in-progress phase triggers once and a subsequent climax extension — which does not re-enter the phase — triggers nothing.
- **The trigger is deliberately source-agnostic.** The payout asks only that the holder entered the in-progress climax phase, never where the arousal came from. A climax reached through out-of-combat intimacy heals exactly as one reached through damage. The passive is therefore two things on purpose: the damage loop's third leg, and a costed out-of-combat recovery option for the archetype whose identity is turning arousal into restoration. It is priced by the climax's own shipped costs (the SP charge, the action lock, the world-clock time to climb 70 pleasure points, and the high-arousal accuracy and agility penalty carried throughout), not by a provenance check.
- **The heal is clamped to the HP gap and never revives.** Reaching climax after losing only 30% of maximum HP restores 30%, not the authored 50%; the surplus is not banked, which is what stops other arousal sources from turning the loop into a net HP generator.

**Non-goals.** No change to the climax state machine, its transitions, its SP cost or its action lock. No change to `pain_to_pleasure` (that is the companion change) or to `priestly_grace`, whose `recovery_arousal_scale` of 0.1 stays as it is — the post-climax reset to the 微興奮 band already makes the two passives' peaks mutually exclusive, so no extra suppression is needed. No new `when.event` value.

## Capabilities

### Modified Capabilities
- `damage-state-feedback`: gains a requirement covering a qualified passive's self-recovery on a canonical climax-phase entry — the once-per-transition guarantee, the max-HP-fraction magnitude, the HP-gap clamp, the no-revive rule and the resource-free settlement.

## Impact

- **Modified**: `world/skills/registry.py` (one new `ENHANCEMENT` row), `world/rules/state_reactions.py` (the phase dispatcher executes the new action; the loader validates its shape), `world/rules/rulebook/state_reactions.yaml` (one new rule).
- **Transaction surface**: the phase dispatcher's callers currently snapshot buff state because the dispatcher only applied and removed buffs. This change makes it write HP, so the enclosing snapshot must cover HP as well — verified as part of the work rather than assumed (see design.md).
- **Test updates**: `world/skills/tests/test_skill_registry.py`'s `ENHANCEMENT` key census gains one entry. That census is an existing tagged data-contract test; it is updated, not duplicated.
- **Untouched**: `world/rules/pleasure.py`, `world/rules/sexual_state.py` and `world/rules/rulebook/sexual.yaml` — the climax state machine, its reset value and its SP cost are all read, never modified.

**No new data-contract test is added by this change.** The behavior is proved with synthetic entities at declared maximum HP entering the phase transition; the only shipped-content touch is the one-line census update.

**Dependency**: none, mechanically — this change stands alone and is safe to implement before, after or alongside `pain-to-pleasure-hp-scaling`. Its *balance* justification, however, assumes that change's coefficient, so shipping this one alone would grant sustain against an arousal ramp that is still priced by the retired tier table. Sequencing them together is a balance decision, not a code dependency.

**Code conflict**: `world/rules/state_reactions.py` and `state_reactions.yaml` are also edited by `pain-to-pleasure-hp-scaling`, in the outcome-dispatch half. Whichever merges second rebases the shared loader-validation function.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
