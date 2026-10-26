# Proposal

## Why

Removing the remaining title producers completes the identity cutover. Names and persona prose already carry identity without an independent role label.

Approved source: `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` (aa3dbe64). Planning only, unreleased clean cutover.

## What Changes

- **BREAKING** Delete NPC title fields, validators and writes from authored/imported/generated producers after plain-name readers are removed.
- Complete the named producer/consumer/test/documentation cutover in design.md, without shims or historical save repair.
- Preserve existing deterministic gameplay ownership and every stated non-goal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-identity-titles`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `import-schema`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `blueprint-portrait-policy`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `scenario-director`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `prompt-library`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `settlement-place-registry`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.
- `guild-registration`: amend the affected current behavior and remove superseded contracts as specified by this change's delta.

## Impact

Current producers include CHARACTER_SCHEMA_V1 title, imports loader/semantic checker, GuildAdventurer.title, PlaceDefinition.host_title, GuildBranch/ShopDefinition host_title, BlueprintNpcReq.title, characterization helper, StageNpcCharacterization, materializer and prompt/templates. Generated-packages changes the same package/prompt schemas and must finish first so this slice removes title from its final schema as well.

This is a one-engineer-day runnable slice with 4 focused implementation/test/documentation units. Exact contracts and complete caller categories are in design.md; planned checks are not planning results.

## Batch:

depends-on: npc-direct-capability-declarations
depends-on: npc-plain-name-presentation
depends-on: authored-dialogue-generated-packages

code-conflicts: N follows D/S and authored-dialogue-generated-packages; it changes final generated schemas only after that active cutover. All ten authored-dialogue-content-* batches are prose-only identity consumers; if still active their no-title guidance is amended, without making optional literary work a prerequisite. Serialize places/prompts/templates/docs and traceability with their owners.

The complete new-new and relevant active-change matrix and amendment ownership are in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md`. The approved source remains unchanged.
