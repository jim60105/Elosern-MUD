## Purpose

Define the shared object-appearance layer's Traditional Chinese presentation frames, used
identically by the text look command, the `at_look` seam, and the webclient explore-look action.

## ADDED Requirements

### Requirement: Target appearance includes the displayed-stats block on every entry path
The shared target-appearance layer SHALL append the displayed-stats block (`display_stat_block`)
for living targets identically across all three entry paths: the text look command (「看 <目標>」),
the character's `at_look` hook, and the webclient `explore.look` action. The block SHALL appear
after the target's zh-tw description and SHALL NOT appear in room appearance. Entities that are not
living SHALL render no block. The affinity stage-line behavior and the onboarding look beat SHALL
be unchanged.

#### Scenario: All three entry paths show the same block
- **WHEN** a player looks at the same living NPC through the text 「看」 command, the `at_look`
  hook, and the webclient `explore.look` action
- **THEN** all three outputs contain the same displayed-stats block after the description, with the
  same values in the same fixed order

#### Scenario: Non-living targets never show the block
- **WHEN** a player looks at a present object or a room through any of the three entry paths
- **THEN** no displayed-stats block appears
