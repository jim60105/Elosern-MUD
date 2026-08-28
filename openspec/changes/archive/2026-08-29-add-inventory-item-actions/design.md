## Context

`InventoryPanel` currently renders native buttons, but `onTileClick()` changes only client-local inspector selection. The `services` v2 inventory row contains identity, quantity, equipped state, and presentation metadata but explicitly carries no action. `ItemDefinition` likewise owns economy identity and presentation only; no deterministic item-use rule exists. Equipment writes exist in `world.rules.equipment`, but they neither verify registry mechanics and ownership nor support removing a named accessory, and the current accessory cap is three.

The existing WebClient action path already provides the required trust boundary: exact payload validators, an action-ID allowlist, authenticated actor resolution, current-state reauthorization, in-flight locking, action results, and canonical panel publication. The change must preserve that boundary and the architecture's deterministic-core single-writer rule. The browser remains a view layer and must not infer mechanics from presentation `kind`, HP values, or item names.

Active combat adds a second constraint. The current `services` panel is unavailable outside exploration, while a combat turn currently admits only an `ActionRequest` resolved by `ActionResolver`. Item use must therefore remain reachable in combat and become an initiative-ordered player action without pretending that an item is an owned skill.

## Goals / Non-Goals

**Goals:**

- Make inventory tiles truthfully use supported items and toggle supported equipment through deterministic, server-authoritative operations.
- Keep item mechanics immutable and registry-owned while keeping tunable effect magnitudes in rulebook data.
- Make item use and conditional consumption atomic, with side-effect-free eligibility checks usable by presenters.
- Let a successful combat item use occupy one ordinary round and let equipment changes remain free actions, as selected for this change.
- Raise the accessory limit to five, replace singleton equipment atomically, and require manual accessory removal at the cap.
- Keep the graphical and text clients functionally equivalent.

**Non-Goals:**

- Targeting another character with an item, choosing an equipment slot in the browser, drag-and-drop, sorting, filtering, item stacks as separate persistent records, cooldowns, crafting, item durability, equipment comparison, or confirmation for equipment changes.
- Allowing one registry item to be both directly usable and equippable in this delivery unit.
- Defining broad food, ammunition, tool, or material mechanics merely because those presentation kinds exist.
- Adding compatibility adapters or data migrations for the unshipped v2 services payload.

## Decisions

### D1. Item mechanics are registry-owned and separate from presentation

`ItemDefinition` gains one optional mechanics value. A usable item carries an immutable use definition with an `effect_key`, `consumable` flag, and combat permission. Equipment carries one exact `EquipmentSlot`. These forms are mutually exclusive for this change; an item with neither remains inspect-only. Presentation `kind` remains visual identity and never selects behavior.

Effect magnitudes and condition parameters live in a new deterministic item-effect rulebook keyed by `effect_key`. The initial `healing_potion` binding restores the rulebook's positive integer HP amount, clamps at maximum HP, is consumable, targets the actor only, and is permitted in combat. Tests assert behavior against the canonical rulebook value rather than duplicating it.

This is preferred over deriving behavior from `ItemKind`, which cannot distinguish an inert potion from a usable potion or assign a weapon to main hand versus off hand. It is also preferred over embedding numeric effects in `ItemPresentation`, which would violate the existing presentation-only contract.

### D2. Item use has a pure preflight and one atomic settlement API

`world.rules.items` owns `ItemUseRequest`, `ItemUsePlan`, named reason codes, `preflight_item_use()`, plan application, and the public exploration/combat settlement facades. Preflight resolves the current registry definition, verifies that the actor holds at least one canonical inventory key, validates the effect and current mode, checks effect-specific conditions, and selects at most one matching contained-object mirror without writing state. For healing, current HP must be below maximum HP. The presenter may call preflight to publish an enabled descriptor or a stable disabled reason, but that descriptor is advisory only.

The item-use plan contains the complete trait update, optional one-key inventory removal, and optional deletion of one matching contained Evennia Object. A key-only consumable has no object deletion; a materialized consumable removes exactly one mirror. Plan application uses the inventory planner and a dedicated object/cache restoration journal, so a database rollback also reconciles Evennia's idmapper and contents caches. A reusable item applies the same effect without key or object removal.

The exploration facade repeats preflight, then wraps plan application and the canonical six-second `WorldClock.advance()` settlement in one outer database transaction. It composes the clock settlement's existing rollback journal with item traits, inventory, quest progress, object containment/deletion, and in-process cache snapshots. A due clock callback failure therefore restores both item and clock surfaces. Rejection and fault-injected failure preserve all touched durable and in-process state byte-for-byte.

This two-stage design handles stale confirmation dialogs safely. A client-visible enabled state never grants authority.

### D3. Combat rounds accept a typed deterministic turn request

The ordinary and compressed round providers and `run_round()` are generalized from `ActionRequest | None` to a closed union of `ActionRequest`, `ItemUseRequest`, or `None`. Dispatch remains explicit: skill requests go to `ActionResolver`; item requests go to the item resolver. Both return the existing result/EventLog shape needed by round settlement and narration. No skill-registry entry is fabricated for an item.

The combat-session facade runs item preflight before initiative. A rejection starts no round. After successful preflight, the item request is supplied exactly once at the player's initiative position while every other participant receives its ordinary policy request. If earlier initiative invalidates the item use, the already-started round remains consumed, matching existing mid-round cast invalidation. Combat's outer touched-surface snapshot explicitly includes item traits, inventory, quest progress, selected mirror object/containment, and the item resolver's cache journal in addition to the existing combat surfaces, so a later upkeep, session, or terminal-settlement failure restores database and in-process state together.

When the player's team is the overwhelming side, `resolve_overwhelm()` accepts the same closed request union for the first simulated player turn. A selected item use resolves once on that first turn; subsequent compressed player turns use ordinary deterministic `basic_attack`, as they do after a selected skill. Commanded-action identity is generalized from skill-only arguments to the closed pair `action_kind` (`skill` or `item`) and `action_key`, and exactly one first-round `commanded_action` entry records that pair. Foe-overwhelming and undecided encounters continue through ordinary rounds and therefore preserve per-round item choice.

Out of combat, successful use advances the player-driven clock by the canonical six-second item-use cost. In combat it adds no command-default time; elapsed rounds settle through the existing combat clock path.

### D4. Equipment toggling is item-specific, ownership-aware, and atomic

`world.rules.equipment` gains `preflight_equipment_toggle(entity, item_key)`, an immutable toggle plan, a public `toggle_equipment(entity, item_key)` operation, and named equipment reasons. Preflight resolves registry mechanics, verifies canonical inventory ownership, computes the exact replacement/removal, and writes nothing. The presenter and mutating operation share this path, and mutation repeats preflight before atomically applying the plan. Equipment storage continues to contain item keys only, and equipped items remain in inventory.

An equipped singleton item is removed from its exact slot. An unequipped singleton item atomically replaces the current occupant of its registry-declared slot; the replaced item remains held. An equipped accessory is removed by matching `item_key`, never by popping the last list entry. An unequipped accessory appends only when fewer than five accessories are equipped. At five, it rejects without replacement. The normalized equipment state forbids duplicate equipped occurrences of one item key, which makes one aggregated inventory tile a deterministic membership toggle.

Equipment toggling does not consume a combat action or advance the clock. The adapter still revalidates current state and publishes a fresh snapshot so subsequent combat modifiers and action previews read the new canonical equipment.

### D5. Services v3 publishes inventory affordances in exploration and combat

The exact services schema advances from v2 to v3 with no compatibility branch. Each inventory row adds exactly one nullable `action` field. Registered usable and equipment items receive the existing bounded action-descriptor shape; unknown and inspect-only items receive `null`. Use descriptors carry `inventory.use`; equipment descriptors carry `inventory.toggle_equip`. Current preflight determines `enabled` and a stable disabled reason, including `hp_full` and `accessory_slots_full`. No numeric effect, condition threshold, or slot choice is sent.

In exploration, the rest of the services panel remains unchanged. In active combat, the panel remains available with canonical player summary and inventory, while host, guild, and shop are null and their actions are absent. Creation-pending characters still receive the unavailable form. This is preferred over creating a second inventory panel because the current drawer, presenter, validator, and store already have one canonical inventory source.

### D6. Two exact UI actions reuse the existing dispatch boundary

The production registry adds:

- `inventory.use` with exact payload `{item_key}`.
- `inventory.toggle_equip` with exact payload `{item_key}`.

Both adapters obtain the actor from the authenticated session, accept no actor, effect, quantity, target, slot, HP, or combat fields, and call only their public deterministic API. `inventory.use` routes through the active combat-session facade when combat is active and calls atomic out-of-combat item-plus-clock settlement otherwise. Both use full-snapshot publication because use may alter status, inventory, combat outcome, clock, context actions, and art, while equipment can alter status and combat previews. Dispatcher epoch/revision checks run first: a retired revision returns `stale` without adapter invocation; a live revision whose domain state changes before settlement returns the deterministic current-state reason such as `hp_full`.

Routing through text commands was rejected because it would bypass exact action payloads and duplicate parsing concerns.

### D7. Tile activation is action-aware without losing inspection accessibility

Pointer hover and keyboard focus continue to drive the shared inspector. Deliberate button activation behaves by the committed action descriptor:

- `action = null` keeps inspection-only behavior.
- A disabled action opens the bounded alert/toast with the committed reason and dispatches nothing.
- An enabled `inventory.use` opens a modal confirmation naming the item. Confirm dispatches once; cancel, Escape, or close dispatches nothing and restores focus to the tile.
- An enabled `inventory.toggle_equip` dispatches immediately with no confirmation.

The combat dock root gains one client-local `背包` row using the existing exploration `openDrawer = inventory` precedent. It opens the frameless drawer without dispatching, adding a server action, pushing a router frame, or changing any server-authored combat action. This gives combat an exact keyboard and pointer entry point while services v3 supplies the canonical rows.

The modal is focus-trapped, labelled, keyboard operable, and reset by panel replacement, drawer close, mode/epoch change, or transport reset. The action client lock prevents a second activation while a mutation is in flight. A stale server rejection uses the same action-result alert path as every other UI action.

### D8. Text commands call the same deterministic APIs

The player commands are `使用 <item_key>` with alias `use`, and `裝備 <item_key>` with alias `equip`. They pass only the parsed key into the same item and equipment facades used by UI adapters and do not duplicate eligibility or mutation logic. Combat use enters the same combat-session facade, while equipment remains a free action. Command syntax and availability are documented in both required game command documents and covered by command tests.

### D9. Item use emits one stable event identity

A successful item use emits one `item_used` entry in the actor's EventLog. Its data contains exactly `item_key`, `effect_key`, `consumable`, and `amount`; `amount` is the actual bounded change, not the configured maximum. The target is the actor for this self-use delivery unit. Rejected preflight emits no EventLog. In player-direction compression, the separate `commanded_action` entry identifies `action_kind = item` and the item key; it does not replace `item_used`.

## Risks / Trade-offs

- [Generalizing the round request type could weaken the ActionResolver boundary] → Keep a closed union and explicit resolver dispatch; skills still have exactly one ActionResolver path, while item mutation stays in its dedicated deterministic resolver.
- [A descriptor can become stale while the confirmation dialog is open] → Treat descriptor eligibility as presentation only and repeat full preflight during execution.
- [Publishing inventory during combat could accidentally expose shop or guild mutations] → Services v3 requires host, guild, and shop to be null in combat and validates the exact mode-specific shape.
- [A free equipment toggle can be used repeatedly during combat] → Preserve the explicit product decision, retain in-flight request locking, and document that it does not consume a round; all effects are canonical and immediately republished.
- [Aggregated rows cannot identify two equipped copies of the same accessory key] → Normalize equipment to at most one equipped occurrence per item key for this change; distinct accessory keys may fill all five slots.
- [Item effects, clock settlement, key removal, and object-mirror deletion could partially commit] → Build a complete plan before mutation, compose it with the owning outer transaction, and restore database, idmapper, contents, and Attribute caches under fault injection.
- [Changing services v2 to v3 invalidates old bundles] → Build and ship server validators, client reducer, and Vite bundle together; no released client requires compatibility.

## Migration Plan

No persisted-data migration is required. Inventory and equipment remain key-only structures. Implementation updates the accessory constant, item registry, rules, protocol, server presenter, client source, and built bundle in one release. Existing local development records containing more than one occurrence of the same equipped key or malformed slot data fail closed until corrected; no compatibility normalization is added.

Rollback consists of reverting the complete change and rebuilding the WebClient bundle. Because no new persistent shape is written, rollback does not require data conversion.

## Open Questions

None. Combat item use consumes a round, combat equipment changes are free actions, usable items require confirmation, equipment does not, and the accessory cap is five.
