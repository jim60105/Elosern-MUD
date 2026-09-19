## Why

`pain_to_pleasure` converts damage taken into arousal, and it prices that conversion by the **source spell's tier** — 學徒 5 / 術師 8 / 大師 12 / 賢者 18 / 主宰 28 / 神格 40, with every non-spell source falling back to the first tier's 5. Both shipped rules in `state_reactions.yaml` carry that table.

That pricing is wrong for the game that actually exists, in two independent ways:

1. **Monsters attack, they do not cast.** A monster's ordinary strike is a non-spell source, so it is worth a flat 5 forever. Climbing from the post-climax baseline of 15 to the 極限 band floor of 85 therefore takes **14 separate hits** against ordinary enemies. The clergy's core loop — the thing that makes the archetype work — barely engages in the fights players actually have, and comes alive only against high-tier casters. That is the exact inverse of "the clergy is the front-line sufferer".
2. **The gain ignores how much it hurt.** Under the tier table, a strike that shaves 1 HP and a strike that takes half the character's health both award the same 5. The cost the character actually paid never enters the calculation, which makes the passive's own fantasy — pain becoming pleasure — unreadable in play.

`docs/lore/skill-trees/light.md` retires the tier table and reprices the gain against **the fraction of maximum HP actually lost**, with the coefficient derived so that losing 50% of max HP walks exactly one full climax journey.

## What Changes

- **The gain becomes loss-proportional.** `pleasure_gain` for an HP-loss event is `floor(140 × actual_loss ÷ max_hp)`. The coefficient is derived, not picked: the 極限 band floor is 85, the post-climax reset is 15, so one journey is 70 points, and `70 ÷ 0.5 = 140`. An independent sanity check falls out — a strike taking 10% of max HP scores **+14**, landing exactly on the upper edge of the shipped ordinary-stimulus band `arousal_up_on_stimulus: +8..+14`, so "a heavy blow" and "a strong stimulus" price the same.
- **Negative buff instances get a flat equivalent.** An accepted negative buff instance carries no HP loss, so it prices at **5% of max HP**, i.e. `+7`. Poison and curses are suffering, but they are not bleeding.
- **BREAKING**: the six-tier `pleasure_gain` mapping is retired from the `then` vocabulary. `source_tier` stops feeding `pleasure_gain` entirely; it keeps every other job it has (`apply_buff_to_source` attribution, periodic-effect tier capture).
- **`dispatch_outcome_reaction` gains an `hp_loss_amount` parameter.** Every one of the five `hp_loss` dispatch sites already computes `actual_loss` immediately above its call, so each passes the value it is already holding — this is parameter threading, not a refactor.

**Non-goals.** No change to which events trigger the passive, or to the miss / zero-loss / immunity / refresh exclusions — `damage-state-feedback` already pins those and they stay byte-identical. No change to `priestly_grace`. No new event in the closed `when.event` vocabulary.

## Capabilities

### Modified Capabilities
- `damage-state-feedback`: the qualified passive's gain is authored as a proportion of actual loss against maximum HP rather than as a source-tier lookup, with a flat max-HP-fraction equivalent for a no-loss negative buff instance.

## Impact

- **Modified**: `world/rules/state_reactions.py` (the `pleasure_gain` execution branch reads the loss fraction instead of the tier map; the loader's `then` validation accepts the new shape and rejects the retired tier mapping; `dispatch_outcome_reaction` gains `hp_loss_amount`), `world/rules/rulebook/state_reactions.yaml` (the two `pain_to_pleasure` rules).
- **Dispatch sites threading the value they already compute** (five, enumerated in design.md): `world/rules/combat.py`, `world/rules/buffs.py` (the rate-tick loss only), `world/rules/items.py`, `world/rules/action/effects/gauge_transfer.py`, and the `counter_damage` branch's recursive self-call inside `world/rules/state_reactions.py`.
- **Untouched**: `world/rules/pleasure.py` — `apply_pleasure_gain()` stays the canonical writer with its arousal/phase cascade unchanged; this change only alters the number handed to it. `world/skills/registry.py` is not touched: `pain_to_pleasure` is an effect-free qualifier row and stays exactly as it is.

**No data-contract test is added by this change.** The coefficient is proved through synthetic entities with declared max HP taking declared losses, asserting the resulting pleasure delta; no test echoes the shipped rule rows.

**Code conflict**: none with `cross-lineage-unlock` or `enhancement-catalog-alignment` (disjoint files). `rapture-renewal-climax-heal` also edits `world/rules/state_reactions.py` and `state_reactions.yaml`, but in the **phase**-dispatch half while this change edits the **outcome**-dispatch half. Whichever merges second rebases.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
