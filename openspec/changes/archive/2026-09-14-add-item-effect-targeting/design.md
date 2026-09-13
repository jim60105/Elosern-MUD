## Context

See `proposal.md` — Why, and `docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §5.1,
§5.2, and §5.8.

Constraints that shape the approach:

- `add-declarative-item-effects` left a deliberate seam: the scope vocabulary exists and is validated,
  but only the acting-entity value loads. This change removes exactly that restriction and wires what
  it was holding back.
- `refactor-target-resolution-srp` left `resolve_targets(actor, context, requirement, candidates)`,
  which an item can call without owning a skill.
- `ItemTouchedJournal` is currently single-entity and is the most delicate code in
  `world/rules/items.py`. Extending it is the real work of this change, not the targeting.
- `inventory-item-actions` requires that a command syntax change update `docs/game/commands.md` and
  `docs/game/command-reference.md` in the same change.

## Goals / Non-Goals

**Goals:**

- Item targets pass through exactly the validations skill targets pass, with no second resolver.
- A failure anywhere in a multi-target settlement leaves every touched entity byte-identical to its
  pre-call state.
- Reach stays a property of the item. No caller input can widen it.

**Non-Goals:**

- New item content. The five scopes become available; writing 女神之吻聖霧 and 情欲香爐 into the
  rulebook is separate content work.
- Multi-target UI affordances beyond passing a target key. A target picker in the web client is its
  own change.
- Changing round occupancy, time cost, or consumption arithmetic. One use is one round and one unit
  regardless of how many entities it reaches.

## Decisions

### D1 — At most one caller-supplied target for a whole use, never a list or a shorthand

The request carries `target: Any | None`, not a sequence.

*Why:* an item's reach is fixed by the rulebook, so the only thing a caller can legitimately choose is
*which* single entity a single-scope effect lands on. Accepting a list would let a caller turn a
single-scope item into an area item; accepting a shorthand would let a caller choose a group an item
was never scoped for. A scalar makes both unrepresentable rather than validated-against.

*Consequence:* an item declaring two single-scope effects points both at the same supplied target.
That is the intended reading — one use, one chosen recipient.

*Alternative rejected:* mirror the skill request's `targets: str | Sequence`. Skills let the *player*
choose scope; items do not. Copying the skill shape would import a permission the item model does not
grant.

### D2 — Context is a parameter, not a construction inside preflight

`preflight_item_use(request, *, in_combat, context)`.

*Why:* the combat session already holds a reconstructed `Battlefield`, and `service_view` already
knows whether it is rendering in combat. Building a context inside preflight would either duplicate
that reconstruction or force preflight to know how to find a battlefield — both worse than passing the
one the caller already has.

*Note:* `in_combat` and `context` are now partially redundant (a battlefield context implies combat).
They are kept separate because `in_combat` gates the `combat_allowed` permission, which is about the
item, while the context is about the world. Collapsing them would conflate two questions.

### D3 — The journal becomes a per-entity map, with actor-only surfaces kept actor-only

`ItemTouchedJournal` holds the actor's inventory, quest log, and mirror once, plus a per-entity record
of traits, buffs, and sexual state for every touched target (the actor included).

*Why:* only the actor consumes, so capturing inventory per target would be meaningless and would
invite a restore that writes inventory onto a companion. Splitting the surfaces by who can own them
makes the wrong restore unrepresentable.

*Why capture before any write rather than lazily per target:* a lazy capture taken after an earlier
target's write has already run cannot restore state that an earlier step's cascade touched. Pleasure
is the concrete case — it moves four sexual-state values at once.

*The half that is easy to miss:* `restore()` today does more than write attribute values back. It
calls `_refresh_advance_entity_caches(actor)` (`world/rules/clock.py:561-580`), which clears the trait
cache **and pops the memoized `entity.sexual` handler** off `entity.__dict__`. `restore_traits` alone
clears only the trait cache. A per-entity restore that calls `restore_traits` and writes the buff and
sexual attributes back, but skips the handler pop, would roll back a companion's stored sexual state
while leaving a stale in-memory `companion.sexual` readable in the same process for the rest of the
session — exactly the failure `_refresh_advance_entity_caches` exists to prevent, and invisible to any
test that re-reads from storage rather than through the handler. **The cache drop runs per captured
entity, not only for the actor.**

*What stays actor-only:* the `contents_cache.init()` re-seed. Only the actor holds the consumed
mirror, so re-seeding a companion's contents cache would be meaningless work on an untouched surface.

### D4 — Targets are resolved once in preflight and carried in the plan

Settlement does not re-resolve; it re-runs preflight (as today) and uses the returned plan's steps.

*Why:* this is the existing contract — "a presented descriptor is advisory only" — and it keeps the
resolver off the write path entirely.

### D5 — `TARGET_INVALID` carries the resolver's reason as detail rather than mapping it

The item layer does not translate `target_dead` / `target_not_present` / `target_out_of_range` into
item-specific reason codes.

*Why:* `ItemUseReason` would otherwise have to mirror `RejectReason` member for member and stay in
sync forever. One item-level code plus the underlying reason as detail gives the player surface
everything it needs while keeping one owner per vocabulary.

### D6 — Group scopes out of combat reach every present entity, hostility-free

`RoomActionContext.relation_to` returns `ALLY` for every non-actor, so `all-allies` and `all` coincide
out of combat and `all-enemies` resolves to nothing.

*Why:* this is the shipped out-of-combat relation model, specified in `targeting-validation`. An item
scoped to the opposing side therefore rejects out of combat with no eligible member — which is the
correct outcome for a thrown weapon used in a tavern, and requires no new rule.

## Risks / Trade-offs

- **A restore writes one entity's snapshot onto another** → key every captured record by the entity's
  primary key and assert the identity on restore; add a test with two targets whose gauges differ so a
  swapped restore fails loudly rather than plausibly.
- **A rolled-back target keeps a stale in-memory `sexual` handler** → run the cache drop per captured
  entity (D3), and test it by reading `target.sexual.pleasure` *through the handler* in the same
  process after a rolled-back multi-target pleasure write. A test that re-reads from attribute storage
  instead would pass while the bug is present.
- **The combat outer rollback misses the new per-target surfaces** → `combat.py`'s item branch folds
  the journal in; the existing combat fault-injection tests are extended to a multi-target item rather
  than new ones being written beside them.
- **A partially-applied multi-target use commits because one target's write raised after another's
  succeeded** → all steps stay inside the one existing `transaction.atomic()`; the journal covers the
  in-process caches the transaction cannot roll back.
- **Target count silently inflates round count or time cost** → explicit tests pinning one round and
  one unit consumed for a four-target item.
- **Archive ordering**: this change's `item-effect-rulebook` delta modifies a spec that
  `add-declarative-item-effects` creates. Archive that change first, or the delta is refused. The
  validator already reports this as an informational notice.

## Migration Plan

No data migration (unreleased project, zero users). No shipped item changes scope, so the change is
observable only through the new capability, not through altered behavior of existing content.

The loader widening, the request shape, the journal rewrite, and the consumer plumbing land together:
a widened loader with an unwired settlement path would accept rulebook data the resolver cannot honor.

Rollback is a revert; nothing persisted changes.
