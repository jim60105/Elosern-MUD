# Spec Delta

## ADDED Requirements

### Requirement: The help overlay carries the party management rules
The help overlay SHALL carry the rule explanations the party and shop windows omit: companion follow rules, item transfer rules (out of combat only, free, equipped and locked items excluded), combat restrictions in the party window, the 系譜 node legend (filled, half-filled, dashed, 可解鎖), the shop's single-price convention, and the P B C K L J M hotkeys, in Traditional Chinese, as static authored text with no state.

#### Scenario: Transfer rules live in help, not in the bag
- **WHEN** the player opens 說明 and the party window's 背包 tab in turn
- **THEN** the help overlay explains the transfer rules while the bag shows only counts, controls and committed disabled reasons

#### Scenario: Help explains following under possession
- **WHEN** the help overlay's party section renders
- **THEN** its follow rules state that the whole party, the player's own body included, follows a possessed companion through exits

#### Scenario: The lineage legend is in help
- **WHEN** the help overlay's party section renders
- **THEN** it explains the three node diamond states and 可解鎖 with shape and text, never colour alone
