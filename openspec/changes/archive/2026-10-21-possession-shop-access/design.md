# Design

## Context

See `proposal.md` for motivation and the five deltas for acceptance contracts. This implements the user's approved Option A from 2026-10-20, with no reopening of the rejected guild/church delegation option.

The current seams were inspected on master. `commands/economy.py:56-73,185-187,224-226` refuses trades before merchant resolution; `:263-287` reads the caller's wallet directly while listing that caller's bag. The web adapters in `web/webclient/actions/service_actions.py:512-610` have equivalent early refusals, then already delegate to normal party-scoped economy rules. `world/rules/party_scope.py:153-174` resolves a live, authenticated possessed companion to the commander and rejects stale or foreign possession bindings.

`world/rules/service_view.py:864-932` already builds the player summary from the owner but combines `in_combat` and possession into a guard that nulls host, guild and shop. Its normal shop builder already accepts the viewed member and party wallet. `web/webclient/presentation/affordances.py:478-549` disables both service openers with the shop refusal, while `:552-590` decides which openers are emitted. These are separate responsibilities.

## Goals / Non-Goals

**Goals:** Keep transaction ownership and all authorization in existing deterministic rules; make the transport and presentation layers expose those rules consistently. Keep guild omission distinct from an unavailable or failed guild service.

**Non-Goals:** No new actor identity, authority abstraction, transport payload, persistence, migration, compatibility path or pricing policy. No new possession handling in guild, church, examination, dialogue, combat engagement, or quest-issuer services. Do not change delivery, private escort abandonment, party management, or other actions outside the decision. Do not edit or complete the consumer change in this work.

## Decisions

### D1. Remove adapter locks and keep the existing economy owner

Delete `_ShopCommandBase.refuse_possessed_trade` and both calls. Delete only the possession rejection branches and obsolete claims in `_buy_adapter`/`_sell_adapter`; keep local-host and schedule resolution, payload validation, party member authorization, and deterministic buy/sell delegation intact. Text without `= <member>` continues to pass the caller's identity, which is the possessed puppet. Web payloads remain exactly `{item_key, quantity, recipient_id}` and `{item_key, quantity, seller_id}`. The viewed-member selection still defaults to the commander on the web; possession must not reset or secretly change that selection. Select the acting puppet explicitly when testing its bag.

The existing rule resolves the commander and authorizes the named member for organization. Continue using that path for configured integer prices, finite stock, equipped-item protection, acquisition progress, contained mirrors, atomic snapshot/restore, and commander-keyed merchant affinity. Do not introduce a second settlement path or send a trade through text parsing. Retire the now-unused `REASON_POSSESSED_SHOP` and its message after all active callers and fixtures are converted; keep talk and engage refusal codes/messages.

The rationale is already decided: `world/rules/party.py::_effective_follow_members` includes the commander's body in possessed traversal, so normal follow keeps the commander co-located. The organizing-purpose member check still rejects a stranded member. Economy is already party-scoped and the acting body has no personal trade identity to translate. Guild/church actions instead require `PlayerCharacter`; church offerings depend on the acting body's skills and acts, and the guild examination belongs to the commander's combat session. Dialogue owns per-character session/affinity and engage owns a combat session. Translating those services to the commander would change their semantics and is explicitly excluded.

### D2. Resolve the text purse through the same commander authority

In `CmdInventory`, read the party purse from the commander resolved by the existing party-scope boundary for a possessed actor; an ordinary player resolves to itself. Keep bag enumeration, repeated-item aggregation, ordering, item prose and the breakdown header on `self.caller`. No companion wallet is created or copied, and the inventory command cannot manufacture authority from a bare `possessed_by` flag. Use existing party error handling for a failed authority resolution. Do not fall back to a zero companion wallet or alter bag ownership.

### D3. Split combat suppression from guild omission

Keep combat as the first branch of `build_services_view`, preserving null host/guild/shop and four zero pagination totals. Outside combat, resolve the merchant normally. Under possession, set guild and guild reason to `None`, do not resolve/build guild staff or examination-counter services, and build host via `_build_host(None, merchant_host)`. Build shop through the same `_build_shop` invocation and member selection as ordinary exploration. Keep the existing owner-keyed player summary and surface-local shop error handling. Missing, ambiguous, closed, off-anchor and malformed merchants retain existing behavior.

At affordance assembly, omit the guild navigation entry while possessed. Remove the shared possession-disable branch from `_service_entry` so the merchant opener uses ordinary service gates. This avoids both a dead guild opener and a guild refusal falsely labeled `possessed_shop`. Preserve all talk affordance gates, including the panel's `explore.talk_open` projection, and the `possessed_engage` gate. No special-case UI balance or permission inference is added.

### D4. Replace active contradictory contracts together

| Existing contract | Amendment carried by this change |
|---|---|
| `openspec/specs/shop-economy/spec.md:231-236` | Remove `Possession keeps the shop refusal` and its refused-purchase scenario; add successful named-bag/party-purse trade requirements and text inventory parity |
| `openspec/specs/webclient-shop-window/spec.md:15-17` | Replace the currently unsatisfiable same-rows/refusal scenario with reachable normal shop presentation and successful trades |
| `openspec/specs/webclient-possession-presentation/spec.md:78-100` | Remove buy/sell from the dispatcher refusal set, replace the purchase-refusal scenario with talk/engage zero-write coverage, and replace guild-opener refusal with guild absence |
| `openspec/specs/exploration-affordances/spec.md:34-53,118-121` | Keep ordinary merchant entry gates and disabled engage; omit possessed guild navigation and qualify generic navigation scenarios accordingly |
| `openspec/specs/webclient-service-menus/spec.md` | Specify possessed guild omission and merchant-only host preference as exceptions to normal host/surface rules; retain combat nulling |
| `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md:42` (§3.2) | Remove the old shop-refusal clause; retain identical party/shop presentation and commander purse |
| Same document `:77` (§4.3) | Replace the shop-refusal bullet with normal possessed named-member shop transactions |
| Same document `:112` (§4.9) | Remove the statement that shop refusal is unchanged; keep possession follow and entry/exit boundaries |
| Same document `:325` (§13) | Remove shop refusal from non-goals and the follow-only claim; retain unchanged price formulas and possession entry/exit rules, and explicitly keep all other NPC services refused |
| `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py:172-178` | Remove the buy/sell possession prohibition in overview, contexts and descriptions; explain default acting bag and shared purse, and update the exact drift manifest together |

The planning commit contains only deltas and implementation tasks. The implementation changes the player/design documents in place. Main-spec synchronization uses the normal later OpenSpec lifecycle, outside this proposal assignment. Archived historical proposals remain historical records and are not rewritten.

The installed CLI rejects a MODIFIED requirement that retires an existing scenario name. To retire the misleading refusal scenarios, the deltas explicitly REMOVE and replace the three affected requirements, preserving every unrelated scenario. At synchronization, replace active traceability references to `the-canonical-affordance-vocabulary-is-shared-and-read-only`, `the-dispatcher-refuses-possession-incompatible-actions-with-fixed-zero-write-results`, and `the-shop-window-uses-the-frame-with-buy-and-sell-tabs-and-the-member-rail` with the corresponding new requirement IDs. The old `possession-keeps-the-shop-refusal` ID is also retired. This is a contract cutover, with no compatibility aliases or dropped unrelated coverage.

### D5. Convert refusal coverage without losing rejection coverage

| Existing seam | Required coverage |
|---|---|
| `world/rules/tests/test_shop_economy.py::test_text_trades_refuse_possession` | Convert to real possessed buy and sell using valid live session/account possession, assert acting bag and purse deltas, stock and commander affinity; cover an explicitly named different member |
| `commands/tests/test_inventory_breakdown.py`, existing shop command tests | Pin post-purchase/post-sale `inventory` purse parity with unchanged companion bag and breakdown rendering, plus ordinary-player parity |
| `web/webclient/presentation/tests/test_possession_presentation.py::test_dispatcher_refuses_possession_incompatible_actions` | Convert shop assertions into real successful trades with an eligible merchant; retain/add separate actual scripted/freeform talk and engage zero-write assertions, plus `talk_open` regression |
| `web/webclient/actions/tests/test_service_actions.py` | Extend named-member buy/sell tests to a genuinely possessed actor; pin explicit puppet and other member authorization, normal failure reasons and committed panel refresh |
| `world/rules/tests/test_service_view/`, `test_service_view_side_effects.py`, presenter/affordance tests | Assert owner summary, null guild with no guild reason, zero guild totals, normal merchant host and shop totals, both-host and guild-only rooms, ordinary merchant errors, unchanged combat suppression and read-only assembly |
| `web/webclient-app/tests/world/shop_window.test.js`, `app_client_shop_window.test.js` | Convert committed `possessed_shop` examples into possessed buy/sell success and identical-row coverage; retain a real ordinary domain refusal for request-correlated notice and row/member/tab clearing behavior |
| `use-shop-trade.js` and its AppClient callers, `ShopWindow.vue`, `stories/World/ShopWindow.stories.js`, current webclient guide and `test_node_suite_evidence.py` | Replace stale possession-refusal examples with ordinary domain refusal examples; keep generic failure notices and no-retry/epoch guards |
| `web/tests/browser/test_browser_services_shop.py` | Extend existing seeded companion-shop journey to enter real possession, keep the same viewed member, open via enabled merchant navigation, buy/sell, and assert exact dispatch/bag/purse updates and absent guild navigation; convert any possessed-refusal method found rather than deleting it |

Use existing deterministic synthetic catalogs and real authority bindings. A bare flag formerly sufficient for an early refusal is insufficient for successful trade authorization. Preserve ordinary insufficient-funds, equipped-item, stock-cap, host, stale/duplicate, and rollback tests. Add regression assertions that the possessed cmdset still excludes guild/church and that existing guild/church/quest-issuer entry points do not substitute the commander. Do not add production possession branches to achieve these tests.

Traceability must retire the removed requirement ID in active tests/evidence and cover the replacement requirements. The local gate resolves main specs only, so new requirement annotations become valid when the standard spec synchronization has occurred; do not leave a commit with unknown IDs. Preserve coverage itself throughout. Reuse existing test modules to avoid shard churn; any new module must be registered in its appropriate manifest.

## Risks / Trade-offs

- An enabled shop row could still hit a forgotten refusal. Mitigation: exercise real text and web transactions and refresh assertions, rather than mocking success or toggling only banner props.
- Omitting guild content could accidentally hide shop or remove owner state. Mitigation: cover mixed guild/merchant rooms, guild-only rooms, owner summary and exact pagination/reason values.
- Removing a combined guard could expose remote services during combat. Mitigation: preserve the combat-first branch and its existing regression, including a possession-marked actor.
- Converting old shop refusal examples could lose ordinary trade error notices or talk/engage protection. Mitigation: keep request-correlated ordinary refusals and test each still-protected action separately.
- The acceptance consumer depends on this runtime change. Mitigation: serialize landing before its task 3.1 resumes; do not edit the existing consumer branch or worktree here.

## Migration Plan

This is a pre-release clean cutover with no saved-data migration or compatibility API. Land adapters, presentation, tests and document amendments as one behavior change; use the normal project deployment. If reverted, revert the complete implementation and contracts together. After landing, resume `party-management-acceptance` on its existing branch so its remaining task can exercise the now-reachable possessed shop.
