# Design

## Context

`world/rules/starting_policy.py` selects the elf policy only in custom mode. Preset activation and starting companion construction both use `resolve_preset_values`.

## Goals / Non-Goals

Share the existing race policy and retain the authored physical builds. Do not change combat, skill kits, equipment, disguise values, lore bands or persisted characters.

## Decisions

- Select the policy by resolved race. Remove the redundant mode parameter and its constants from the pure policy resolver, migrating its callers; keep creation request modes for selecting identity, gear and skill inputs.
- Preserve each elf card's physical allocations and assign its remaining budget to magic. Update card comments and guidance that describe the former values.
- Keep preset activation and companion creation on the same value resolver. No pending draft conversion is required because custom policy and preset selection payloads are unchanged.

## Risks / Trade-offs

Newly constructed companions receive lower starting magic, too. Existing saves and authored NPCs retain their stored values. Preset skills and equipment can still produce different combat outcomes.
