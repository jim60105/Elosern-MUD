# Party combat and equipment growth batch contract

Planning source is the explicitly approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, commit `8c47578d`. Its written-status label predates the explicit approval. These proposals authorize planning only. The existing UI batch is coordination context and is unchanged.

## Implementation order and effort

Land `webclient-combat-panel-v6` first. Apply new changes 1 through 10 in the numbered order below. Then consume the remaining existing UI chain in its declared order: formation-engine, formation, figure-plates, defeated-foes, command-card-centred, stage-target-picking, cross-side-confirm. Apply new changes 11 through 18 afterward. This conservative default serializes overlapping integration seams. Independent slices may run together only if both the direct dependencies and the conflict matrix permit it; the numbered order remains the declared merge order. Planning commits stay on primary; later os-apply owns implementation branches. No apply/archive/merge is performed here.

| Order | Change | Total hours, including verification/docs/integration | Direct prerequisites |
|---:|---|---:|---|
| 1 | `combat-ratio-mitigation` | 5.5 | None |
| 2 | `equipment-weapon-damage-factor` | 6.5 | `combat-ratio-mitigation` |
| 3 | `party-combat-actor-commands` | 6.5 | None |
| 4 | `party-combat-persistent-drafts` | 6.5 | `party-combat-actor-commands` |
| 5 | `party-combat-atomic-rounds` | 7.5 | `party-combat-persistent-drafts` |
| 6 | `party-combat-opening-routing` | 4.5 | `party-combat-atomic-rounds` |
| 7 | `party-combat-defend-dodge` | 7 | `combat-ratio-mitigation`, `party-combat-atomic-rounds` |
| 8 | `party-combat-taunt-constraints` | 7 | `party-combat-defend-dodge`, `webclient-combat-panel-v6` |
| 9 | `party-combat-confirmed-surrender` | 6 | `party-combat-atomic-rounds` |
| 10 | `party-combat-retreat-resolution` | 7 | `party-combat-confirmed-surrender`, `party-combat-defend-dodge` |
| 11 | `party-combat-protocol-v7` | 7.5 | `equipment-weapon-damage-factor`, `party-combat-opening-routing`, `party-combat-taunt-constraints`, `party-combat-retreat-resolution`, `webclient-combat-panel-v6` |
| 12 | `party-combat-text-commands` | 7 | `party-combat-protocol-v7` |
| 13 | `webclient-party-command-selection` | 7 | `party-combat-protocol-v7`, `webclient-combat-command-card-centred`, `webclient-combat-stage-target-picking`, `webclient-combat-cross-side-confirm` |
| 14 | `webclient-party-items-tactics` | 7 | `webclient-party-command-selection` |
| 15 | `webclient-party-exit-confirmation` | 5.5 | `webclient-party-items-tactics` |
| 16 | `equipment-growth-runtime-calibration` | 6 | `equipment-weapon-damage-factor`, `party-combat-defend-dodge` |
| 17 | `party-combat-encounter-calibration` | 7 | `equipment-growth-runtime-calibration`, `party-combat-text-commands` |
| 18 | `party-combat-runtime-acceptance` | 6.5 | `webclient-party-exit-confirmation`, `party-combat-encounter-calibration` |

Total estimated implementation effort is 117.5 engineer-hours across 18 changes. Each change is strictly below 8 hours. Reusing the existing boundaries is part of the estimate; unknown broad redesign is excluded from these contracts, not approved functionality. No runtime verification has been performed by proposal authoring.

## Approved behavior ownership

| Approved section | Owning new change numbers | Complete acceptance boundary |
|---|---|---|
| §1 authority and §2 scope | 1, 2, 3, 6, 9, 10 | Explicit engine §6.3 amendment; literal traits and progression/affinity access remain; no new enemy basic tactics, shared bag, transfers, out-of-combat companion management or geometry redesign. |
| §3.1 actor authorization and capability | 3, 11, 12, 13, 14 | Independent commander/actor/target identities, full skill scales/costs/SELF and own-inventory item effects/targets, forged actor rejection; no possession. |
| §3.2 draft edit and final automatic submission | 4, 5, 6, 11, 12, 13 | One server draft; membership/preflight/reselection; initiating entry; no editing cost/AI/upkeep or separate whole-party confirmation; no interactive compression. |
| §3.3 ordinary round and execution invalidation | 5, 7, 8 | Initiative once, declarations before actions, selected ally requests once, deterministic enemies, final invalid target loses action with no retarget/cost, valid misses retain cost, one upkeep. |
| §3.4 durable retry/rollback | 4, 5, 9, 10, 18 | Restart/reconnect draft restoration, serialized current revision and durable receipts, whole round/settlement/cache rollback, no tactical leak. |
| §4.1 Defend and Dodge | 7, 11, 12, 14, 16, 17 | 0 MP/SP, no cooldown, declaration eligibility/expiry, final 35% floored reduction after scale, bypass/upkeep exceptions, threshold+25/margin/critical/check-only/AREA, estimator parity. |
| §4.2 Taunt | 8, 11, 12, 14, 17 | Typed hostile candidates before utility/final validation, ordinary range/seal restrictions, initiative winner/no promotion, winner removal, area/support/flee freedom. |
| §5.1 ratio mitigation | 1, 7, 16, 17 | Finite positive K40 baseline; negative clamp, both schools/sides, attack rounding, post-defense rider, half-up scale/floors, bypass/Defend order, independent 60/20 examples. |
| §5.2 weapon factor and actual authoring | 2, 16, 17 | Closed schema/rarity ceilings, nonadditive main/off-hand and nonweapon exception, physical elemental/multi-strike, neutral controls, actual registry values and reload evidence. |
| §5.3 armor and combined calibration | 16, 17 | Real construction/grant/equip/commit/reload; armor monotonic defense/gauge/tradeoffs; coefficient×critical×factor×strikes, riders/scales/magic/bypass and both sides; observed-only tuning, historical qualification. |
| §6 confirmation/surrender | 9, 11, 12, 15, 18 | Session/round/commander/operation-bound token, cancel keeps draft, no allied personal-flee bypass, zero-extra-round ordinary defeat/exam FAIL, no restoration privilege. |
| §6.1 retreat | 10, 11, 12, 15, 18 | Slowest acting ally/fastest living present pursuer d100 contest with existing constant; no accuracy/Dodge; no pursuer roll; no actor defeat; carried downed companions; all-party success/failure; one time settlement. |
| §7 client/text and coordination | 11, 12, 13, 14, 15, 18 | Exact v7 single-actor choices, all-actor progress, same card/targets/scale/items, warnings/focus/accessibility, actor vs target; full text parity and confirmation. |
| §8 integration and §9 evidence/docs | All; 18 owns assembled gate | Focused independent tests, failure injection, actual multi-actor skill/item/edit/reconnect and exits on browser/text; command docs, validators/fixtures, canonical IDs and shards; contract gate and observability when changed; full managed browser/trace evidence CI-only. |

## Shared admission and lifecycle contract

`commander` is the authenticated session owner and stays the puppet. `actor_id` selects only a currently authorized allied session participant. Targets are a separate identity set. Per-actor closed commands are skill (existing TargetSpec/scale), item (existing item key/optional single recipient), or tactic (Defend/Dodge, or Taunt with one enemy). No unsupported personal action, scale or item effect is dropped for companions.

`round_revision` is a durable per-round admission identity, independent of `draft_version` for free editing. Every session mutation enters the existing single deterministic server writer; competing request callbacks are queued, then re-read uncached durable session/revision inside the transaction. This server currently uses one Evennia deterministic writer, not multiple web workers writing combat. No process-local used flag or SQLite SELECT FOR UPDATE assumption is accepted as the durable guard. A bounded commander-owned completion receipt survives clearing active_combat, covering the last completed session/round operation; older or different session/revision requests reject stale, never execute. The final confirmed complete draft is persisted before the round transaction so technical rollback preserves accepted choices. A crash leaves all round/receipt/settlement state durable together or none. Every new attribute/cache surface is in the existing snapshot/journal restoration boundary. Prompt/round/exit admission uses the same writer and revision guard.

No extra whole-party confirmation is added. The last valid member confirmation starts exactly one ordinary round. Membership changes require explicit fresh confirmation rather than causing an incomplete old draft to execute. Ordinary final target invalidation is a spent action with no retarget/cost; technical failure rolls the complete round back. Opening order metadata preserves the existing explicit encounter first-actor exception only for its opening round. Interactive overwhelm compression and allied policy fallback are removed; independent noninteractive overwhelm and enemy policy remain.

## Version and UI contract

Version 7 is a breaking exact-field cutover on top of active v6. It publishes all allied actor summaries and durable progress but only one actor full choices at a time, preserving the 65,536-byte OOB limit. Read-only combat.actor_choices requests update transport selection, never drafts. See change 11 design for every exact object/payload bound. Skills retain v6 conditions/polarity semantics, item polarity follows the same authoritative typed effect classification, and no v6/v7 compatibility layer is added.

Changes 11 through 15 are the coordinated transport/client cutover: old adapters and producers are removed end to end, with no assembled release until change 15 and the final acceptance gate pass. Intermediate source commits are integration dependencies, never a claim of the complete user feature. Existing centered-card width/anchor, formation, plates, fallen state, target navigation and warning checks are consumed unchanged. Actor/progress controls use existing card rows/detail slots; this planning batch does not redesign stage geometry. The drawer supports actor-scoped in-combat item use and free commander equipment operations, never companion equipment/transfer management.

## New-to-new conflict matrix

Rows and columns use the numbered changes above. `F` means known shared implementation/test/doc files (and possibly shared specs); `S` means shared capability but distinct named requirements and no exact code-file overlap; `D` means direct dependency without identified file/spec overlap; `.` means no direct dependency or observed shared surface. Every `F` or `S` requires ordered integration; `S` does not imply requirements overwrite each other. Full MODIFIED blocks in changes 13, 14 and 15 are explicitly chained on the incoming UI and preceding party keyboard contracts. Main-spec synchronization must preserve all earlier additions.

| # | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | = | F | . | . | . | . | F | F | . | . | . | . | . | . | . | . | F | . |
| 2 | F | = | . | . | . | . | F | F | . | . | D | . | . | . | . | F | F | . |
| 3 | . | . | = | F | F | F | . | S | F | F | F | S | . | . | . | . | . | . |
| 4 | . | . | F | = | F | F | . | S | F | F | . | S | . | . | . | . | . | . |
| 5 | . | . | F | F | = | F | F | F | F | F | . | S | . | . | . | . | . | . |
| 6 | . | . | F | F | F | = | . | F | F | F | D | F | . | . | . | . | . | . |
| 7 | F | F | . | . | F | . | = | F | . | F | . | . | . | . | . | D | F | . |
| 8 | F | F | S | S | F | F | F | = | S | F | D | S | . | . | . | . | . | . |
| 9 | . | . | F | F | F | F | . | S | = | F | . | F | . | . | . | . | . | . |
| 10 | . | . | F | F | F | F | F | F | F | = | D | S | . | . | . | . | . | . |
| 11 | . | D | F | . | . | D | . | D | . | D | = | S | S | S | S | . | . | . |
| 12 | . | . | S | S | S | F | . | S | F | S | S | = | . | S | . | . | D | F |
| 13 | . | . | . | . | . | . | . | . | . | . | S | . | = | F | F | . | . | . |
| 14 | . | . | . | . | . | . | . | . | . | . | S | S | F | = | F | . | . | . |
| 15 | . | . | . | . | . | . | . | . | . | . | S | . | F | F | = | . | . | D |
| 16 | . | F | . | . | . | . | D | . | . | . | . | . | . | . | . | = | F | F |
| 17 | F | F | . | . | . | . | F | . | . | . | . | D | . | . | . | F | = | F |
| 18 | . | . | . | . | . | . | . | . | . | . | . | F | . | . | D | F | F | = |

### Shared implementation seams and integration owner

- Shared scalar and damage ordering: 1, 2, 7, 16, 17. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Session record/draft/provider/atomic admission: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Canonical combat view and actor preview: 3, 11, 12. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Enemy candidate legality and estimation: 1, 2, 7, 8, 17. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Exact schemas/adapters/fixtures/version constants: 11, 12, 13, 14, 15. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Client resolver/menu/frames/view/stage warning: 13, 14, 15, 18. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Both player command docs and command manifest: 6, 9, 12. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.
- Real calibration data and evidence: 16, 17, 18. The later numbered owner integrates against the earlier landed contract; final assembly owner is change 18.

Conditional cross-cutting conflicts apply to every slice adding tests: `.github/evennia-shards.json`, `.github/browser-shards.json`, canonical traceability annotations and shared synthetic fixture builders. Integration must retain exact single-shard ownership and earlier requirements. Docs shared by numbered changes are serialized in declared order. No new test-data freeze exception is used for behavioral tests; real shipped-data evidence uses existing calibration/data-contract discipline.

## Existing-active-UI conflict matrix

| Active proposal | New changes with direct shared/coordination surfaces | Shared code/spec surface | Required disposition |
|---|---|---|---|
| `webclient-combat-panel-v6` | 3, 8, 11 | world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; webclient-combat-menu | Land v6 before 8/11; 3 integrates the read model additively. |
| `webclient-combat-formation-engine` | None | No shared geometry implementation; existing formation engine is consumed unchanged; webclient-contextual-hud | Consume landed contract; no geometry rewrite. |
| `webclient-combat-formation` | 13, 14, 15, 18 | AppClient.vue; stories; browser methods; no formation geometry ownership transfer; webclient-combat-menu; webclient-contextual-hud | Land active chain before 13; preserve its behavior and integrate later. |
| `webclient-combat-figure-plates` | 13, 15, 18 | AppClient.vue; stories/focus integration; glyph/plate contract unchanged; webclient-contextual-hud | Land active chain before 13; preserve its behavior and integrate later. |
| `webclient-combat-defeated-foes` | 13, 18 | AppClient.vue; stories; fallen/beat target state preserved; webclient-contextual-hud | Land active chain before 13; preserve its behavior and integrate later. |
| `webclient-combat-command-card-centred` | 13, 14, 15, 18 | ActionDock.vue; AppClient.vue; stories; fixed card geometry unchanged; webclient-contextual-hud | Land active chain before 13; preserve its behavior and integrate later. |
| `webclient-combat-stage-target-picking` | 13, 14, 15, 18 | stage_targets.js; interaction/combat/view stores; ActionDock.vue; AppClient.vue; stories and browser tests; webclient-combat-menu; webclient-contextual-hud | Land active chain before 13; preserve its behavior and integrate later. |
| `webclient-combat-cross-side-confirm` | 13, 14, 15, 18 | cross_side.js; frames/view/interaction/combat stores; QuestionCard.vue; AppClient.vue; stories; webclient-combat-menu | Land active chain before 13; preserve its behavior and integrate later. |

All unlisted active/new pairings have no identified direct code or requirement rewrite. Changes 11/13 consume transitive prerequisites through the explicit active UI chain; new client changes never remove warning checks or restore the retired participant roster. Existing active proposals are read-only coordination input and are neither edited nor merged by this batch.

## Planning and implementation gates

Every change includes proposal, design, capability deltas and unchecked implementation tasks. Per-change strict OpenSpec validation and root os-phase output are recorded at handoff. The whole artifact set receives one blocking independent review after initial proposal commits; blocking findings are corrected in directory-scoped follow-up commits with dispositions recorded here. That review is planning evidence only.

Implementation must run the focused tests named in tasks, canonical contract gate and observability lint with focused event tests when logging changes. Added/moved tests update shard manifests in the same implementation change. Change 18 exercises real browser and text paths and records evidence; full managed browser suite and full traceability evidence remain CI-owned. No build, test or formatter is run while drafting proposals.
