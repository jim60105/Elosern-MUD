## Why

統御術 is shipped content that cannot be used. Its handler requires `event_context` keys
(`confer_skill_key`, `confer_scale`) that **no production caster supplies** — `commands/action.py`
builds a cast context carrying only `disguise`, and only for `status_disguise` — so the skill is
registered, ownable, listed in the panel, and rejected at preflight on every cast. Underneath that,
`record_conferred_grant()` appends to `entity.db.skill_grants` unconditionally, so the same source
conferring the same skill twice records two grants and `effective_value()` multiplies both: a free,
repeatable, unbounded stat multiplier. It also never checks that the conferring entity owns what it
hands out. The divine-mystery redesign builds a whole chain on this verb
(`docs/lore/skill-trees/divine-mystery.md` §7 item 2), and its boundary clause 2 — "威力上限＝施法者
自身的權能上限" — is unenforceable until all three holes are closed.

## What Changes

- **BREAKING (internal storage semantics)**: `entity.db.skill_grants` becomes replace-by-key. Recording
  a grant for a `(source_key, skill_key)` pair that already has one replaces it, so a repeated
  conferral refreshes the scale instead of compounding the multiplier. Two different sources still
  count separately.
- The conferral write path rejects a skill the conferring entity does not **directly** own, so a
  conferred grant can neither exceed nor be chained onward from what its source itself holds.
- The conferral scale is read from the occurrence's own `EffectPolicy.coefficient` — the
  per-occurrence magnitude dial already index-aligned with `effects` — instead of `event_context`. The
  registry's policy validator currently rejects a non-identity coefficient on anything but damage and
  healing effects, so the two conferral effect classes are admitted to that allow-list here.
- The conferred set is **derived, not chosen**: one grant per directly-owned skill that passes the
  shipped conferrability shape validation. No caller names a skill, so no surface needs a picker.
- A conferral whose derived set is empty rejects rather than committing an action that records
  nothing.
- Both conferral prefixes drop their required event-context keys, so preflight and the shared preview
  stop advertising and then refusing them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-handler`: REMOVED the old conferral requirement and ADDED its replacement. The shape changes
  on three axes at once (additive → replace-by-key, caller scale → node data, deferred cast path →
  live cast path), so its scenario set cannot survive a MODIFIED edit; this is the same REMOVED→ADDED
  retirement the element-catalog wave used.
- `effect-context-validation`: MODIFIED — the per-handler declaration requirement gains the empty-set
  clause and stops naming conferral keys that no longer exist.

## Impact

`world/skills/registry.py` (`_validate_effect_policies` allow-list);
`world/rules/skill_effects.py` (replace-by-key write, source-ownership validation, derived set);
`world/rules/action.py` (`_handle_confer_skill_partial`, `_handle_confer_growth_rate` and both
registrations); `world/rules/action_preview.py` only if the shared preview needs more than the
now-empty required-context table (verify, do not assume); tests plus `.github/evennia-shards.json`.
`docs/lore/skill-trees/divine-mystery.md` §2, §6 and §7 were amended while this change was authored so
the design source of truth already describes the derived set and the coefficient gate. No registry
data and no catalog node lands in this change.

## Batch

- depends-on: none
- Code conflict note for the supervisor: `conferral-revocation` also edits the tail of
  `world/rules/action.py` (handler registrations) and adds a second `skill-handler` requirement. It
  reads this change's store semantics, so it queues after this one; the two touch different
  requirements, so neither rebases the other's spec text.
