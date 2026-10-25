# Proposal

## Why

Component presence currently produces coarse room-wide shop/guild navigation, while other supported services are hidden in commands or dialogue. A derived target-bound descriptor makes availability discoverable without duplicating authority.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Project contextual services from capabilities and explicit dialogue associations, with text-client discovery and exact target routes.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

- `npc-contextual-services`: Project contextual services from capabilities and explicit dialogue associations, with text-client discovery and exact target routes.

### Modified Capabilities

- `webclient-exploration-menu`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `scripted-dialogue`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `authored-dialogue-sources`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `game-command-docs`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

The existing service model handles shop, guild registration/board/report and independent examination requests. Church enrollment is a real text command, not an existing web drawer. Guild 回報 has deterministic reportable_quest_summary behavior; other prose such as drill-yard 考核 does not provide an examination service. Authored scene reading already distinguishes formal/refusal/opening/service deliveries; generated-packages will provide current source-aware topic identities.

This is a one-engineer-day runnable slice with 5 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-title-authoring-removal
depends-on: npc-direct-capability-declarations
depends-on: npc-targeted-service-flows
depends-on: authored-dialogue-generated-packages
depends-on: authored-dialogue-content-guild

code-conflicts: P follows D/T plus authored-dialogue-generated-packages and content-guild because it adds source services against their final codecs/topic IDs. All other nine content slices remain independent of P but share authoring docs/codecs test inventory; their prose cannot imply a service. Serialize constants/presenters/frame-resolvers with active publication and immutable-adoption work. U follows P.

The complete new-new and relevant active-change matrix and amendment ownership are in `../npc-examination-reception/batch.md`. The approved source remains unchanged.
