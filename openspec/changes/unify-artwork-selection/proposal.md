# Proposal

## Why

Registry-only startup subjects cannot currently resolve the official reference used by the automatic-generation guard. They therefore generate default cards that obscure available official artwork, while scene and portrait presenters maintain separate selection policies.

## What Changes

- Use one capability-driven subject selection chain for characters, monsters, scenes and future gallery-bearing kinds.
- Resolve registered monster and scene official references from typed subjects without requiring a spawned entity. Keep character preset/NPC references provenance-only.
- Suppress automatic generation when a valid operator official default resolves. Preserve deliberate deletion suppression, age gates, transaction isolation and on-demand generation.
- Keep matching equipment bindings first, explicit official selection before the gallery default, generated gallery default before unselected official default, then declared built-in terminal sources.
- Keep scene and monster replacement at one generated card. Generation never clears an explicit official selection.
- **BREAKING**: unify scene subject preferences with the common chain; room-specific authored overrides remain an outer, higher-priority source. Scene personal state belongs to the shared archetype, not a room.
- Extend official-reference membership to scene archetypes; preserve existing loader support for scene and room directories.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-gallery-autogen`: shared official-satisfied guard and manual bypass.
- `art-gallery-resolution`: common deterministic priority and scene participation.
- `art-gallery-kind-capabilities`: declare reference and preference policies.
- `official-art-resolution`: entity-less registry references and common priority.
- `official-art-personalization`: scene preference ownership and generation preservation.
- `official-artwork-catalog`: scene registry membership and vocabulary alignment.
- `art-gallery-generation`: explicit requests remain available under official coverage.
- `art-gallery-model`: single-card replacement and preference ownership.
- `art-gallery-fallback`: capability-selected terminals without changing demographic rules.
- `art-subject-model`: typed registry identities for official lookup.
- `art-source-fault-facts`: shared source-attributed faults.
- `scene-artwork-presentation`: include explicit scene official selection after authored room overrides.
- `webclient-gallery-management-actions`: allow admitted scene official selection through declared preference scope.

## Impact

Affected owners are `world/art/`, gallery server actions/read models and focused art tests. Update `docs/development/official-artwork-deployment.md` and the approved unified-image design's source-policy sections. No new dependencies, artwork files, commands, protocol fields, migrations or compatibility paths. Human-reviewed policy reconciliation is recorded in `design.md`, section “Policy review”; image fidelity is outside this change.

## Batch:

depends-on: none

Apply and archive before `retire-classic-art-assets`. Both touch `art-gallery-resolution`, `art-gallery-autogen`, `art-gallery-model`, `art-gallery-generation`, `art-subject-model`, `art-source-fault-facts`, and potentially official/fallback requirements during complete retirement. Code conflicts include presenter, service and gallery tests. Serialize implementation and spec synchronization; retirement must preserve this change's added scenarios when composing shared requirement blocks.
