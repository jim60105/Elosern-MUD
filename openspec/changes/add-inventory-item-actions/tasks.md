## 1. Item Mechanics Registry

- [x] 1.1 Add immutable usable-item and equipment mechanics definitions to `world.lore.items`, enforce their mutually exclusive validated shapes, and bind `healing_potion` plus existing equipment to canonical mechanics without changing presentation semantics.
- [x] 1.2 Add the deterministic item-effect rulebook and loader validation for positive bounded effect data, with healing magnitude read only from that canonical source.
- [x] 1.3 Add registry and rulebook tests for valid usable, reusable, equipment, inspect-only, unknown-effect, malformed-slot, and ambiguous definitions.

## 2. Deterministic Item Use

- [x] 2.1 Implement `ItemUseRequest`, stable rejection reasons, and side-effect-free `preflight_item_use()` for ownership, mode, effect validity, and current healing eligibility.
- [x] 2.2 Implement composable item-use planning and settlement, including HP clamping, exactly-one key and existing contained-mirror consumption, key-only consumption, unchanged reusable quantity, stable `item_used` EventLog output, and idmapper/contents/Attribute cache restoration.
- [x] 2.3 Implement one atomic exploration facade that composes item settlement with the canonical six-second clock advance and its due-event rollback journal.
- [x] 2.4 Add focused deterministic and Evennia tests for full-HP rejection, missing ownership, materialized and key-only consumables, reusable success, max-HP clamping, EventLog fields, mirror/cache rollback, and clock-callback fault rollback.

## 3. Equipment Toggle And Five Accessories

- [ ] 3.1 Change `ACCESSORY_MAX_SLOTS` from three to five and update every rule, presenter, story, and existing test that currently assumes three.
- [x] 3.2 Add shared side-effect-free equipment preflight and replace the slot-supplied mutation surface with its ownership-aware, registry-resolved immutable toggle plan and atomic singleton settlement.
- [x] 3.3 Implement exact item-key accessory removal, distinct-key membership, append below five, and named rejection at five without automatic replacement.
- [x] 3.4 Add focused tests for unheld and non-equipment rejection, all singleton slots, atomic replacement rollback, removing a middle accessory, five-slot capacity, sixth-item rejection, duplicate prevention, persistence round-trip, and no combat-round or clock cost.

## 4. Combat Item Turn

- [x] 4.1 Generalize ordinary and overwhelm round providers to the closed skill-or-item request union with explicit resolver dispatch and unchanged monster/companion `ActionRequest` policy behavior.
- [x] 4.2 Add combat-session item use with preflight-before-initiative, expanded inventory/mirror/cache outer snapshots, exactly-once first-turn use under ordinary and player-direction compressed resolution, generalized commanded-action identity, and no extra command-default time.
- [x] 4.3 Add combat tests for ordinary and player-direction overwhelm potion use, foe-overwhelm agency, commanded item logs, one action per participant, full-HP preservation, mid-round invalidation, knockout before item turn, upkeep/session/terminal fault rollback, and round-based elapsed time.

## 5. Services V3 And UI Actions

- [x] 5.1 Evolve the services presenter and exact validator to schema v3, adding nullable inventory action descriptors and exposing canonical player/inventory data during combat while keeping host, guild, and shop absent.
- [x] 5.2 Derive use and equipment descriptor enablement through their shared side-effect-free deterministic preflight APIs, including stable `hp_full` and `accessory_slots_full` reasons, with unknown and inspect-only rows carrying null actions.
- [x] 5.3 Implement exact validators and narrow adapters for `inventory.use` and `inventory.toggle_equip`, register both in the production allowlist, and publish full canonical snapshots without direct state assignment or text-parser routing.
- [x] 5.4 Update protocol mirrors, fixtures, serializers, Node tests, Python presentation/action tests, and integration tests for the expanded exact allowlist, v3 fields, exploration/combat mode shapes, stale-before-adapter versus live domain rejection, malformed payloads, duplicates, no-puppet handling, and atomic panel refresh.

## 6. Inventory Drawer Interaction

- [ ] 6.1 Update `InventoryPanel` to preserve hover/focus inspection while making deliberate activation follow the committed nullable action descriptor, including inspect-only and `aria-disabled` reason behavior.
- [ ] 6.2 Add the accessible item-use confirmation dialog with item naming, focus trap, confirm/cancel/Escape behavior, opener focus restoration, and reset on panel, drawer, mode, epoch, or transport replacement.
- [ ] 6.3 Add the combat root's client-local `背包` drawer row using the existing frameless `openDrawer` path, route confirmed use and direct equipment toggle through the single Pinia dispatch entry, preserve the in-flight lock, and avoid optimistic quantity/equipped changes.
- [ ] 6.4 Add Vitest coverage for pointer/keyboard parity, one dispatch, cancel, full-HP refusal, stale confirmation retirement, transport reset, direct equip/unequip/replacement, five accessories, cap warning, unknown items, and canonical post-result rendering.
- [ ] 6.5 Update Storybook fixtures, stories, and the frozen component-coverage manifest for actionable use, confirmation, disabled reasons, equipment toggle, five accessories, cap warning, unknown items, combat inventory, and unavailable services.

## 7. Text Command Parity And Documentation

- [ ] 7.1 Add `使用 <item_key>`/`use` and `裝備 <item_key>`/`equip`, parsing only the item key and delegating to the same exploration, combat-session, and equipment deterministic APIs.
- [ ] 7.2 Add command tests for exploration use, combat use, full-HP rejection, consumable/reusable quantity, singleton replacement, exact accessory removal, five-slot warning, and free combat equipment changes.
- [ ] 7.3 Update `docs/game/commands.md` and `docs/game/command-reference.md` with exact command keys, aliases, syntax, combat availability, turn/time costs, confirmation distinction, and named refusal behavior.

## 8. Traceability And Verification

- [ ] 8.1 Obtain canonical requirement IDs with `uv run --locked python -m tools.spec_traceability list`, add substantive `covers_requirement` annotations for modified main requirements where applicable, and run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 8.2 Run focused uv-managed tests for lore items, item rules, equipment/inventory, combat sessions, services presentation, UI action adapters, commands, and command documentation.
- [ ] 8.3 Run the dependency-free WebClient Node gate, `npm test`, `npm run build`, `npm run build-storybook`, and `npm run showcase-coverage`, fixing authored sources rather than hand-editing built output.
- [ ] 8.4 Run `uv run --locked python -m compileall -q world typeclasses commands server`, `openspec validate add-inventory-item-actions --strict`, and `git diff --check`, then compare implementation and tests against every proposal, design, and delta-spec requirement before marking the change complete.
