# Design: Dedicated party-management acceptance seed

## Context

Handoff issue 2 establishes that the existing modes compose 蒼雀, 燼雀 and 艾拉, omit 卡恩, and grant the heal to the first companion. The closed console registry has no create/rename/bind/grant verbs. The original acceptance design requires 艾拉 and 卡恩 and limits setup to console verbs. Synthetic pre-session initialization already exists in the harness; the repo's console-only rule applies to manual runtime patching of game state.

## Goals / Non-Goals

Supply the exact acceptance prerequisites without adding production GM operations or silently substituting journey identities. Existing `store_open_companion`, companion-lineup, field-cast and party-combat acceptance flags keep their current behavior. No raw console batch, shell ORM patch, console allowlist expansion or pretend success evidence is authorized.

## Decisions

Choose the dedicated deterministic seed option explicitly. Add an opt-in `ELOSERN_BROWSER_PARTY_MANAGEMENT_ACCEPTANCE=1` mode accepted only in the isolated synthetic managed runtime. It is a pre-session fixture initialization exception, not permission for post-start mutation outside the protected console. Reject incompatible overlapping party/service composition flags with a diagnostic before seeding instead of relying on order-dependent overwrites; documented compatible base synthetic settings remain accepted.

Coordinate with the original acceptance apply owner before changing its `design.md`. Replace its journey setup clause with: the managed runtime initializes the dedicated deterministic party-management acceptance seed before login; after login every manual state intervention uses existing protected GM domain verbs with automatic snapshots; raw repair and shell patches are prohibited. Preserve the named journey, screenshots policy and all remaining acceptance criteria. Do not copy the stale master acceptance artifacts over the owner's branch or reset its evidence.

Implement a focused fixture module composed through existing validated character/companion construction, party membership, lineage grants, inventory/equipment, map/exit and encounter seams. Persistent game mutations route through their deterministic package owners. Exact authored synthetic display identities are 艾拉 and 卡恩 with stable distinct fixture tags/IDs; bind both as effective members, not positional `party_ids()[:1]` selection and not renaming arbitrary companions. Keep all effective members and the owner's body co-located at the open merchant with capacity for the named pair. The base preset companion may remain only if capacity permits and it remains co-located; tests explicitly identify the required pair and never treat the base companion as a substitute.

艾拉 owns `t_hush_mend` and the synthetic hostile opener `t_ember_burst`, with all prerequisites, identity restrictions and resources satisfied through the lineage grant seam. Independently verify their field and opening previews are legal for 艾拉. Use an initial commander wound large enough to remain healable after earlier free shopping/equipment steps, plus a companion wound and owned real consumable for successful item-use parity. Provide transfer quantity/headroom, initially held wearable equipment and a spare alternative for a visible equipment change; the shop stocks at least three purchasable potions and the purse covers them. Leave room for a sale. The fixture documents exact starting quantities and resources rather than assuming a refusal can stand in for a successful action.

Provide a nearby living hostile monster that the pair can defeat deterministically, and a real usable exit to a connected safe room. Pin only fixture parameters required for legal actions and a finishable encounter; let real combat/possession/movement logic execute. Fixture tests prove navigation and previews without completing the original acceptance checklist. The later acceptance worker still cancels then confirms the opening, finishes the fight, possesses 艾拉, traverses with the owner's body and 卡恩, compares surfaces while possessed, and observes combat equipment/transfer rules through the actual UI.

## Risks / Trade-offs

A dedicated mode adds maintenance but avoids unrelated security-sensitive console verbs. Repeated initialization must not duplicate the tagged pair or grants; if reseeding is unsupported by the harness, reject it before mutation and document the fresh-runtime requirement. Existing flag combinations are unchanged when the new flag is absent. Snapshot availability and valid synthetic lineage are hard prerequisites for the fixture consumer tests and later permitted runtime intervention.

## Verification and documentation

Test exact pair identity, membership/capacity, co-location, actor ownership/prerequisites, real inventory/equipment and a usable exit. Use real item/skill/opening preview consumers; include an ordinary read of both members' lineage. Add one managed fixture smoke exercising authenticated panel and text consumers, with no external services. Register methods/modules in the exact manifest owners and document launch flags, incompatibilities, state table and runtime-only GM policy in the existing fixture guide. The original acceptance owner performs the evidence journey after all six fixes land; fixture smoke is never substituted for UI evidence.
