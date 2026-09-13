# Tasks: add-item-effect-targeting

Depends on `refactor-target-resolution-srp` and `add-declarative-item-effects` being implemented
first. Design decisions referenced below live in `design.md` (D1–D6).

## 1. Journal first — the riskiest surface, before anything depends on it

- [ ] 1.1 Rewrite `ItemTouchedJournal` as actor-owned surfaces (inventory, quest log, mirror,
  contents-cache re-seed) plus a per-entity record of traits, buffs, and sexual state keyed by primary
  key (D3). Verify the actor's own record is captured through the same per-entity path, not a special
  case.
- [ ] 1.2 Run the in-process cache drop for **every** captured entity on restore, not only the actor:
  `restore_traits` clears the trait cache but not the memoized `entity.sexual` handler, which
  `_refresh_advance_entity_caches` (`world/rules/clock.py:561-580`) pops (D3). Verify with a
  fault-injection test that reads `target.sexual.pleasure` **through the handler** in the same process
  after a rolled-back multi-target pleasure write and gets the pre-call value — a test that re-reads
  from attribute storage instead would pass while the bug is present.
- [ ] 1.3 Assert entity identity on restore so a record can only be written back to the entity it came
  from (design Risks). Verify with a two-target test whose gauges differ, so a swapped restore fails
  loudly rather than plausibly.
- [ ] 1.4 Verify the existing single-target rollback tests
  (`test_item_use.py`, `test_holy_water_cleanse.py`) pass unchanged against the rewritten journal
  before any multi-target code exists.

## 2. Scope resolution

- [ ] 2.1 Remove the self-only restriction from `world/rules/item_effects.py` and add the scope →
  `TargetRequirement` mapping: self → SELF/SELF_ONLY, single → SINGLE/ANY, the three group scopes →
  AREA/ANY plus their shorthand. Verify the `item-effect-rulebook` delta's "Every scope value loads"
  scenario.
- [ ] 2.2 Add a structural test that item and skill targets validate identically: an item effect
  scoped to a single entity and a single-target skill reject the same dead candidate for the same
  reason through the same resolver.

## 3. Request and preflight

- [ ] 3.1 Add `target: Any | None = None` to `ItemUseRequest` — a scalar, never a sequence or a
  shorthand (D1). Verify a supplied group shorthand token rejects.
- [ ] 3.2 Add the `context` parameter to `preflight_item_use` (D2). Verify `in_combat` still gates the
  `combat_allowed` permission independently of the context's kind.
- [ ] 3.3 Resolve each effect's targets through the shared resolver and expand group scopes through
  the context. Verify the five ADDED scenarios in the `item-use-resolution` delta, including the
  out-of-combat room resolution and the empty-group rejection.
- [ ] 3.4 Add `NO_TARGET` and `TARGET_INVALID` to `ItemUseReason` with Traditional Chinese messages,
  `TARGET_INVALID` carrying the resolver's own reason as detail (D5). Verify the enum completeness
  test still covers every member.
- [ ] 3.5 Extend the effectiveness gate across targets: reject only when no effect is effective
  against any of its targets. Verify the "One effective target among several carries the whole use"
  scenario.

## 4. Settlement and event log

- [ ] 4.1 Expand the plan to one step per effective effect-and-target pair (D4), keeping every step
  inside the single existing `transaction.atomic()`. Verify consumption does not scale with target
  count — the "A multi-target use consumes exactly one unit" scenario.
- [ ] 4.2 Capture the journal for every entity the plan touches before the first write. Verify the
  "A mid-settlement failure restores every touched entity" scenario with fault injection after two of
  four targets.
- [ ] 4.3 Emit one `item_used` entry per effective pair, each naming its own target, and set the
  EventLog's target list to the deduplicated touched set. Verify the "A multi-target effect emits one
  entry per affected target" scenario.

## 5. Combat wiring

- [ ] 5.1 Pass the target and the battlefield context through both `ItemUseRequest` constructions in
  `world/rules/combat_session.py` (`:1235`, `:1248`). Verify the existing combat item-turn suite
  passes unchanged.
- [ ] 5.2 Fold the multi-entity journal into `world/rules/combat.py`'s item branch rollback contract.
  Verify by extending the existing combat fault-injection tests to a multi-target item rather than
  writing new ones beside them.
- [ ] 5.3 Verify a four-target item consumes exactly one round and adds no separate item-use time —
  the two new `item-use-resolution` combat scenarios.

## 6. Player surfaces

- [ ] 6.1 Extend `commands/items.py` to `使用 <item_key> [target]`, resolving the target token to a
  present entity. Verify the missing-target and telnet/WebClient-parity scenarios in the
  `inventory-item-actions` delta.
- [ ] 6.2 Add the optional bounded `target_key` to the `inventory.use` payload in
  `web/webclient/actions/service_actions.py`, keeping every existing prohibited field prohibited.
  Verify the two new payload scenarios, including that a target supplied for a self-scoped item is
  ignored rather than honored.
- [ ] 6.3 Build a `RoomActionContext` in `world/rules/service_view.py:770` so inventory-row enablement
  descriptors resolve through the same preflight. Verify a single-scope item's row shows the
  no-target reason rather than appearing enabled.

## 7. Documentation and validation

- [ ] 7.1 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the new `使用`
  syntax — required by `inventory-item-actions` to land in this same change. Verify both files show
  the optional target argument.
- [ ] 7.2 Update the 第六層 scope table in `docs/lore/items.md` and `docs/development/adding-items.md`
  §2 to describe the five scopes and which lore items each unblocks. Verify no remaining claim that
  items only affect their user.
- [ ] 7.3 Run the full deterministic suite plus the item regression test from
  `add-declarative-item-effects` task 1.1, and verify the four shipped items still behave identically.
- [ ] 7.4 Run `openspec validate add-item-effect-targeting` and the repository's lint/observability
  gate; verify both pass, and confirm the only remaining notice is the expected archive-ordering
  informational about `item-effect-rulebook`.
