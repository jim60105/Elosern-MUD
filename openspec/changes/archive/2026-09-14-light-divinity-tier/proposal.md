## Why

The authored MP-240 capstone cannot receive a tier under the five-band classifier. Extend the common label classifier using the already documented sixth cost band, without adding a cast gate.

## What Changes

- Extend CostTier and MP_COST_TIERS for the documented label-only sixth band; update all affected label consumers through LSP references.
- Verify matching-column and fallback precedence with synthetic spell objects, especially the 180 overlap and both new endpoints.
- Update the authoring cost-band documentation without creating numeric casting requirements.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-registry`: The executable contract changes as specified in this proposal's delta.

## Impact

Implementation surfaces: `world/skills/cost_tiers.py`, `world/skills/tests/test_cost_tiers.py`, `docs/development/adding-spells.md`.

Dependencies: None. Estimated bounded implementation: 3 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
