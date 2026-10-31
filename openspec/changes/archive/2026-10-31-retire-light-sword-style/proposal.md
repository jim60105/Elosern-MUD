# Proposal

## Why

The two human sword presets still start with `light_sword_style`, outside the authored 劍術 tree. Retiring that obsolete skill and granting the existing root lets both characters begin that tree without inventing a separate royal sword art.

## What Changes

- **BREAKING:** Delete the `light_sword_style` registry definition and narration row, retire its main-spec requirement, and remove its current consumers. The retired key will no longer resolve in the runtime registry, narration catalog, presets, or import validation.
- Set `elysa_snow` and `lidzia_rosenthal` to `active_skills=("basic_swordplay",)`. On new activation both own the existing sword root and can begin practicing 劍術. Later nodes retain existing ownership and proficiency rules; this does not grant the whole tree.
- Replace the import example's skill with `basic_swordplay`; update developer documentation, the category census, the preset kind-error fixture, and the practice docstring. Remove the retired test and its traceability annotation. Preserve test-file freeze registration.
- Remove the 光劍架式 lore bullet and the separate 「聖騎士劍術」 concept. Describe the Kingdom's 聖騎士團 as training in the existing 劍術 system. Update the two current technical design documents that still cite the retired key.
- Replace the skill-lineage prose example with `shadow_slash`, leaving its practice rule unchanged. Add no skill uniqueness constraint or positive/negative uniqueness narrative.

There is no alias, migration, deprecation path, or new replacement skill. The existing `basic_swordplay` is reused in the two presets and import example exactly as authored. `basic_attack`, `dual_wield_style`, all 14 martial-tree nodes, faction definitions, items, NPC profiles, and NPC 「劍聖劍術」 prose remain unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-registry`: REMOVED `light_sword_style deals damage via the standard damage convention`.
- `skill-lineage`: MODIFIED `Successful ACTIVE resolution accruses lineage practice XP`, changing one scenario's example only and preserving the existing heading and every scenario.

## Impact

This is one engineer-day of bounded data deletion, reference updates, and focused regression checks. `design.md` inventories every discovered current reference and unaffected contract; `tasks.md` names edits and executable acceptance checks. No runtime implementation is claimed by this proposal.

No new executable mechanism requirement is added for catalog choices or lore wording. Existing registry, preset, narration, import, and synthetic lineage tests establish the mechanisms. Lore meaning and narrative quality are human-reviewed against `design.md`, “Lore review contract”; they are not copy-pinning tests.

## Historical evidence

The archived exclusivity narrative remains in `openspec/changes/archive/2026-08-13-preset-skill-kits/design.md:59-61`. The search found no current assertion of that single-sword exclusivity. `AGENTS.md` defines archived changes as historical evidence, with main specs owning the current contract; this proposal preserves the archive rather than silently rewriting it. Other archived retired-key mentions and ignored local logs are likewise historical, not resolvable callers. Current planning artifacts necessarily name the deletion target.
