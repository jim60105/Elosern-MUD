# Party combat and equipment growth batch contract

Planning source is the explicitly approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, commit `8c47578d`. Its written-status label predates explicit approval. These artifacts authorize planning only. Existing active UI proposals are unchanged coordination input.

## Mandatory implementation order and effort

Land `webclient-combat-panel-v6` before change3. Apply new changes1-10 in numbered order, consuming that v6 prerequisite. Land the remaining existing UI chain in its own declared order, formation-engine, formation, figure-plates, defeated-foes, command-card-centred, stage-target-picking, cross-side-confirm. Then apply new changes11-20. This order is a mandatory admission/integration prerequisite, not a suggestion to bypass explicit incoming spec blocks. A supervisor may schedule nonconflicting preparatory work together, but only the declared order admits their integrated cutover. Planning commits stay on primary; later apply owns implementation branches.

| Order | Change | Total hours including implementation, focused verification, docs and integration | Direct prerequisites |
|---:|---|---:|---|
| 1 | `combat-ratio-mitigation` | 5.5 | None |
| 2 | `equipment-weapon-damage-factor` | 6.5 | `combat-ratio-mitigation` |
| 3 | `party-combat-actor-commands` | 6.5 | `webclient-combat-panel-v6` |
| 4 | `party-combat-persistent-drafts` | 6.5 | `party-combat-actor-commands` |
| 5 | `party-combat-atomic-rounds` | 7.5 | `party-combat-persistent-drafts` |
| 6 | `party-combat-opening-routing` | 4.5 | `party-combat-atomic-rounds` |
| 7 | `party-combat-defend-dodge` | 7 | `combat-ratio-mitigation`, `party-combat-atomic-rounds` |
| 8 | `party-combat-taunt-constraints` | 7 | `party-combat-defend-dodge`, `webclient-combat-panel-v6` |
| 9 | `party-combat-confirmed-surrender` | 6 | `party-combat-atomic-rounds` |
| 10 | `party-combat-retreat-resolution` | 7 | `party-combat-confirmed-surrender`, `party-combat-defend-dodge` |
| 11 | `party-combat-protocol-v7` | 6.5 | `equipment-weapon-damage-factor`, `party-combat-opening-routing`, `party-combat-taunt-constraints`, `party-combat-retreat-resolution`, `webclient-combat-panel-v6`, `webclient-combat-cross-side-confirm` |
| 12 | `party-combat-command-transport` | 6.5 | `party-combat-protocol-v7` |
| 13 | `party-combat-text-commands` | 7 | `party-combat-command-transport` |
| 14 | `webclient-party-command-selection` | 7 | `party-combat-command-transport`, `webclient-combat-command-card-centred`, `webclient-combat-stage-target-picking`, `webclient-combat-cross-side-confirm` |
| 15 | `webclient-party-items-tactics` | 7 | `webclient-party-command-selection` |
| 16 | `webclient-party-exit-confirmation` | 5.5 | `webclient-party-items-tactics` |
| 17 | `equipment-growth-runtime-calibration` | 6 | `equipment-weapon-damage-factor`, `party-combat-defend-dodge` |
| 18 | `party-combat-factor-budget-calibration` | 5.5 | `equipment-growth-runtime-calibration` |
| 19 | `party-combat-encounter-calibration` | 6.5 | `party-combat-factor-budget-calibration`, `party-combat-text-commands` |
| 20 | `party-combat-runtime-acceptance` | 6.5 | `webclient-party-exit-confirmation`, `party-combat-encounter-calibration` |

Total estimate is 128 engineer-hours across20 changes. Every change is strictly below8 hours. The final review split protocol/schema from transport integration and combined-factor evidence from finite encounter tuning. No approved behavior was removed.

## Approved behavior ownership

| Approved section | Owner numbers | Acceptance boundary |
|---|---|---|
| §1 authority and §2 scope | 1, 2, 3, 6, 9, 10 | Explicit engine §6.3 amendment; literal traits and progression/affinity access remain; no new enemy basic tactics, shared bag, transfers, out-of-combat companion management or geometry redesign. |
| §3.1 actor authorization and capability | 3, 11, 13, 14, 15 | Independent commander/actor/target identities, full skill scales/costs/SELF and own-inventory item effects/targets, forged actor rejection; no possession. |
| §3.2 draft edit and final automatic submission | 4, 5, 6, 11, 13, 14 | One server draft; membership/preflight/reselection; initiating entry; no editing cost/AI/upkeep or separate whole-party confirmation; no interactive compression. |
| §3.3 ordinary round and execution invalidation | 5, 7, 8 | Initiative once, declarations before actions, selected ally requests once, deterministic enemies, final invalid target loses action with no retarget/cost, valid misses retain cost, one upkeep. |
| §3.4 durable retry/rollback | 4, 5, 9, 10, 20 | Restart/reconnect draft restoration, serialized current revision and durable receipts, whole round/settlement/cache rollback, no tactical leak. |
| §4.1 Defend and Dodge | 7, 11, 13, 15, 17, 19 | 0 MP/SP, no cooldown, declaration eligibility/expiry, final 35% floored reduction after scale, bypass/upkeep exceptions, threshold+25/margin/critical/check-only/AREA, estimator parity. |
| §4.2 Taunt | 8, 11, 13, 15, 19 | Typed hostile candidates before utility/final validation, ordinary range/seal restrictions, initiative winner/no promotion, winner removal, area/support/flee freedom. |
| §5.1 ratio mitigation | 1, 7, 17, 19 | Finite positive K40 baseline; negative clamp, both schools/sides, attack rounding, post-defense rider, half-up scale/floors, bypass/Defend order, independent 60/20 examples. |
| §5.2 weapon factor and actual authoring | 2, 17, 19 | Closed schema/rarity ceilings, nonadditive main/off-hand and nonweapon exception, physical elemental/multi-strike, neutral controls, actual registry values and reload evidence. |
| §5.3 armor and combined calibration | 17, 19, 18 | Real construction/grant/equip/commit/reload; armor monotonic defense/gauge/tradeoffs; coefficient×critical×factor×strikes, riders/scales/magic/bypass and both sides; observed-only tuning, historical qualification. |
| §6 confirmation/surrender | 9, 11, 13, 16, 20 | Session/round/commander/operation-bound token, cancel keeps draft, no allied personal-flee bypass, zero-extra-round ordinary defeat/exam FAIL, no restoration privilege. |
| §6.1 retreat | 10, 11, 13, 16, 20 | Slowest acting ally/fastest living present pursuer d100 contest with existing constant; no accuracy/Dodge; no pursuer roll; no actor defeat; carried downed companions; all-party success/failure; one time settlement. |
| §7 client/text and coordination | 11, 13, 14, 15, 16, 20, 12 | Exact v7 single-actor choices, all-actor progress, same card/targets/scale/items, warnings/focus/accessibility, actor vs target; full text parity and confirmation. |
| §8 integration and §9 evidence/docs | All;20 owns assembled acceptance | Focused independent tests, failure injection, actual multi-actor skill/item/edit/reconnect and exits on browser/text; command docs, validators/fixtures, canonical IDs and shards; contract gate and observability when changed; full managed browser/trace evidence CI-only. |

## Shared admission and lifecycle contract

Commander is the authenticated puppet and never changes during companion commands. Actor identity is an authorized subordinate allied-session reference; targets are a separate identity set. Per-actor commands preserve complete skill/scale/TargetSpec behavior, own-inventory item effects/targets and basic tactics.

Round_revision is durable round/operation admission identity; draft_version handles free edit CAS. Every session mutation enters the existing single Evennia deterministic writer; competing callbacks queue and reread uncached durable session/revision inside the transaction. The deployment has one deterministic combat writer, not multiple web-worker writers. No process-local used flag or SQLite SELECT FOR UPDATE assumption is the durable guard. A bounded commander-owned completion receipt survives clearing active_combat and records the last completed session/revision; older/different requests reject stale without executing. Final confirmed draft entries persist before round resolution so technical rollback retains accepted selections. Round effects/metadata/receipt/settlement are durable together or absent together, and new attribute/cache surfaces join existing restoration journals.

Last valid required member confirmation auto-submits one ordinary round with no whole-party confirm. Changed membership requires fresh explicit confirmation. Empty required sets stay paused with no-eligible-actors and party-operation paths, never editing-triggered enemy/upkeep/time; confirmed retreat then takes its approved no-acting-ally defeat branch. Normal target invalidation consumes one action without retarget/cost, while technical failure rolls the entire round back. Interactive allies have one selected-command slot even if positive actions_per_turn is greater; enemies/noninteractive slots and zero-action gates keep existing behavior. Opening first-actor metadata applies once; interactive compression and allied policy fallback are removed.

## Exact protocol and UI cutover

Change11 owns exact v7 actor/read-model and mirrored panel schemas. Change12 owns dispatcher/schema admission, guarded adapters, exact result variants and canonical publication. See their designs for complete bounds and field sets. All allied summaries/progress are published but only one actor full catalog, keeping65,536-byte OOB bounds. Actor queries update only transport presentation selection. Existing v6 condition/polarity facts remain; no compatibility parser or account/puppet identity override is accepted.

Changes11-16 are one unreleased transport/client cutover; existing active combat adapters/producers are retired end to end. No assembled release is accepted until change20. Existing centered card geometry, formation, plates, fallen treatment, target navigation and warning checks remain. Actor/progress controls use existing card rows/detail slots, and the in-combat drawer routes own-inventory use through actor commands while keeping commander equipment toggles free. No companion equipment/transfer management surface is added.

## New-to-new conflict matrix

Numbers refer to the table above. F means shared implementation/test/doc files, possibly shared specs. S means shared capability with distinct named requirements and no exact code-file overlap. D means direct dependency without shared files/specs; . means no identified direct dependency or overlap. Every F or S requires ordered integration preserving earlier additions; full keyboard MODIFIED blocks in14/15/16 chain on incoming active UI plus the preceding party block. Conditional shard/fixture conflicts are listed separately.

| # | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | = | F | . | . | S | . | F | F | . | . | . | . | . | . | . | . | . | . | F | . |
| 2 | F | = | . | . | S | . | F | F | . | . | D | . | . | . | . | . | F | . | F | . |
| 3 | . | . | = | F | F | F | . | S | F | F | F | . | S | . | . | . | . | . | . | . |
| 4 | . | . | F | = | F | F | . | S | F | F | . | . | S | . | . | . | . | . | . | . |
| 5 | S | S | F | F | = | F | F | F | F | F | . | . | S | . | . | . | . | . | . | . |
| 6 | . | . | F | F | F | = | . | F | F | F | D | . | F | . | . | . | . | . | . | . |
| 7 | F | F | . | . | F | . | = | F | . | F | . | . | . | . | . | . | D | . | F | . |
| 8 | F | F | S | S | F | F | F | = | S | F | D | . | S | . | . | . | . | . | . | . |
| 9 | . | . | F | F | F | F | . | S | = | F | . | . | F | . | . | . | . | . | . | . |
| 10 | . | . | F | F | F | F | F | F | F | = | D | . | S | . | . | . | . | . | . | . |
| 11 | . | D | F | . | . | D | . | D | . | D | = | S | . | S | S | S | . | . | . | . |
| 12 | . | . | . | . | . | . | . | . | . | . | S | = | S | S | S | S | . | . | . | . |
| 13 | . | . | S | S | S | F | . | S | F | S | . | S | = | . | S | . | . | . | D | F |
| 14 | . | . | . | . | . | . | . | . | . | . | S | S | . | = | F | F | . | . | . | . |
| 15 | . | . | . | . | . | . | . | . | . | . | S | S | S | F | = | F | . | . | . | . |
| 16 | . | . | . | . | . | . | . | . | . | . | S | S | . | F | F | = | . | . | . | D |
| 17 | . | F | . | . | . | . | D | . | . | . | . | . | . | . | . | . | = | F | F | F |
| 18 | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | F | = | F | F |
| 19 | F | F | . | . | . | . | F | . | . | . | . | . | D | . | . | . | F | F | = | F |
| 20 | . | . | . | . | . | . | . | . | . | . | . | . | F | . | . | D | F | F | F | = |

### Integration ownership

Change5 owns the outer round/provider/receipt unit and explicit allied action-count amendment. Change10 integrates retreat against it. Change12 owns transport/dispatcher integration on the panel contract from11. Client changes14/15/16 integrate in that order without stage redesign. Change17 owns initial/selected actual gear authoring and committed reload; change18 owns the finite30-case factor matrix; change19 owns exactly eight encounter cells × seeds0-3 and finite tuning. Change20 owns assembled runtime evidence and blocks acceptance of any missing approved behavior.

Conditional cross-cutting conflicts apply to every slice adding/moving tests, `.github/evennia-shards.json`, `.github/browser-shards.json`, canonical requirement annotations and shared synthetic fixture builders. Preserve exactly-one-shard ownership and independent behavior expectations. Shared developer evidence/command docs integrate in declared order. The real shipped-data calibration uses existing data-contract discipline, never arbitrary new freeze exceptions.

## Existing-active-UI conflict matrix

| Active proposal | Direct new owners | Shared code/spec surfaces | Disposition |
|---|---|---|---|
| `webclient-combat-panel-v6` | 3, 8, 11, 12 | world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; webclient-combat-menu | Direct prerequisite of3/8/11; transport12 preserves the landed classifier/panel facts. |
| `webclient-combat-formation-engine` | None | No shared geometry implementation; existing formation engine is consumed unchanged; webclient-contextual-hud | Consume unchanged geometry contract. |
| `webclient-combat-formation` | 14, 15, 16, 20 | AppClient.vue; stories; browser methods; no formation geometry ownership transfer; webclient-combat-menu; webclient-contextual-hud | Land existing chain before11; preserve geometry/behavior and integrate later. |
| `webclient-combat-figure-plates` | 14, 16, 20 | AppClient.vue; stories/focus integration; glyph/plate contract unchanged; webclient-contextual-hud | Land existing chain before11; preserve geometry/behavior and integrate later. |
| `webclient-combat-defeated-foes` | 14, 20 | AppClient.vue; stories; fallen/beat target state preserved; webclient-contextual-hud | Land existing chain before11; preserve geometry/behavior and integrate later. |
| `webclient-combat-command-card-centred` | 14, 15, 16, 20 | ActionDock.vue; AppClient.vue; stories; fixed card geometry unchanged; webclient-contextual-hud | Land existing chain before11; preserve geometry/behavior and integrate later. |
| `webclient-combat-stage-target-picking` | 14, 15, 16, 20, 12 | stage_targets.js; interaction/combat/view stores; ActionDock.vue; AppClient.vue; stories and browser tests; webclient-combat-menu; webclient-contextual-hud | Land existing chain before11; preserve geometry/behavior and integrate later. |
| `webclient-combat-cross-side-confirm` | 14, 15, 16, 20, 12 | cross_side.js; frames/view/interaction/combat stores; QuestionCard.vue; AppClient.vue; stories; webclient-combat-menu | Land existing chain before11; preserve geometry/behavior and integrate later. |

All unlisted active/new pairs have no identified direct code or requirement rewrite. The mandatory incoming chain and explicit dependencies cover transitive prerequisites. Existing active proposal files are read-only and never edited, merged or archived by this planning assignment.

## Final review dispositions

One blocking independent whole-set review inspected the approved document, all original18 artifact sets and relevant canonical/incoming UI requirements. Its initial verdict required corrections. Every finding was adopted in this20-change revision; no finding was rejected or deferred.

| Finding | Adopted remedy and owner |
|---|---|
| B1 incompatible dispatcher authority/registry/scale contracts | New transport12 supplies complete webclient-action-dispatch deltas; commander authentication remains unchanged while only exact guarded subordinate references are permitted. |
| B2 missing exact v7 data | Schema11 pins item summaries/count, reason rows, roots/recovery and all bounds; transport12 pins success-only prompt data and every result variant without weakening the global result envelope. |
| B3 retained contradictory scenarios | v7 unavailable is7; inventory.use is exploration-only; text combat use saves a nonfinal entry and parity is against combat.command; final-entry round is separate. |
| B4 missing initial weapon budget cells | Loader change2 authors valid1.0 initial ceilings for every shipped rarity. Calibration17 may select revised ceilings and actual nonneutral weapon values. |
| B5 multiple action-slot ambiguity | Round change5 amends combat-resolution, caps interactive allied selected commands at one and retains enemy/noninteractive slots, fuse/liveness and zero gates. |
| B6 oversized/unbounded estimates | Split11 into schema11 at6.5h and transport12 at6.5h. Split combined-factor evidence18 at5.5h from encounter tuning19 at6.5h, with30 explicit factor cases and eight fixed encounter cells × four seeds, finite tuning and repeated selected-value pass. |
| N1 incomplete machine prerequisites | Actor3 now explicitly depends on panel-v6; schema11 explicitly depends on cross-side-confirm, carrying the whole incoming UI chain; mandatory batch admission order is explicit. |
| N2 empty actor set | Draft4 explicitly reports no-eligible-actors and stays paused with confirmed party exits; no all-empty automatic round or invented missing command. |

The reviewer did not independently re-review the revisions. The handoff reports this initial verdict and adopted dispositions separately from final strict planning validation; neither is runtime verification.

## Planning and implementation gates

Final planning validation passes for all20 changes with `openspec validate <change> --strict`. The CLI reports informational dependency-preview notices for the incoming v6-to-v7 requirement renames and the stage-target requirement that is not yet in main specs. These are supplied by explicit active-proposal prerequisites, not missing artifacts; no archive was attempted. Stable existing scenario titles are retained because strict delta validation preserves scenario identities; their updated WHEN/THEN clauses define the amended behavior. The root repository contract gate passed, including2222/2222 requirement coverage, zero traceability/observability/test-data violations, manifest checks and18 gate contract tests. No gameplay build/test or runtime smoke was performed during planning.

Every change contains proposal, design, capability deltas and unchecked implementation tasks. Final per-change strict validation/status and os-phase run from root are reported at handoff. Initial changes and review fixes are signed commits scoped individually to their change directories on master. No implementation, build, test or formatter runs during drafting.

Implementation tasks require focused independent tests, exact schemas/fixtures, both command docs where affected, canonical IDs and shard ownership, plus contract gate and observability lint/focused event tests when logging changes. Change20 exercises the real browser/text paths and final assembled evidence. Full managed browser execution and complete traceability evidence remain CI-owned.
