# Proposal

## Why

After `narration-core-and-combat-prose`, the 115 ACTIVE elemental spells all open on an
element-and-shape line: 火焰箭 and 火焰風暴 differ, but 火焰箭 and 火球術 read the same, and
so do the thirteen spells of every element. Elemental magic is the largest skill family in the
game, so this is the most visible remaining "every skill sounds the same" defect.

## What Changes

- Author a per-spell action line for each of the 115 ACTIVE elemental spells across the eight
  elements, one or two variants each, with the element's own imagery vocabulary and the spell's
  own shape (single target, area, buff, heal, control).
- Add per-spell kind overrides only where the spell changes the shape of the fight — an area
  spell's opening addresses the whole line-up, a scorch or chill spell's opening carries its
  lasting mark — and leave the shared outcome and mechanical pools to do the rest.
- Remove the elemental-magic family from the catalog's pending-family set, leaving only sexual
  acts pending.

## Capabilities

### New Capabilities

### Modified Capabilities
- `action-narration`: adds the per-spell coverage requirement for the elemental-magic family
  and shrinks the pending-family set to sexual acts.

## Impact

- One authored data module per element under `world/skills/narration/` (eight modules, in the
  registry's slice order) plus the catalog aggregate's import list and the frozen
  pending-family constant.
- The coverage-contract slice gains the elemental assertion and its pinning test.
- No registry row change, no balance change, no pipeline or panel change.
