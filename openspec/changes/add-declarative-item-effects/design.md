## Context

See `proposal.md` — Why, and `docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §3 and
§5, which this change implements for self-scoped effects.

Constraints that shape the approach:

- `world/rules/items.py` is 730 lines and already owns settlement, the rollback journal, and the
  clock seam. The vocabulary and loader do not belong in it.
- `equipment_effects.py` is the shipped precedent for "registry declares the shape, rulebook owns
  everything else, loader enforces two-way alignment at startup". Items should look like it.
- `extract-shared-effect-appliers` must land first: this change binds four effect verbs to the entry
  points it publishes.
- The four shipped items must keep their exact magnitudes and their exact rejection reasons. This is
  a model change, not a balance change.

## Goals / Non-Goals

**Goals:**

- A new effect for an existing verb is a YAML edit, with no Python change anywhere.
- `world/rules/items.py` contains no branch keyed to an individual item or effect identity.
- The four shipped items behave identically before and after.

**Non-Goals:**

- Targeting. Every scope except the acting entity is rejected at load time here (see D5).
- `ItemKind.TOY`, the ammunition consumption mechanic, and any new item content. All separately
  flagged in `docs/lore/items.md`.
- Unifying item gauge writing with `combat.py::_apply_heal`. Two gauge writers remain; merging them is
  a question this change does not answer.

## Decisions

### D1 — A separate `world/rules/item_effects.py` module

Vocabulary, dataclasses, and loader go in a new module; `world/rules/items.py` imports the loaded
profiles.

*Why:* it mirrors the `equipment_effects.py` / `equipment.py` split already in the tree, and keeps the
settlement file from growing while it is being substantially rewritten.

*Alternative rejected:* extend `world/lore/items.py`. The registry is lore — immutable identity — and
the loader validates rulebook data against it. Putting the validator in the thing being validated
inverts the dependency.

### D2 — The verb key is the discriminator; no separate `op` field

An effect entry is `{stat, amount, scope}`, `{apply_status, scope}`, or `{remove_status, scope}`.

*Why:* the three selectors (`all`, `positive`, `negative`) are meaningful only when removing, so
splitting apply and remove into two verbs makes the illegal combination unrepresentable rather than a
cross-field rule the loader must remember to check. The YAML also reads as a sentence.

*Alternative rejected:* `{status, mode: apply|remove}`. Symmetrical with the stat entry, but
reintroduces the cross-field rule and lets `{status: all, mode: apply}` be written before being
rejected.

### D3 — Effectiveness is computed in preflight, not at apply time

Each `ItemEffectStep` carries the magnitude actually applicable to current state, computed before any
write.

*Why:* this is the existing contract (`ItemUsePlan` already carries the bounded amount, not the
configured one) and it is what makes the event log report what happened rather than what was
configured. It also gives the at-least-one-effective gate something to test without writing.

*Trade-off:* a step's magnitude is computed against state as it was before earlier steps in the same
use applied. For the shipped and near-term items — each effect touching a different stat — this cannot
matter. If an item ever declares two adjustments to the *same* stat, the second's precomputed
magnitude will be stale. The loader SHALL reject two adjustments to the same stat in one item so the
stale case is unrepresentable rather than subtly wrong.

### D4 — Reason-code fallback rather than a new code per stat pair

When a use is rejected, the code is the shared one if every ineffective step agrees, else `no_effect`.

*Why:* this degrades exactly to today's behavior for single-effect items, so all four shipped
`hp_full` / `mp_full` / `no_debuffs` spec scenarios survive without a special case. Enumerating a code
per combination would be unbounded.

### D5 — Non-self scopes are rejected at load time, with the owning change named

The scope vocabulary is fully defined and validated here; only the acting-entity value is accepted.

*Why:* the alternative is either a half-wired scope that reaches settlement and does something
undefined, or splitting the vocabulary definition across two changes so neither reviews it whole.
`AGENTS.md` explicitly prefers a deliberate declared seam over a fake implementation.

### D5b — `apply_status` builds a source-qualified instance key for `unique_per_source` definitions

*Why this is not automatic:* `_add_buff` keys the handler entry on `instance_key or definition_key`
and carries `source_key` only as opaque cache data. Passing `source_key` alone therefore does **not**
produce independent instances — two different items granting the same status would collide on one
handler key. The shipped precedent for genuine per-source stacking is `grant_conferred_growth_rate`
(`buffs.py:228-240`), which builds `instance_key=f"conferred_growth_rate:{source_key}"` explicitly.

*Decision:* the `apply_status` dispatch passes `source_key=f"item:{item_key}"` and, when the target
definition declares `stacking: unique_per_source`, also
`instance_key=f"{status}:item:{item_key}"`. A `refresh`-stacking definition keeps the bare definition
key so re-application renews the one instance, which is that stacking mode's whole point.

*Note:* no shipped item uses `apply_status`, so this is unobservable today. It is decided here
because the approved design document makes a per-source stacking claim that would otherwise be false
the first time an aphrodisiac-mist or regeneration item is written.

### D5c — The status verbs get their own ineffective reasons

`STATUS_BLOCKED` for an `apply_status` the target is equipment-immune to, and `NOTHING_TO_REMOVE` for
a `remove_status` selector matching nothing — except the `negative` selector, which keeps the shipped
`no_debuffs` reason so 受洗聖水's specced scenario survives verbatim.

*Why now rather than when the first such item ships:* D4's fallback rule says a single-effect item
reports its one ineffective step's own reason. Without these members, a single-effect
`apply_status` item would report the generic `no_effect` while a single-effect stat item reports
`hp_full` — an inconsistency baked into the vocabulary at the moment the vocabulary is being designed.

### D6 — `MAX_EFFECT_AMOUNT` bounds the absolute value

The existing 9999 bound now applies to `abs(amount)`, and zero is rejected.

*Why zero is rejected:* an effect that can never change anything is a configuration mistake, not a
deliberate no-op, and silently accepting it would produce items that always reject with `no_effect`
for reasons invisible in the YAML.

### D7 — The journal surface stays actor-only in this change

`ItemTouchedJournal` gains the sexual-state surface (pleasure effects write it), but remains
single-entity.

*Why:* every shipped and accepted scope in this change is the acting entity, so a multi-entity journal
would be untestable dead code here. It is the first task of `add-item-effect-targeting`.

## Risks / Trade-offs

- **A migrated item silently changes magnitude or reason code** → the regression task pins all four
  shipped items' amounts, reason codes, and settlement outcomes before the rewrite, and re-runs them
  after.
- **The rewrite of `world/rules/items.py` loses a rollback surface** → the journal capture/restore
  code is not rewritten in this change; only the plan and apply paths are. Any journal edit beyond
  adding the sexual-state surface is out of scope and should be treated as a review flag.
- **Pleasure effects reach `apply_pleasure_gain` with a negative amount, a direction that function was
  written for gains** → explicit tests that the arousal, wetness, and climax cascade does not fire on
  a reduction, and that the value clamps at zero.
- **Two adjustments to one stat produce a stale precomputed magnitude** → the loader rejects that
  shape outright (D3).
- **A `buffs.yaml` key collides with a selector word** → guarded by the startup assertion added in
  `extract-shared-effect-appliers`.
- **`test_equipment_combat_wiring.py` is treated as an import-path fix and under-estimated** → it
  constructs the old mechanics shape and asserts on removed plan fields; budget it as a real rewrite
  (see proposal Impact).

## Migration Plan

No data migration (unreleased project, zero users). The registry deletion, the rulebook re-key, and
the settlement rewrite must land in one commit: `ItemEffectKey` cannot be removed while
`item_effects.yaml` is still keyed by it.

Rollback is a revert; nothing persisted changes.
