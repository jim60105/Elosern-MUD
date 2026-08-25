## 1. Freeze what this wave inherits and enumerate what it breaks

- [ ] 1.1 Confirm H1 is archived and H3 is `Done` in the roadmap's delivery table before any file is touched; H4 may not start earlier (roadmap §9)
- [ ] 1.2 Record the preserved identifiers this change must not move (`#action-dock` with its `data-mode`, `tabindex` and listbox composite role, `#combat-row-<i>`, `data-item-key`, the `action-*` / `target-*` item keys, `#elosern-action-live`, `#elosern-offline-overlay`, `#inputfield`, `#narrative-unread`, `data-testid="narrative-feed"`) and add the Vitest assertion that each survives the drawer restructure
- [ ] 1.3 Grep `web/tests/browser/` for `.quest-board__`, `data-testid="quest-board"`, `data-testid="shop`, `data-testid="inventory`, `data-testid="skill`, `data-testid="lore`, `data-testid="character-panel` and record the hit list in the change: `test_browser_services.py` (the `_wait_services_available` gate at :79-95 and its 17 call sites, `.quest-board__title` at :174) and `test_browser_pointer.py` (`.quest-board__action` at :512). They are re-mapped in group 9
- [ ] 1.4 Record the current `component-manifest.json` count left by the preceding waves; H4 extends it by exactly three and updates the frozen-count assertion to the resulting number

## 2. The shared focus trap

- [ ] 2.1 Add `components/focus-trap.js`: a documented focusable-selector query, forward/backward `Tab` cycling, an initial-focus target, and a restore-to-opener handle
- [ ] 2.2 Re-point `components/FullLogOverlay.vue` at the shared trap, replacing its hard-coded two-element cycle, with its existing Escape and focus-restore behaviour unchanged
- [ ] 2.3 Vitest: the trap cycles across a multi-control surface in both directions, ignores hidden and disabled nodes, and restores focus to the opener; the full-log overlay's existing suite still passes unchanged

## 3. The drawer shell

- [ ] 3.1 Add `components/HudDrawer.vue` with the draft's chrome: `position:fixed; top:0; right:0; bottom:0; width:min(560px,94vw)`, `--panel-solid` background, a left border and the left-cast shadow, and the `.dhead` / `.body` / `.foot` column with the body as the only scrolling region
- [ ] 3.2 Add the slide transition (`translateX(100%)` → `translateX(0)`) and the blurred scrim, both expressed through the existing `--motion-*` / `--ease-*` tokens so the reduced-motion block already covers them
- [ ] 3.3 Wire the modal contract: focus trapped on open, Escape closes and restores focus to the opener, activating the scrim closes, and the drawer's labelled close control closes
- [ ] 3.4 Register the open drawer into H1's open-surface set (`AppClient.vue`'s `openSurfaces`) so the stage recession H1 specified applies without a second mechanism
- [ ] 3.5 Storybook story with deterministic offline args: closed, open with a short body, open with an overflowing body, and open with a footer
- [ ] 3.6 Vitest: only one drawer is open at a time; the scrim is present only while a drawer is open; the stage carries the recession mark while open and loses it on close; reduced motion disables the transition while the open state still applies

## 4. The drawer controller

- [ ] 4.1 Add the store slice: `openHudDrawer(name)` / `closeHudDrawer()` over the closed set `skill | inventory | shop | quest | lore | status`, publishing `view.hudDrawer`; an unknown name is rejected, not coerced
- [ ] 4.2 Re-point `stores/elosern.js`'s `openCharacter` branch (today a no-op that only sets `activeSubDock`) at `openHudDrawer("status")`
- [ ] 4.3 Host the router's service frames: while a `service_menu.js` frame is the current frame, open the matching drawer and render that frame's rows inside it through H3's shared row renderer; leaving the surface closes the drawer, and closing the drawer pops exactly one level
- [ ] 4.4 Teardown from one place: a committed mode change out of exploration, an epoch reset, and a transport loss each close every open drawer and discard local selection, quantity and confirmation state
- [ ] 4.5 Vitest: no state exists in which a service frame is current and its drawer is closed; Escape from a hosted frame pops exactly one level; a mode change to combat closes the services drawers and leaves the status drawer openable

## 5. The three drawers the dock does not own

- [ ] 5.1 Move `SkillBook.vue` into a drawer body (`技能書`), keeping its active/passive tabs, its search and its per-skill cost/target/cast cells rendered only where the payload provides them
- [ ] 5.2 Move `LoreDrawer.vue` into a drawer body (`圖鑑`), removing its duplicated wallet line and its duplicated player-summary rows; the draft's discovered-entry compendium is not built (no `lore` panel exists)
- [ ] 5.3 Add `components/CharacterStatusDrawer.vue` (`角色狀態`): the `status`-backed vitals and full condition roster in every mode, plus the `character`-backed body (`CharacterPanel`) with its own registry-owned reason when `character` is unavailable
- [ ] 5.4 Render the disguise section as a 真值 / 顯示 comparison from `character.disguise.displayed[]` beside the true trait rows, with the standing statement that combat always resolves on true traits — never a substituted value
- [ ] 5.5 Add the single labelled control in the status drawer that opens the skill drawer, and the single labelled control in the quest drawer that opens the lore drawer
- [ ] 5.6 Assert the 親密狀態 block is absent: no arousal / wetness / shame / exposure / climax_phase / per-part sensitivity / virginity element and no placeholder standing in for one
- [ ] 5.7 Storybook stories for each of the three drawers, including the combat state of the status drawer (vitals and conditions present, character sections unavailable)
- [ ] 5.8 Vitest: the status drawer renders its `status` sections with `character` unavailable and invents nothing; the condition roster renders every committed condition with a non-colour severity glyph, its label and every numeric or derived-modifier value the payload carries

## 6. The bag and the equipment doll

- [ ] 6.1 Remove `InventoryPanel.vue`'s `equipped === true` filter and render the bounded `services.inventory.rows` listing — `display_name`, `held`, and an `equipped` marker — retitled `背包 · 裝備`
- [ ] 6.2 State the ceiling in words when the listing holds `MAX_INVENTORY_ROWS` (32) rows, and render no total otherwise; `pagination.inventory_total` is the shipped row count and is never presented as untruncated holdings
- [ ] 6.3 Add `components/EquipmentDoll.vue`: 主手 / 副手 / 盔甲 as three named boxes with an explicit empty state, an accessory group for the 0..3 `accessory` rows, and a labelled passthrough row for any other server-authored slot key
- [ ] 6.4 Do not build item rarity borders, a per-item statistics line, or a comparison tooltip; add no use / consume / equip control
- [ ] 6.5 Remove `InventoryPanel.vue`'s wallet line
- [ ] 6.6 Storybook stories: empty bag, mixed bag with equipped rows, bag at the 32-row ceiling, doll with every slot filled, doll with empty slots, doll with three accessories, doll with an unrecognised slot key
- [ ] 6.7 Vitest: no row renders a field the payload lacks; an unrecognised slot key is rendered, not dropped; the ceiling notice appears only at 32 rows; the unavailable `services` form renders the registry-owned reason and no fabricated wallet, row or slot

## 7. The two service drawers and the emptying of the right-hand stack

- [ ] 7.1 Move `ShopPanel.vue` into a drawer body (`商店`), keeping its bounded quantity form and its server-advertised maxima unchanged, and removing its wallet line
- [ ] 7.2 Move `QuestBoard.vue` into a drawer body (`任務`), and put the pointer `guild.quest_abandon` behind the same explicit two-step confirmation the dock path already requires
- [ ] 7.3 Verify every drawer affordance still emits its exact server-authored `action_id` and payload through the single store dispatch entry, and still locks under `mutationsLocked` and the offline overlay
- [ ] 7.4 Remove the six reference panels from `AppClient.vue`'s `#panel-right` slot and mount the drawer layer above the stage
- [ ] 7.5 Leave `components/HudFrame.vue`'s `hud-right` anchor, its geometry and the caption's width reservation untouched — H2 re-tenants that anchor with the minimap island, and editing it here would be a forced serialize (roadmap §7)
- [ ] 7.6 Verify at both viewports that an emptied right anchor renders no box, no border and no tab stop while H2 is unlanded
- [ ] 7.7 Vitest: no reference surface is in the DOM while every drawer is closed; each is reachable in at most two actions from the dock root; exactly one wallet rendering exists across the whole drawer layer

## 8. Manifest, showcase and the deferred-surface assertion

- [ ] 8.1 Add `Core/HudDrawer`, `Data/EquipmentDoll`, `Data/CharacterStatusDrawer` to `component-manifest.json` and update the frozen-count assertion to the resulting number
- [ ] 8.2 Run `npm run build-storybook` and `npm run showcase-coverage`; both must pass with the extended set
- [ ] 8.3 Update `tests/overlays/deferred_surfaces_absent.test.js`: remove the `\bBag\b` pattern and the "keeps the equipped-only InventoryPanel" case, documenting in the test's own comment that `services.inventory` (`world/rules/service_view.py:695-720`) backs the bag; keep Party, Intimate, EventLog, Toasts and every name the preceding waves added
- [ ] 8.4 Extend the same file to assert the drawer layer reserves nothing for a party/companion drawer, an intimate/adult collapsible, an item-rarity affordance or a discovered-lore compendium

## 9. Browser acceptance and re-map

- [ ] 9.1 Re-map `test_browser_services.py`'s `_wait_services_available` off the `[data-testid="quest-board"]` visibility gate onto the committed store state plus the drawer's own `data-testid`, with opening the drawer as the journey's first step; update all 17 call sites
- [ ] 9.2 Re-map `test_browser_services.py`'s `.quest-board__title` visibility assertion at the 1280x720 case onto the open drawer's heading
- [ ] 9.3 Re-map `test_browser_pointer.py`'s `.quest-board__action` pointer service-submission journey onto the quest drawer, asserting exactly one `guild.register` is still emitted
- [ ] 9.4 Add a browser assertion that every keyboard service journey — register, board → accept, abandon behind its confirmation, turn-in, buy and sell with their bounded quantities — completes with arrows and Enter only, with the frame rendered inside the drawer and the emitted payloads unchanged
- [ ] 9.5 Add a browser assertion that at 1440x900 and 1280x720 an open drawer is closable in one action, Escape restores focus to the opener, and no reference surface is in the DOM while every drawer is closed
- [ ] 9.6 Add a browser assertion that the stage recession mark is present while a drawer is open and cleared when the last surface closes
- [ ] 9.7 Add a browser assertion that the narrative caption is wider at both viewports than before the `hud-right` removal, and that no stage anchor overlaps another at either viewport
- [ ] 9.8 Re-run the offline-degradation regression: bundle blocked → text playable; `services` unavailable → the drawers render only the registry-owned reason with no fabricated wallet, stock, quest, lore or row

## 10. Gates and handoff

- [ ] 10.1 `npm test`, `npm run build`, `npm run build-storybook`, `npm run showcase-coverage` green
- [ ] 10.2 `node --test web/static/webclient/js/tests/*.test.js` green (the preserved menu logic is unchanged and asserted not broken)
- [ ] 10.3 `uv run --locked python -m tools.spec_traceability check` green; every new requirement carries `@covers_requirement` annotations
- [ ] 10.4 `openspec validate webclient-hud-04-reference-drawers --strict` passes
- [ ] 10.5 Rebuild `web/static/webclient/app/dist` and verify the running client at 1440x900 and 1280x720: every drawer opens, traps focus, closes on Escape, and the stage behind it recedes
- [ ] 10.6 Flip the roadmap's H4 Status cell to `Done`
