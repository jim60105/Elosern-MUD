# Tasks

Total estimate: **7.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Help content (1.5h)

- [x] 1.1 Add the 隊伍 help section (follow rules, transfer rules, combat restrictions, 系譜 legend with shape and text, one-price shop convention, P B C K L J M hotkeys) and its story; verify a Vitest content test and that no party or shop window renders rule prose.

Verified with `pnpm test web/webclient-app/tests/overlays/help_overlay.test.js web/webclient-app/tests/data/party_member_tab.test.js web/webclient-app/tests/data/party_window.test.js web/webclient-app/tests/world/shop_window.test.js`: 4 files, 71 tests passed. Help renders without store state or interactive controls; existing member/shop tests retain their rule-prose absence assertions. `Overlays/HelpOverlay/PartyRules` uses the real renderer.

## 2. Residue sweep (1h)

- [ ] 2.1 Search for any remaining reference to the seven deleted components (code, stories, CSS, `.elosern-root` duplicates, tests, specs, manifest) and remove it in its owning change if found; verify `pnpm run build-storybook`, `pnpm run showcase-coverage` and `tests.test_webclient_frozen_contract`.

The exact-name and kebab-case selector sweep covered `web/webclient-app`, `web/static/webclient`, top-level tests, main specs and the actual manifest at `web/webclient-app/component-manifest.json`. No retired component files, imports, registered stories, manifest entries or production CSS selectors remain. Stale implementation comments and client instructions now name the current skill tab and party/shop windows.

Intentional matches remain in negative-presence tests (`deferred_surfaces_absent.test.js`, `app_client_drawers.test.js`), the showcase's governed-deletion requirement, capability names such as `party-inventory-panel`, and historical archived specs/design prototypes. These are retirement evidence or different identities, not live components. Current main-spec wording remains stale in `webclient-skillbook-casting`'s Purpose, two HUD scenario headings, and the action-dispatch scenario's historical change list. Main specs were not edited by this apply worker. The Purpose correction remains an owning archive/spec-maintenance prerequisite, so this task is not marked complete.

`pnpm run build-storybook` succeeded; `pnpm run showcase-coverage` reported all 78 game and 33 GM components covered with no unlisted title. The frozen contract initially passed 9 tests. After adding the help browser method, its accessibility-attribute selector exposed a frozen-hook scanner failure; the method now uses the section's accessible region name instead, without adding a hook or weakening the audit.

## 3. Assembled acceptance (4h)

- [ ] 3.1 Run the agent-browser journey: buy potions for 艾拉, transfer some to 卡恩, re-equip 艾拉, cast a field heal as 艾拉, have 艾拉 open combat on a monster through the 開戰並施放 confirmation (cancel once, then confirm) and finish the encounter, possess 艾拉 and walk her through an exit confirming the player's body and 卡恩 follow, and confirm the party window, shop and navigation are unchanged, then in combat re-equip a companion and observe transfer disabled with 戰鬥中無法交換物品; record each step's committed state.
- [ ] 3.2 Exercise each text command once in a live session (`給`, `取回`, `裝備 = 成員`, `買`/`賣 = 成員`, `使用 = 成員`, `cast 由 成員`, `修煉 = 成員`, `狀態`, `技能`, `系譜`) and record the transcript lines.

### Observed runtime evidence and unmet prerequisites

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

- [ ] 4.1 Register the help browser method in `.github/browser-shards.json`, annotate canonical IDs for the added requirement, run `tests.test_evennia_test_optimization_contract`, `tests/test_command_docs.py`, `uv run --locked python -m tools.contract_gate` and `openspec validate party-management-acceptance --strict`.

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
