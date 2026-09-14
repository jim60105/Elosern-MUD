## Why

The flat light catalog cannot express the complete authored lineage and composite effects. After the reusable mechanics land, replace it in one complete data cutover without description-only substitutes or a light data-contract test suite.

## What Changes

- Declare the complete 16-node light tree from the amended technical design §4.4, using reusable typed effect policies, state gates, buff profiles and reactions.
- **BREAKING**: remove `holy_shield` and exclusively used buff/status references; recost `goddess_blessing` from 145 to 150. No aliases, migrations or backward-compatibility layer.
- Declare the separate `pain_to_pleasure` and `priestly_grace` passives; preserve existing acquisition and derived proficiency caps.
- Replace light-specific key/count/label/value/effect-table echo tests with synthetic program-behavior coverage. Remove obsolete freeze entries without adding exemptions.
- Update player command documentation and the spell-authoring guide; exercise actual authored content through a disposable runtime smoke scenario.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-registry`: Replace the old light catalog requirement with executable lineage and composed-effect behavior, rather than a duplicated table test contract.

## Impact

`world/skills/registry.py`; light bindings in buff, status, combat-modifier and reaction rulebooks; affected presets/loadouts; existing light data-echo tests; `tools/test_data_freeze.json`; `docs/development/adding-spells.md`; both player command reference documents.

Dependencies are all reusable light-mechanics proposals listed in this change's design. This is a six-hour integration slice, including focused verification. It does not implement missing generic handlers. Main specs, game code and tests remain unchanged in this proposal-only turn; do not apply, archive, sync or merge until requested.
