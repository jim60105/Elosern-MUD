# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Implement actor-local item list/detail/target/review and shared command payloads; test companion-only stock, no-effect disabled reasons, SELF and targeted item scopes.
  - `web/static/webclient/js/elosern/combat_menu.js` adds `panelItems`/`itemModel`/`itemsRootRow`/`itemRows`/`openItem` (the `combat.items` stock frame plus one item's `none-confirm`/`self-confirm` review and `target-<id>` SINGLE rows) and exposes `itemByKey`/`menus.items`; `stores/frame-resolvers.js` registers `combat.items`/`combat.item`; `stores/elosern/view.js` resolves the item subject for the stage step; `stores/elosern/stage_targets.js` accepts the scalar `target_id` row shape.
  - Wire payloads are the closed v7 union only: `{kind:"item", payload:{item_key}}` for NONE/SELF (the key is absent, never null) and `{kind:"item", payload:{item_key, target_id}}` for SINGLE, all inside the guarded envelope read at submit time.
  - Evidence: Node gate `combat_menu.test.js` (stock frame quantity/summary/committed reason, NONE/SELF payloads, SINGLE `target_id`, no-candidate disabled row, envelope) and `hud_dock_menus.test.js`/`dock_panes.test.js`/`app_client_scene_overview.test.js` root geometry; Vitest `tests/store/party_items_tactics.test.js` (companion-only stock, no-effect reason, SELF and SINGLE submission); `tests/frame-resolvers.test.js` source table.

## 2. Bounded implementation and evidence (1h)

- [x] 2.1 Enable Defend/Dodge/Taunt rows with authoritative availability and stage enemy selection; test zero-cost display, valid target loss and no fake effects on draft save.
  - `tacticModel`/`tacticRootRow`/`tacticMenu` read the committed `choices.tactics` rows verbatim (label, `enabled`, `reason`, `targets`); `combat.tactic` renders Defend/Dodge as one `確認<名稱>` row and Taunt as the stage single-enemy step. A tactic the panel does not offer stays visible, disabled and inert; 挑釁's subject shape is the closed vocabulary's client-side fact (`single`) so the stage step stands.
  - Evidence: Node gate (root order/availability, `tactic-confirm` payload, Taunt target payload, disabled reason, unknown key) and Vitest (Defend/Dodge one inert command, Taunt target payload, unavailable action sends nothing). No consumption, cost or effect is applied client-side anywhere in the path.

## 3. Bounded implementation and evidence (1.5h)

- [x] 3.1 Route in-combat drawer use through the same actor command flow while preserving free bag/equipment operations; test no actorless use bypass, no companion equipment UI and revalidation after equipment changes.
  - `components/InventoryPanel.vue` gains the `combat` prop (an enabled `inventory.use` emits at once there instead of opening the local confirmation); `composables/intents.js` routes that intent to `store.useCombatItem`, which closes the drawer and opens the same `combat.item` review/target frame the 道具 row opens; `AppClient.vue` passes `:combat`. `inventory.toggle_equip`, inspection and disabled rows are byte-identical to before, and no companion equipment surface is added.
  - Evidence: Vitest `tests/world/inventory_panel.test.js` (combat: immediate emit, no dialog, toggle unchanged, disabled/inspect rows silent) and `tests/store/party_items_tactics.test.js` (bag → item frame → one `combat.command`, `inventory.use` never sent, toggle still free; an unknown item is refused and a vanished item pops its frame).

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Extend warnings and focus/lock state to item/tactic paths; test duplicate click, cancel/back, actor switching, stale inventory and preserved confirmed drafts.
  - `askCrossSide(kind, form, focusKey, command, display)` + `evaluateCrossSide`/`factsFor`/`committedSubject` take the submitted kind's committed facts, candidates and label; the held record carries `subjectKind`/`subjectKey` and still binds actor, session, round revision, draft version and frame identity. `settleCrossSide` revalidates the subject (availability, candidate membership, frame subject parameter), so an equipment change that drops or disables the item cancels the question unsent.
  - Evidence: Vitest hostile-item-on-ally (`否`/Escape cancel with nothing sent, `是` sends the held command once), beneficial-item-on-enemy wording, stale item frame pop, stale held-warning drop, actor switch dropping the open item frame, and `cross_side_confirm.test.js`/`party_command_selection.test.js` unchanged skill behaviour; Node gate's router repeat/lock cases.

## 5. Bounded implementation and evidence (1h)

- [x] 5.1 Add real component/stories and bounded browser journey for companion item and tactics; update client command docs, canonical IDs and shard ownership.
  - Stories: every combat panel carries the actor's committed stock and basic actions; `CombatItemStock`, `CombatItemSelfUse`, `CombatItemTargetStep`, `CombatItemAllyWarning`, `CombatTacticConfirm`, `CombatTauntTargetStep` (and the disabled-command story now focuses the sealed tactic).
  - Browser: `CombatMenuBrowserTest.test_item_and_tactic_choices_send_the_actor_command` (keyboard only; injected stock, 道具 rows with quantity/summary/committed reason, one guarded `item` command, one `tactic` command, no `inventory.use`), registered in `.github/browser-shards.json` shard 0. Execution stays CI-owned.
  - Docs: `web/webclient-app/AGENTS.md` (stage-target subjects, the item/tactic card flows, the bag routing rule) and `docs/development/frontend-vue-architecture.md` (new section; the root inventory line corrected).
  - Canonical IDs: this change adds no main-spec requirement (its delta is MODIFIED plus one ADDED requirement that only reaches `openspec/specs/` at archive), so no `covers_requirement` ID is migrated; the browser method annotates the existing canonical `webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy`. `tools.contract_gate` traceability stays fully covered.

## 6. Integration gate (1h)

- [x] 6.1 Run focused Node/Vitest/item-adapter tests and one bounded browser method plus tools.contract_gate; verify quantities change only from canonical committed panels.
  - Evidence: `node --test web/static/webclient/js/tests/*.test.js` (554 pass); `vitest run` (180 files, 2490 tests pass); `pnpm run build-storybook` and `pnpm run showcase-coverage` (74/74 webclient components, 33/33 GM components); `uv run --locked python -m tools.contract_gate` (traceability, observability, test-data, manifests, contracts all pass); `openspec validate webclient-party-items-tactics --strict`.
  - Quantities are read only from the committed panel: the 道具 row composes `label ×quantity` from the server's `choices.items`, and no client path writes, decrements or predicts a quantity (the item command is a draft declaration; consumption stays with the resolved initiative action).
  - Archive order: this change retires the `not_implemented` placeholder and preserves the client-local Flee/Forfeit rows, so it must sync to `openspec/specs/` **before** `webclient-party-exit-confirmation`, whose MODIFIED requirement replaces that root wording with Retreat/Surrender and the `combat.exit_confirm` route.
