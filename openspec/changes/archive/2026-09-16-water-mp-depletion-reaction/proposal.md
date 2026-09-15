## Why

Water's exclusive combat verb is the mana tide: draining enemy MP must be a first-class engine fact, not a silent gauge write. Today MP can fall to zero from buff rate ticks or cast costs with no outcome event — the `state_reactions` when-vocabulary has no MP event, `_apply_rate_modifier` dispatches only the `hp` negative-delta branch, and the step-6 cast deduction mutates the trait directly. Water's 潮退 DoT ladder (潮退侵蝕 −5, 深海漩渦 −12, 溺潮 −18) and its suffocation payoff need one canonical MP-decrease fact that every current and future MP mover shares.

User-ratified givens recorded verbatim: **MP-depletion is an engine-level global fact** — "entity MP reached zero via a decrease" is dispatched once by ONE canonical MP-decrease writer, payload carries source + tier (same convention as `hp_loss`'s source-tier in `state_reactions.yaml`). Cast-cost payment, buff rate ticks (潮退 DoT), and all future MP transfer effects MUST route through that writer. Whether zeroing suffocates is filtered at the RULE layer by source conditions (skill_qualified-style), never by not-dispatching. **Batch order:** this change lands BEFORE any 潮退 buffs.yaml row goes live — no silent no-dispatch window; the DoT rows ship inside this change.

## What Changes

- Add the canonical MP-change writer (module `world/rules/mp_flow.py`): one function pair for authored MP decreases/increases that clamps per gauge, returns the actual delta, and dispatches the new `mp_zero` outcome event exactly once when stored MP crosses from positive to zero **via a decrease**, with source-skill and source-tier attribution.
- Route every existing MP-decrease writer through it: the buff engine's `rate {target: mp}` tick path in `world/rules/buffs.py` and the step-6 cast-cost deduction in `world/rules/action.py`. No gauge-write bypass may remain.
- Extend the `state_reactions` when-vocabulary with one closed event-source-qualification key so a suffocation rule matches the event's originating skill (rule-layer source filtering; the event is always dispatched regardless of who listens). `mp_zero` rides the existing open `event:` value slot — no new when key is needed to match the event itself. (The zero-MP-cap redirect for 溺潮 does NOT get a home here: it rides change 2's per-effect audience gate, keeping the reaction engine and the cast pipeline free of it.)
- Ship the water rulebook rows this change exists to unblock: three tier-graded 潮退 MP-drain DoT buff rows (`ebbing`, `ebbing_deep`, `ebbing_maelstrom`; −5/−18/−12 per 10 s, duration 60), the `suffocated` blocking marker (40 s) plus its `suffocation_locks_actions` combat-modifier row, and the suffocation reaction rule qualified to the drowning source.
- Replace the `water_bind` row's inert emptiness with the real bind binding (`actions_per_turn: 0` combat-modifier row) so 束縛 delivered by data becomes behavior in the same wave's vocabulary.

## Capabilities

### New Capabilities
- `mp-state-feedback`: the canonical MP-change fact, its exactly-once `mp_zero` outcome dispatch with source attribution, shared-source semantics (spell cast, DoT tick, future transfer), rollback containment and cast-cost behavior.

### Modified Capabilities
- `buff-handler-integration`: the MP-targeted rate tick dispatches the canonical MP change with persisted source attribution (superset of the fixed-delta/bounds/decay requirement).
- `action-resolution-pipeline`: MP cast-cost deduction is one routed write through the canonical writer on the same staged effect (superset of the eight-step pipeline requirement).
- `combat-modifier-table`: suffocation and bind markers lock actions through the existing `actions_per_turn: 0` mechanism, one table, one condition engine.

## Impact

`world/rules/mp_flow.py` (new); `world/rules/buffs.py`; `world/rules/action.py`; `world/rules/state_reactions.py`; `world/rules/rulebook/state_reactions.yaml`, `buffs.yaml`, `combat_modifiers.yaml`, `status_display.yaml`; new focused test modules registered in `.github/evennia-shards.json`.

No active OpenSpec changes exist (`openspec list --json` returned an empty change set at authoring time), so there is no serialization gate against sibling changes — unlike Phase B. Dependencies: none; this is wave change 1 and must land before any 潮退 row goes live. This is a bounded one-engineer-day slice. Verification is synthetic program-behavior tests only — no water catalog/data-contract tests.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.
