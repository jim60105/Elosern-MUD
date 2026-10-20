# Tasks

Total estimate: **7.5 hours**, including implementation, focused verification, documentation and integration.

Current status after the `possession-shop-access` follow-up is **5/5 verified tasks**. The final section records the former shop gap's successful re-check and supersedes the earlier blocked handoffs. The ordinary pre-sync contract gate still reports the new active-delta requirement as unknown; proposed-contract checking passes, and the archive owner must run the ordinary gate after synchronization.

## 1. Help content (1.5h)

- [x] 1.1 Add the 隊伍 help section (follow rules, transfer rules, combat restrictions, 系譜 legend with shape and text, one-price shop convention, P B C K L J M hotkeys) and its story; verify a Vitest content test and that no party or shop window renders rule prose.

Verified with `pnpm test web/webclient-app/tests/overlays/help_overlay.test.js web/webclient-app/tests/data/party_member_tab.test.js web/webclient-app/tests/data/party_window.test.js web/webclient-app/tests/world/shop_window.test.js`: 4 files, 71 tests passed. Help renders without store state or interactive controls; existing member/shop tests retain their rule-prose absence assertions. `Overlays/HelpOverlay/PartyRules` uses the real renderer.

## 2. Residue sweep (1h)

- [x] 2.1 Search for any remaining reference to the seven deleted components (code, stories, CSS, `.elosern-root` duplicates, tests, specs, manifest) and remove it in its owning change if found; verify `pnpm run build-storybook`, `pnpm run showcase-coverage` and `tests.test_webclient_frozen_contract`.

The exact-name and kebab-case selector sweep covered `web/webclient-app`, `web/static/webclient`, top-level tests, main specs and the actual manifest at `web/webclient-app/component-manifest.json`. No retired component files, imports, registered stories, manifest entries or production CSS selectors remain. Stale implementation comments and client instructions now name the current skill tab and party/shop windows.

Intentional matches remain in negative-presence tests (`deferred_surfaces_absent.test.js`, `app_client_drawers.test.js`), the showcase's governed-deletion requirement, capability names such as `party-inventory-panel`, and historical archived specs/design prototypes. These are retirement evidence or different identities, not live components. Current main-spec wording remains stale in `webclient-skillbook-casting`'s Purpose, two HUD scenario headings, and the action-dispatch scenario's historical change list. Main specs were not edited by this apply worker. The Purpose correction remains an owning archive/spec-maintenance prerequisite, so this task is not marked complete.

`pnpm run build-storybook` succeeded; `pnpm run showcase-coverage` reported all 78 game and 33 GM components covered with no unlisted title. The frozen contract initially passed 9 tests. After adding the help browser method, its accessibility-attribute selector exposed a frozen-hook scanner failure; the method now uses the section's accessible region name instead, without adding a hook or weakening the audit.

## 3. Assembled acceptance (4h)

- [x] 3.1 Run the agent-browser journey: buy potions for 艾拉, transfer some to 卡恩, re-equip 艾拉, cast a field heal as 艾拉, have 艾拉 open combat on a monster through the 開戰並施放 confirmation (cancel once, then confirm) and finish the encounter, possess 艾拉 and walk her through an exit confirming the player's body and 卡恩 follow, and confirm the party window, shop and navigation are unchanged, then in combat re-equip a companion and observe transfer disabled with 戰鬥中無法交換物品; record each step's committed state.
- [x] 3.2 Exercise each text command once in a live session (`給`, `取回`, `裝備 = 成員`, `買`/`賣 = 成員`, `使用 = 成員`, `cast 由 成員`, `修煉 = 成員`, `狀態`, `技能`, `系譜`) and record the transcript lines.

### Initial runtime evidence and unmet prerequisites (historical, before blocker fixes)

An isolated localhost `ManagedServer` with existing `store_open_companion` and `COMPANION_FIELD_CAST` fixture flags was opened through headless `agent-browser`. It supplied commander 蒼雀 (`#1`), preset companion 燼雀 (`#3`, not co-located) and shop companion 艾拉 (`#110`). No 卡恩 exists. No state was injected into the client, and no Django shell or direct persistent-state repair was used.

The exact journey remains open:

1. **Buy potions for 艾拉: observed.** In the actual shop, select 艾拉, select 熾焰噴射劑, set quantity 3 and activate 買給艾拉. The committed `party_inventory` names member 110, `t_ember_spray.held=3`, and purse `1000 → 976`; stock falls `18 → 15`.
2. **Transfer some to 卡恩: blocked.** The required named companion is absent; the console has no NPC-create/rename or party-binding verb.
3. **Re-equip 艾拉: partially observed through text, not the required UI journey.** Buy the canonical `t_thorn_knife` and equip it for 艾拉. Committed held count is 1, `equipped_count=1`, and its give descriptor is disabled with `已裝備的物品無法交換；請先卸下。`.
4. **Field heal as 艾拉: blocked.** The existing heal fixture grants `t_hush_mend` to 燼雀, not 艾拉; no console verb grants skills. The actual member-cast command refuses an unowned skill.
5. **Cancel/confirm 開戰並施放, finish the encounter: not reached.**
6. **Possess 艾拉 and traverse with the owner's body and 卡恩: not reached.**
7. **Compare party/shop/navigation while possessed: not reached.** Trading must retain its existing possession refusal, with no purse/inventory mutation.
8. **In-combat companion re-equip and transfer-disabled reason: not reached.**

An attempt to co-locate the existing preset companion through the permitted console path, `POST /gm/api/console/teleport {"target":"#3","room":"#106"}`, returned `snapshot_failed`, with no mutation. The managed runtime's server log reports `AttributeError: 'Settings' object has no attribute 'GM_SAVES_ROOT'` in `server/saves/snapshot.py:138`; its startup save-report step is degraded for the same reason. The design requires defects to be resolved in owning follow-ups and acceptance to remain open. No snapshot policy or rule was bypassed.

The shop's actual potion buy/sell prices were 8/6 copper. Help therefore explains only the required single-price-per-page convention, without inventing the parent design's unverified blanket half-price claim. No pricing behavior changed.

### Live text transcript

Commands were sent through the real authenticated Evennia text transport; incoming text was observed without replacing dispatch handlers. The first give used the visible command input. Registry keys were then read from committed shop/character panels.

| Command | Actual response / committed observation |
| --- | --- |
| `給 熾焰噴射劑 = 艾拉` | `你把 1 個熾焰噴射劑交給了艾拉。` |
| `取回 熾焰噴射劑 = 艾拉` | `你從艾拉那裡取回了 1 個熾焰噴射劑。` |
| `買 t_thorn_knife 1 = 艾拉` | `你買了 1 個 t_thorn_knife，花費 122 銅，剩餘 854 銅。` |
| `裝備 t_thorn_knife = 艾拉` | `艾拉裝備了 荊刺小刀（魔力 +4｜施法消耗 −5%）。` |
| `賣 t_ember_spray 1 = 艾拉` | `你賣了 1 個 t_ember_spray，獲得 6 銅，目前 860 銅。` |
| `使用 t_ember_spray = 艾拉` | `你的體力已經全滿。` Item not consumed; successful member use remains unverified. |
| `cast t_hush_mend=蒼雀 由 艾拉` | `你不會使用這項技能。` Successful member casting remains unverified. |
| `修煉 basic_attack = 艾拉` | `艾拉將在下次休息時修煉「合成基本攻擊」。` Committed active row has `booked=true`. |
| `狀態 艾拉` | `狀態：艾拉` with HP `110／110`, MP `90／90`, SP `105／105`, and magic `10（基礎 6｜荊刺小刀 ＋4）`. |
| `技能 艾拉` | `技能：艾拉`; 合成逃跑, 合成基本攻擊 and 噤聲輕撫 all appear at level 0; passive section says `（無）`. |
| `系譜 艾拉` | `你的技能系譜暫時無法閱讀。` Successful lineage rendering remains unverified. The GM reader log also reports a lineage-query cycle refusal. |

Additional exploratory commands using a display name and an incorrect guessed registry key returned `商店不賣這個物品。`; practice on an unowned skill returned `PRACTICE_SKILL_UNKNOWN`. They are not success evidence. Final committed 艾拉 stock is two potions and one equipped knife, purse 860, with `basic_attack` booked. Screenshots and the full raw transcript stay in ignored scratch space, never committed. Task 3.2 remains open because refusals alone do not establish successful text parity.

## 4. Integration (1h)

- [x] 4.1 Register the help browser method in `.github/browser-shards.json`, annotate canonical IDs for the added requirement, run `tests.test_evennia_test_optimization_contract`, `tests/test_command_docs.py`, `uv run --locked python -m tools.contract_gate` and `openspec validate party-management-acceptance --strict`.

The real help method, `web.tests.browser.test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_help_party_rules_are_static_and_absent_from_the_bag`, is registered beside the existing help opener method in exactly one shard. It opens help through the actual navigation control, asserts every party-rule category and all seven keycaps, proves no action is dispatched by reading help, closes it, opens the real bag and checks that rule prose is absent. Its literal requirement ID was obtained with `tools.spec_traceability list --json-output` on a scratch equivalent tree with the proposed requirement deltas applied; no main spec was synchronized or edited.

Final exercised checks:

- Five focused Vitest files passed, 100 tests total (help, member/window, shop, skill tab).
- `pnpm run build` passed. The final managed help method passed, 1 test, using `uv run --locked --env-file=.env.party-acceptance.local python -m web.tests.browser.unittest_driver <method>`.
- `uv run --locked python -m unittest tests.test_evennia_test_optimization_contract tests.test_command_docs` passed 40 tests.
- `uv run --locked python -m tools.contract_gate` passed both lints, manifests and all 18 repository contracts (including frozen/shard ownership), but remains nonzero solely for the new requirement's pre-sync unknown ID. The ordinary main-spec index contains 2,349 requirements and does not yet contain this active delta. No checker exception or allowlist was added.
- Against the scratch equivalent delta-applied specs and current tests, `tools.spec_traceability --repo-root <scratch> check --json-output <report>` passed, with 2,350 requirements covered, zero uncovered and zero errors. This is proposed-contract evidence, not a claim that the ordinary pre-sync gate passed.
- `openspec validate party-management-acceptance --strict` passed.
- Both writing-style and Traditional Chinese content linters passed the new authored help prose with zero errors or warnings.

The initial managed help run failed before loading any SPA because the live `dist` bundle had not been built. Building it resolved that environment prerequisite; it is unrelated to the runtime defects above. The owned runtime and browser were shut down successfully and the throwaway runtime launcher was deleted.

### Pre-implementation review dispositions

The blocking review identified contradictory no-authored-help contracts. Complete MODIFIED deltas now permit only the static party reference while retaining the deferred category-to-entry guide prohibition. Its non-blocking findings were adopted: pre-sync and proposed-contract traceability are reported separately; possession's existing shop refusal is an explicit remaining journey assertion; residue matches are classified rather than deleting absence tests or historical evidence. The lineage suggestion was adopted as shape-and-text descriptions, with 可解鎖 separate from the three diamond states and no rule text drawn as a keycap.

### Post-implementation review disposition

The reviewer inspected the static implementation, tests, docs, proposed deltas and all 772 lines of the raw feature diff through `27a033bb`. Its initial inability to obtain a Git diff was resolved by supplying that complete read-only diff artifact to the same reviewer. The completed review found no blocking issues and no additional actionable non-blocking findings or suggestions. Approval covers only the static help/test/docs work; it explicitly leaves the documented runtime prerequisites, remaining task checkboxes, synchronization and archive unapproved. No finding was ignored or silently deferred.

That handoff had 1/5 verified tasks complete. The ordinary contract gate must be reassessed after the owning synchronization, and the named assembled journey and successful text parity must be completed after their real fixture/runtime prerequisites are resolved.

## Resumed verification after owning blocker fixes

The feature branch was rebased without conflict onto primary `72f22a8523e0322ca5647d6221f04db5d54ec2aa`, incorporating all six archived owning fixes. The repeated residue sweep confirms that the stale current-contract Purpose, HUD scenario headings and action-dispatch wording have been corrected by their owner. Remaining name/selector matches identify explicit retirement assertions, historical routing comments or unrelated protocol capability names; no live retired component, story, manifest entry or CSS rule remains.

Task 2.1 verification after rebase: Storybook build passed; showcase coverage passed for all 78 game and 33 GM components; `uv run --locked python -m unittest tests.test_webclient_frozen_contract` passed all 9 tests. The live client bundle was rebuilt for the resumed runtime journey.

### Resumed task 3.1 graphical journey

The dedicated `ELOSERN_BROWSER_PARTY_MANAGEMENT_ACCEPTANCE=1` synthetic runtime supplied commander 蒼雀 (`#1`), 艾拉 (`#12`), 卡恩 (`#13`), the merchant and monster (`#11`) in store room `#6`. Headless `agent-browser` operated the real shop, party window, skill-use card, combat card, possession action and exit compass. Committed snapshots, screenshots and read-only GM projections remain in ignored `tmp/`, not committed.

| Step | Observed committed state |
| --- | --- |
| Buy three potions for 艾拉 | Activate 買給艾拉 with quantity 3. Her potion count increases `4 → 7`, merchant stock `18 → 15`, and purse `1000 → 976`; clock remains 12:00:00. |
| Transfer two to 卡恩 | Use the quantity control and 交給卡恩. Settled holdings show 艾拉 `7 → 5`, 卡恩 `1 → 3`, with purse and clock unchanged. The immediately captured transfer snapshot preceded settlement; the subsequent bag and final holdings establish the committed counts. |
| Re-equip 艾拉 | Select 燼微短刃 and 裝備（替換 荊刺小刀）. Subsequent committed rows show `t_cinder_dirk.equipped_count=1` and `t_thorn_knife.equipped_count=0`, with the clock still 12:00:00. |
| Field heal as 艾拉 | Select 靜謐癒合, 施放, then 蒼雀. 艾拉 MP `90 → 80`; commander HP `95 → 114`; party regeneration also changes 艾拉 HP `85 → 91` and 卡恩 `80 → 86`. Clock reaches 12:00:06. These are observed totals, not an assertion that all recovered HP came from the spell. |
| Cancel opening once | Select 燼火爆發 and 驗收燼蟲（開戰）, then 取消 in 開戰確認. Mode remains exploration, MP remains 80, clock remains 12:00:06, and no combat draft exists. |
| Confirm opening | Reopen the same monster confirmation and activate 開戰並施放. Combat draft contains actor 12's `t_ember_burst` targeting 11; the other three members still require choices. 艾拉 remains at MP 80 until the round settles. |
| Finish encounter | Confirm defense for the other members, settling the opening round and charging 艾拉 once (`80 → 69` MP). Then select party attacks through the real target step. Encounter ends in exploration at 12:00:18; 艾拉 MP remains 69 and purse 976. |
| Possess and compare party/navigation | Activate 附身 for 艾拉; result is `possessed` / `你附身到了艾拉身上。`, controlled identity 12. Reopened party window retains its five tabs, ordered member rail, viewed 艾拉 and party purse 976; its action becomes 解除附身 and leave carries the possession restriction. Exploration navigation retains 隊伍／任務／地圖 and the same tools/settings. |
| Possessed shop comparison | **Evidence gap remains.** In the same merchant room, the actual merchant card disables 商店 with `附身狀態下無法進行交易。`. Committed services v7 has `available:true`, `host:null`, `shop:null`, zero stock/sellable totals and wallet 976. Calling only the existing view-local shop opener for inspection renders the 商店 heading and 購買／出售 tabs, without the earlier member rail or stock. This does not establish the required unchanged shop presentation; no trade refusal or panel fact was bypassed. |
| Traverse while possessed | Focus the real exit compass, select the exit and confirm movement through 後門. Controlled 艾拉 reaches 商鋪後院 (`#7`). Protected GM read endpoints independently show commander `#1`, 艾拉 `#12` and 卡恩 `#13` all located in room `#7`. |
| In-combat companion re-equip and transfer restriction | Return possession and traverse back through the real exit. For a second encounter, use protected `set_gauge {target:"#11",gauge:"hp",value:40}`; it succeeds with `snapshot.taken=true`, save `20261020T092107-3df123`. Reopen combat through 艾拉's confirmation, then use the party bag to replace 燼微短刃 with 荊刺小刀. Settled rows show the replacement equipped while round revision remains 0 and clock remains 12:01:18. Select the potion: holdings remain 艾拉 5 / 卡恩 3, every receive descriptor is disabled, the visible bar states `戰鬥中無法交換物品。`, and no give controls or quantity stepper are offered. |

Task 3.1 stays unchecked solely because the literal shop-presentation invariance has not been established. The possession trade refusal is expected; it is not evidence that the shop contents remain present. The existing design requires an owning follow-up for any actual defect, not a change to these acceptance criteria.

### Resumed task 3.2 successful live text transcript

A fresh dedicated runtime was used to retain the fixture's wounds and actor-owned skills without manual repairs. Commands traversed the actual authenticated Evennia text transport. An interruption required reconnecting the browser before the final two read commands; the same runtime and persistent character state were retained. The following nine earlier successful responses are in the tool transcript, and the final skill/lineage responses plus committed state were saved to ignored scratch space.

| Command | Actual successful response |
| --- | --- |
| `給 熾焰噴射劑 = 艾拉` | `你把 1 個熾焰噴射劑交給了艾拉。` |
| `取回 熾焰噴射劑 = 艾拉` | `你從艾拉那裡取回了 1 個熾焰噴射劑。` |
| `裝備 t_cinder_dirk = 艾拉` | `艾拉裝備了 燼微短刃（魔力 +4｜施法消耗 −5%），原本的 荊刺小刀 已收回背包。` |
| `買 t_ember_spray 1 = 艾拉` | `你買了 1 個 t_ember_spray，花費 8 銅，剩餘 992 銅。` |
| `賣 t_ember_spray 1 = 艾拉` | `你賣了 1 個 t_ember_spray，獲得 6 銅，目前 998 銅。` |
| `使用 t_ember_spray = 艾拉` | `你使用了「熾焰噴射劑」，恢復了 25 點生命值。` |
| `cast t_hush_mend=蒼雀 由 艾拉` | `艾拉 對 蒼雀 恢復了 10 點生命。` followed by `艾拉 消耗了資源。`, `艾拉 的能力值發生了變化。`, `艾拉 累積了技能熟練度。` |
| `修煉 t_hush_mend = 艾拉` | `艾拉將在下次休息時修煉「靜謐癒合」。` |
| `狀態 艾拉` | `狀態：艾拉`, HP `110／110`, MP `80／90`, SP `105／105`, magic `10（基礎 6｜燼微短刃 ＋4）`, no conditions. |
| `技能 艾拉` | `技能：艾拉`; `靜謐癒合 Lv.0（熟練 1/50）［修煉中］`, `燼火爆發 Lv.0（熟練 0/50）` with `解鎖：燼流星 Lv.3`, plus the innate/other owned actives. |
| `系譜 艾拉` | `技能系譜：已完成 0 / 5 樹`; fire graph `火（1/2）根：燼火爆發` includes `燼流星 Lv.0　← 燼火爆發 Lv.3　需「燼火爆發 Lv.3」`; separate heal graph contains `靜謐癒合 Lv.0（本階 1/50）`; the other three owned singleton graphs also render. No unavailable response occurs. |

Final committed member panel confirms purse 998, 艾拉 HP 110 / MP 80, three potions, equipped 燼微短刃, unequipped 荊刺小刀, and `t_hush_mend` with `booked:true`, `xp_into_level:1`, `xp_to_next_level:49`. This replaces the earlier refusal-only evidence for task 3.2. The interrupted launcher had left owned server processes running; cleanup reconstructed ownership from their runtime environment and matching pidfiles, then used `ManagedServer.stop()` to stop only that runtime and remove its private roots.

The shop gap is also source-confirmed: `world/rules/service_view.py:897–900` forces `guild`, `shop` and `host` to `None` when `owner is not None`; `web/webclient/presentation/affordances.py:501–509` disables the merchant service entry under possession. `ShopWindow.vue` therefore follows its absent-shop branch. This was recorded for an owning follow-up; the acceptance implementation does not weaken possession trade authorization or fabricate shop facts.

### Resumed task 4.1 integration evidence

The existing help method registration and canonical annotation are unchanged and have exact shard ownership. Final focused Vitest execution passed **102 tests in five files** after the owning fixes. The managed help browser method passed against the rebased live runtime. `tests.test_evennia_test_optimization_contract` plus `tests.test_command_docs` passed **40 tests**, and strict OpenSpec validation passed.

The required ordinary `uv run --locked python -m tools.contract_gate` was executed and returned nonzero solely for the expected pre-sync new requirement ID at the help method's decorator: **2,350 current main requirements covered, zero uncovered, one unknown-ID error**. Both lints, manifests and all **18 repository contracts** passed. The equivalent proposed-contract tree, rebuilt from the rebased main specs plus both complete deltas and current tests, passed canonical-ID listing and static checking with **2,351 requirements covered, zero uncovered, zero errors**. Task 4.1's registration, annotation and requested checks are performed; its checked box does not claim the ordinary pre-sync gate is green or replace the archive owner's mandatory post-sync gate.

### Resumed final blocking review

A fresh blocking `rubber-duck` review read the complete 838-line raw feature diff from `72f22a85` to `e807b211`, all 145 lines of this evidence as then committed, design/deltas and shortcut integration. It found **no blocking or non-blocking issues and no additional suggestions**. Its verdict explicitly retains task 3.1 as incomplete for the possessed-shop presentation gap and requires the ordinary contract gate to pass after owning spec synchronization before completion/archive. Those conditions are accepted, not waived. This was a read-only review of implementation and recorded observations, not an independent runtime rerun. Earlier pre-implementation findings and their dispositions remain recorded above; the resumed review adds no unresolved review finding.

## Final closure after possession-shop-access

The feature branch was rebased without conflict onto `cd58e69fbf9c7aed44de08f7f2c527476663f823`, which includes the archived owning fix `possession-shop-access`. This acceptance adds no replacement shop test or gameplay change. The earlier source diagnosis and refusal observations describe the pre-fix runtime only.

### Closing task 3.1's exact remaining gap

A fresh isolated synthetic runtime initialized only `ELOSERN_BROWSER_PARTY_MANAGEMENT_ACCEPTANCE=1` before login. Headless `agent-browser` opened it at the large acceptance viewport, 2560 × 1440. The session compared the actual merchant and party windows before possession, selected `艾拉`, used the real 附身 control, then reopened those windows through their live controls after the possession transition settled. No GM intervention or persistent-state patch was needed for this re-check.

| Observation | Committed state and rendered result |
| --- | --- |
| Before possession | Selected member 艾拉 (`12`), party purse 1,000, four stock rows, potion stock 18 and 艾拉 holding four potions. |
| Possessed party window | Same member order and selected `艾拉`; same five tabs, `成員 / 背包 / 狀態 / 技能 / 系譜`. The action becomes 解除附身 and leaving is disabled, as required by the possession context. |
| Navigation | Exact same nine labels in the same order, `隊伍 / 任務 / 地圖 / 信件 / 圖鑑 / 稱號冊 / 角色肖像圖庫 / 說明 / 設定`. |
| Possessed merchant entry | The real merchant's 商店 entry is enabled with no disabled reason. The committed service-entry list contains only `shop`, with no guild entry. |
| Possessed shop | Merchant host remains available, `guild:null`, real non-null `shop`, `member_id:12`, owner purse 1,000 and all four committed stock rows byte-for-byte equal to the pre-possession rows. The rendered shop has 購買 / 出售 tabs, the full four-member rail, 為艾拉挑選 and actual stock/detail regions. |
| Buy one while possessed | The real 買給艾拉 control settles potion stock 18 → 17, 艾拉 holdings 4 → 5 and the commander purse 1,000 → 992. The bag agrees on member 12 and purse 992. |
| Sell one while possessed | The real 出售 control settles potion stock 17 → 18, 艾拉 holdings 5 → 4 and the commander purse 992 → 998. The bag agrees on member 12 and purse 998; possession remains active and mode remains exploration. |

The comparison waited for committed state. The transition closes the drawer; reopening it is the normal interaction, and a transient pre-settlement snapshot is not counted as the final window. Full read-only view/snapshot evidence and screenshots remain in ignored scratch files, `tmp/party-management-possessed-shop-proof.json`, `tmp/party-management-possessed-shop-final.png` and `tmp/party-management-possessed-sale-final.png`.

This re-check closes the only gap in the preceding assembled journey. Its already-recorded purchase/transfer, equipment, field-heal, cancel/confirm and victory, possessed exit with the commander's body and 卡恩 following, combat equipment, and disabled-transfer steps remain the exercised evidence for those steps. The complete journey is established by those recorded runs together; this final run does not claim to repeat them all.

### Final integration evidence

The owning automated journeys were reused without duplication. Both `ShopCompanionJourneys.test_buy_potions_for_a_companion` and `test_possessed_shop_opens_at_the_large_acceptance_viewport` passed through the managed browser driver, **2 tests**, covering actual possessed buy/sell settlement and the large-viewport opening. The acceptance's own managed static-help method also passed again, **1 test**.

The final focused Vitest run passed **102 tests in five files**. The rebuilt client passed. Repository ownership, command-documentation and frozen contracts passed **49 tests** together. `openspec validate party-management-acceptance --strict` passed.

The ordinary `uv run --locked python -m tools.contract_gate` again returned nonzero only for the new help requirement's pre-sync unknown ID. It reported **2,352 current main requirements covered, zero uncovered, one error**. Both lints, manifests and all **18 repository contracts** passed. A fresh scratch equivalent of the rebased main specs plus the two complete deltas and current tests passed canonical listing and static checking with **2,353 requirements covered, zero uncovered, zero errors**. An initial scratch-only heading parser produced duplicate headings; correcting that temporary parser resolved the scratch error without changing repository specs or gate policy.

The headless browser was closed and the owned managed runtime exited cleanly with status 0 through `ManagedServer.stop()`, which removed its private roots. The temporary launcher was removed. No main spec, primary checkout or unrelated worktree was edited; synchronization and archive remain the owner's next phase.

### Final full-change review and correction

The final blocking review read the complete 879-line feature diff against `cd58e69f`. It found one blocking issue in the acceptance's own authored help, which still said `附身時無法交易`, and in the two tests requiring that obsolete claim. That sentence had become false after the owning shop fix. There were no additional non-blocking findings or suggestions.

The finding was adopted. The static shop row now states `附身時仍可交易`, retaining the single-price convention and explaining that purchases debit the party purse and sales credit it. Both the Vitest and real browser method require the supported trading statement and both purse clauses, and explicitly reject the obsolete prohibition. This changes only help and its assertions; the owning live buy/sell evidence and gameplay rules remain unchanged.

After correction, the five focused Vitest files passed again, **102 tests**, the client rebuild passed and the corrected managed help browser method passed again, **1 test**. Both content linters passed the corrected player-facing sentence with zero errors or warnings. The final technical evidence has zero writing-style errors or warnings and zero Chinese-content errors; its repeated-English-word warnings are in English technical documentation, which follows `AGENTS.md`, and are intentionally retained.
