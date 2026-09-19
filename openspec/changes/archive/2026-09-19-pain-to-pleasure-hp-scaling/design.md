## Context

See proposal.md — Why. What the implementation can lean on:

- **There are exactly five `hp_loss` dispatch sites, and every one already computes `actual_loss`** on the line above its `dispatch_outcome_reaction(...)` call. Each already guards `if actual_loss > 0:` before dispatching, so the value needs threading, not deriving:
  - `world/rules/combat.py:486` — `actual_loss = max(0, int(before - max(0.0, after)))`
  - `world/rules/buffs.py:469` — the rate-tick direct loss (this file dispatches `hp_loss` **once**; its other dispatch, at line 652, is `negative_buff_added`)
  - `world/rules/items.py:972` — `actual_loss = -applied`
  - `world/rules/action/effects/gauge_transfer.py:100`
  - `world/rules/state_reactions.py:560` — the `counter_damage` branch's **recursive self-call**, carrying `source_actual_loss` for the counter-struck source. This site lives inside the dispatcher being modified, not in a caller, and is the one an implementer grepping the caller list would miss.
- Not a site: `world/rules/mp_flow.py:66` dispatches `mp_zero`, and `world/rules/combat.py:490` dispatches `physical_hit`. Neither carries a loss fraction.
- The `pleasure_gain` execution branch is one small block in `dispatch_outcome_reaction` that currently resolves a tier key against a dict and falls back to 學徒.
- `apply_pleasure_gain()` is the canonical writer and owns the whole arousal/wetness/climax-phase cascade. This change hands it a different integer and touches nothing else about it.
- The rule loader already validates each rule's `then` shape and rejects unknown action keys fail-closed, so rejecting the retired tier mapping is an addition to an existing guard.

## Goals / Non-Goals

**Goals:**

- The gain reads only the harm suffered, never the source's nature.
- The coefficient lives in the rulebook, not in Python.
- The retired tier mapping cannot be authored back in by accident.

**Non-Goals:**

- No change to the trigger set, the exclusions, the transaction boundary, or `apply_pleasure_gain()`. No change to `source_tier`'s other roles.

## Decisions

### D1. The coefficient is rulebook data, the derivation is Python

The rule authors `pleasure_gain: {max_hp_coefficient: 140}` (and the buff rule adds `flat_max_hp_fraction: 0.05`); the engine computes `floor(coefficient × actual_loss ÷ max_hp)`.

Putting 140 in the YAML keeps this change consistent with every other balance constant in the project — `sexual_pleasure.yaml`'s bands, `progression.yaml`'s multipliers — all of which are declared provisional and expected to be retuned from playtest data. A constant in Python would be the only balance number in this system that requires a code edit to move.

Alternative considered: keep `pleasure_gain: <int>` and reinterpret the int as a coefficient. Rejected — the same key would silently mean something different in old and new data, and the integer form is still used by other rules that mean a flat gain.

### D2. `hp_loss_amount` is an explicit parameter, not a context lookup

The alternative was reading the loss back off the entity inside the dispatcher (compare stored HP against a snapshot). Rejected: the dispatcher runs *after* the write, several of the call sites apply non-lethal flooring, and one of them (the counter leg) dispatches for a *different* entity than the one the outer call is about. Every call site already knows its own answer unambiguously; asking the dispatcher to re-derive it would be re-deriving a fact that was just discarded, with a floor/clamp bug waiting in each variant.

The parameter defaults to `None`. A `pleasure_gain` rule that needs a loss fraction and receives `None` produces **no gain** rather than a guessed one — the same fail-closed posture as the unreadable-max-HP case.

### D3. The negative-buff rule prices through the same derivation

`negative_buff_added` carries no loss, so its rule authors a flat max-HP fraction and the engine runs it through the identical `floor(coefficient × fraction)` path. One code path, two data shapes. This keeps the two shipped rules' numbers commensurable — a curse is worth 5% of a health bar, stated in the same currency as a hit — instead of introducing a second, unrelated scale.

### D4. Max HP is read through the existing trait accessor, and failure is silent

`floor` needs a positive denominator. The engine reads the recipient's maximum HP through the same accessor the damage pipeline already uses; if it is missing, zero or negative, the branch applies nothing. This mirrors the dispatcher's existing posture for a missing `sexual` handler or an entity without `attributes` — a state reaction on a malformed entity is a no-op, never an exception that aborts a damage settlement mid-transaction.

## Risks / Trade-offs

- **Chip damage now rounds to zero.** A strike taking under `1/140` of max HP floors to `+0`. → Accepted and arguably correct: a scratch should not advance arousal. It does mean a very high-max-HP character is immune to trivial chip accumulation, which is consistent with the passive's fantasy.
- **The clergy loop gets substantially faster against real enemies.** That is the entire point, but it is a live balance change, not a refactor. → The four brakes the lore page relies on are all pre-existing and untouched: the high-arousal agility/accuracy penalty from pleasure ≥ 60, the action lock during 進行中, the SP cost at climax, and the HP-gap clamp on any healing. The self-heal that closes the loop is a **separate** change (`rapture-renewal-climax-heal`); until it lands, this change makes arousal accumulate faster and grants no new sustain.
- **The two-step climax gate makes 50% HP an approximation.** Crossing 85 sets 接近; entering 進行中 needs one further gain event. → Documented in the lore page rather than engineered around: the extra hit is a pre-existing property of `apply_pleasure_gain` and a mild, welcome cost. The spec's "reaches the threshold band that opens the climax gate" scenario is worded to assert the band, not the phase.
- **`state_reactions.py` is also edited by `rapture-renewal-climax-heal`.** → Disjoint halves of the module (outcome dispatch here, phase dispatch there) plus a shared loader-validation function. Whichever merges second rebases the validator edit.

## Open Questions

None. The coefficient, the flat fraction and their derivations are ratified in `docs/lore/skill-trees/light.md` §聖職者循環的數值平衡.
