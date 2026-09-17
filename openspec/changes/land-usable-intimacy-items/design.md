## Context

See `proposal.md` — Why. Everything this slice needs already exists and is tested; what it lacks is shipped data.

`world/rules/item_effects.py` declares `ItemStat.PLEASURE` and validates it like any other gauge. `world/rules/items.py` special-cases it in exactly two places: the preflight reads the pleasure counter without materialising the intimacy handler and reports the full-gauge reason at 100, and the settlement writes through `apply_pleasure_gain`, the single entry point in `world/rules/pleasure.py`, then reports the delta that actually moved. Non-consuming uses are already handled — the mirror-deletion step is guarded by the consumable flag — and `combat_allowed` is already enforced at submission.

The loader closes `item_effects.yaml` against the registry's usable set in both directions at startup. A registry entry with use mechanics and no profile, or a profile with no registry entry, fails the server.

`sexual.yaml` fixes the stimulus band at `+8..+14` for the `stimulus_applied` event. That is the range the intimacy system already considers one act's worth of stimulation.

## Goals / Non-Goals

**Goals:**
- Ship the first real users of the pleasure effect verb, the combat bar, and the non-consuming use.
- Keep every magnitude traceable to a number the intimacy system already uses, so nothing here becomes an independent balance knob.

**Non-Goals:**
- Any status effect. The codex's earlier 「催情霧」 was retired in favour of a plain pleasure gain precisely so this slice would need no status-rulebook edit.
- Duration, cooldown, or lingering-sensitivity modelling. The codex's flavour text describes effects lasting an evening; the mechanical model is a single instantaneous gain, and the document deliberately does not claim otherwise.
- Storefronts, for the third time. Same follow-up.

## Decisions

**Three magnitudes taken verbatim from the stimulus band, not chosen.** `sexual.yaml` already says one act's stimulation is `+8..+14`. Gentle takes `+8`, moderate `+11`, intense `+14` — the band's floor, midpoint, and ceiling. This means a bath salt is never stronger than a caress and the sanctuary's ritual mist is never stronger than the strongest act, without anyone having to re-derive a scale. Alternative considered: a separate item magnitude scale. Rejected — a second scale would drift from the first and would need its own balance rationale.

**One effect entry per device, self-scoped.** The effect model permits ordered multi-entry profiles and five scopes. None of the seven needs either: the codex describes each as doing one thing to its user. Declaring a single self-scoped entry keeps every device's behaviour obvious and leaves the richer shapes for items that genuinely need them. It also means a full pleasure gauge makes the whole use ineligible, which is the correct refusal — there is nothing else for the use to accomplish.

**Non-consuming devices are bounded only by the item-use time cost, and that is enough.** `纏枝魔藤`, `女神之吻聖霧`, and `情欲香爐` are reusable in the codex. With no cooldown system, a player can use one repeatedly; each use costs the standard out-of-combat item-use duration of world time, and the gauge saturates at 100, at which point further uses are refused rather than wasted. So the worst case is spending world time to reach a state the intimacy system already lets a player reach. Adding a cooldown mechanism to prevent that would be inventing a system to solve a non-problem. This is recorded because it is the obvious reviewer question.

**`combat_allowed = false` for all seven, including the ones that look like potions.** `熱吻藥水` and `微電跳蛋糖` are shaped like combat consumables, and raising an opponent-facing gauge mid-fight would interact with the intimacy combat rules in ways the codex never designed. The codex states the whole category is out of combat; keeping the bar uniform avoids a per-item argument.

**`情欲香爐` is usable, not wearable.** It was catalogued as a worn accessory carrying a 催情霧 attached buff. A worn item cannot express a one-shot gain, so when the status was retired the censer moved to the usable table as a reusable device. Its 12000-copper price and `rare` tier came with it; both sit inside the intimacy-device band and need no adjustment. This is recorded because the item appears in older drafts of the codex under the wearable table.

## Risks / Trade-offs

- **First shipped use of the pleasure write path means an unexercised integration could surface here.** → The path is covered by synthetic-item tests in `world/rules/tests/test_item_use.py` and `test_item_combat_turn.py`, including the zero-floor and mid-band cases. The remaining risk is the preflight's fail-closed read of an unmaterialised intimacy record, so the verification group uses a device on an entity that has never had intimacy state touched.
- **A reusable item is a new lifecycle for the rollback journal.** → The journal already captures gauges, statuses, and intimacy state per touched entity, and skips the mirror-deletion step for a non-consuming use. The verification group asserts inventory count is unchanged after a successful reusable use and after a rolled-back one.
- **Seven more unstocked items, in a category that now has twelve.** → The intimacy category ships complete as data and reachable only by grant until the 聖所 and elven storefronts land. That follow-up is named in the codex and is the single largest remaining gap in the item work.
- **Pleasure is a gauge players may not want raised by accident.** → Every device here is self-scoped and player-initiated; nothing in this slice lets one entity raise another's pleasure.

## Migration Plan

Not applicable. Pre-release, additive, and no existing item profile changes.
